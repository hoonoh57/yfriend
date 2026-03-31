"""
engines/visual/gemini_image.py - Mutable visual engine
1차: Pollinations.ai (무료, API키 불필요)
2차: Gemini Image API (폴백)
사용자 설정: config.yaml의 image_preset으로 프롬프트 스타일 선택
"""
from __future__ import annotations
import asyncio
import base64
from pathlib import Path
from urllib.parse import quote

import requests

from core.models import Blueprint, Part, PartType, Scene


# 이미지 프롬프트 프리셋
IMAGE_PRESETS = {
    "documentary": (
        "A professional documentary-style photograph, "
        "shot on location with natural lighting, Canon EOS R5, "
        "wide angle 24mm lens, vivid true-to-life colors, "
        "{scene}. No text, no watermarks, no logos."
    ),
    "cinematic": (
        "A cinematic widescreen photograph taken with a Sony A7R IV camera, "
        "85mm f/1.4 lens, shallow depth of field, golden hour natural lighting, "
        "photorealistic, ultra high definition 8K, film grain, "
        "{scene}. No text, no watermarks, no logos."
    ),
    "aerial": (
        "An aerial drone photograph taken from above, DJI Mavic 3 Pro, "
        "sweeping landscape view, golden hour, ultra sharp details, "
        "photorealistic, National Geographic quality, "
        "{scene}. No text, no watermarks, no logos."
    ),
    "ghibli": (
        "A beautiful Studio Ghibli anime style illustration, "
        "hand-painted watercolor textures, soft pastel colors, "
        "dreamy atmospheric lighting, Hayao Miyazaki inspired, "
        "{scene}. No text, no watermarks."
    ),
    "disney": (
        "A Disney Pixar 3D animation style render, "
        "vibrant saturated colors, soft ambient occlusion, "
        "cheerful mood, detailed environment, "
        "{scene}. No text, no watermarks."
    ),
    "oil_painting": (
        "A classic oil painting on canvas, impressionist style, "
        "thick visible brushstrokes, rich warm color palette, "
        "museum quality fine art, dramatic chiaroscuro lighting, "
        "{scene}. No text, no signatures."
    ),
    "minimal": (
        "A clean modern minimalist design, flat illustration style, "
        "limited color palette, geometric shapes, "
        "professional graphic design, editorial quality, "
        "{scene}. No text, no watermarks."
    ),
}


class Engine:
    """Scene별 키프레임 이미지 생성 - 사용자 설정 기반"""

    def __init__(
        self,
        model: str = "gemini-2.5-flash-image",
        pollinations_model: str = "flux",
        pollinations_enhance: bool = True,
        image_preset: str = "documentary",
        custom_prompt_template: str = "",
        delay_between_scenes: int = 16,
        api_key=None,
        **kwargs,
    ):
        self.gemini_model = model
        self.poll_model = pollinations_model
        self.poll_enhance = pollinations_enhance
        self.preset = image_preset
        self.custom_template = custom_prompt_template
        self.delay = delay_between_scenes

        if isinstance(api_key, list):
            self.api_keys = [k for k in api_key if k]
        elif isinstance(api_key, str) and api_key:
            self.api_keys = [api_key]
        else:
            self.api_keys = []

    async def generate_keyframes(
        self, blueprint: Blueprint, output_dir: Path, **kwargs
    ) -> list[Part]:
        output_dir.mkdir(parents=True, exist_ok=True)
        parts = []

        print(f"      설정: 프리셋={self.preset}, 모델={self.poll_model}, enhance={self.poll_enhance}")

        for scene in blueprint.scenes:
            print(f"      [IMG] scene_{scene.scene_number:02d}: {scene.title}")
            image_path = output_dir / f"scene_{scene.scene_number:02d}_keyframe.png"

            prompt = self._build_prompt(scene)
            success = await self._generate_pollinations(prompt, image_path)

            if not success and self.api_keys:
                print(f"           Pollinations 실패, Gemini 폴백 시도...")
                success = await self._generate_gemini(prompt, image_path)

            if success:
                part = Part(
                    part_type=PartType.KEYFRAME,
                    file_path=image_path,
                    scene_id=scene.scene_id,
                    metadata={"prompt": prompt[:200]},
                )
                parts.append(part)
                print(f"           -> {image_path.name} [OK]")
            else:
                print(f"           -> {image_path.name} [FAIL]")

            if scene != blueprint.scenes[-1]:
                print(f"           ({self.delay}초 대기...)")
                await asyncio.sleep(self.delay)

        return parts

    def _build_prompt(self, scene: Scene) -> str:
        # 커스텀 템플릿이 있으면 우선 사용
        if self.custom_template:
            return self.custom_template.format(scene=scene.visual_prompt_en)

        # 프리셋에서 템플릿 가져오기
        template = IMAGE_PRESETS.get(self.preset, IMAGE_PRESETS["documentary"])
        return template.format(scene=scene.visual_prompt_en)

    async def _generate_pollinations(self, prompt: str, output_path: Path) -> bool:
        try:
            encoded = quote(prompt)
            enhance = "true" if self.poll_enhance else "false"
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1920&height=1080&model={self.poll_model}"
                f"&enhance={enhance}&nologo=true"
            )
            print(f"           Pollinations 요청 중 ({self.poll_model})...")

            response = requests.get(url, timeout=180)

            if response.status_code == 200 and len(response.content) > 1000:
                output_path.write_bytes(response.content)
                print(f"           OK ({len(response.content)//1024}KB)")
                return True
            else:
                print(f"           실패: status={response.status_code}")
                return False
        except Exception as e:
            print(f"           에러: {str(e)[:80]}")
            return False

    async def _generate_gemini(self, prompt: str, output_path: Path) -> bool:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return False

        for i, key in enumerate(self.api_keys):
            key_label = f"KEY_{i+1} ({key[:8]}...{key[-4:]})"
            try:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model=self.gemini_model,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                    ),
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        output_path.write_bytes(image_data)
                        print(f"           Gemini OK ({key_label})")
                        return True
            except Exception as e:
                print(f"           Gemini FAIL {key_label}: {str(e)[:60]}")
                if "429" in str(e):
                    await asyncio.sleep(2)
                continue
        return False
