"""
engines/visual/gemini_image.py - Mutable visual engine
1차: Pollinations.ai (무료, API키 불필요)
2차: Gemini Image API (폴백)
"""
from __future__ import annotations
import asyncio
import base64
import time
from pathlib import Path
from urllib.parse import quote

import requests

from core.models import Blueprint, Part, PartType, Scene


class Engine:
    """Scene별 키프레임 이미지 생성 - Pollinations.ai 우선"""

    def __init__(
        self,
        model: str = "gemini-2.5-flash-image",
        aspect_ratio: str = "16:9",
        style: str = "cinematic, photorealistic, 4K, vibrant colors",
        api_key=None,
        **kwargs,
    ):
        self.gemini_model = model
        self.aspect_ratio = aspect_ratio
        self.style = style

        # Gemini 폴백용 API키
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

        for scene in blueprint.scenes:
            print(f"      [IMG] scene_{scene.scene_number:02d}: {scene.title}")
            image_path = output_dir / f"scene_{scene.scene_number:02d}_keyframe.png"

            prompt = self._build_prompt(scene, blueprint.style_guide)

            # 1차: Pollinations.ai (무료, 키 불필요)
            success = await self._generate_pollinations(prompt, image_path)

            # 2차: Gemini Image API (폴백)
            if not success and self.api_keys:
                print(f"           Pollinations 실패, Gemini 폴백 시도...")
                success = await self._generate_gemini(prompt, image_path)

            if success:
                part = Part(
                    part_type=PartType.KEYFRAME,
                    file_path=image_path,
                    scene_id=scene.scene_id,
                    metadata={
                        "prompt": prompt[:200],
                        "aspect_ratio": self.aspect_ratio,
                    },
                )
                parts.append(part)
                print(f"           -> {image_path.name} [OK]")
            else:
                print(f"           -> {image_path.name} [FAIL]")

            # Rate limit 방지: 장면 사이 16초 대기 (무가입 15초 제한)
            if scene != blueprint.scenes[-1]:
                wait = 16
                print(f"           ({wait}초 대기...)")
                await asyncio.sleep(wait)

        return parts

    def _build_prompt(self, scene: Scene, style_guide: str) -> str:
        return (
            f"A professional documentary-style photograph, "
            f"shot on location with natural lighting, Canon EOS R5, "
            f"wide angle 24mm lens, vivid true-to-life colors, "
            f"{scene.visual_prompt_en}. "
            f"No text, no watermarks, no logos."
        )


    async def _generate_pollinations(self, prompt: str, output_path: Path) -> bool:
        """Pollinations.ai로 이미지 생성 (무료, API키 불필요)"""
        try:
            encoded = quote(prompt)
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1920&height=1080&model=flux&enhance=true&nologo=true"
            )

            print(f"           Pollinations 요청 중...")

            response = requests.get(url, timeout=120)

            if response.status_code == 200 and len(response.content) > 1000:
                output_path.write_bytes(response.content)
                print(f"           Pollinations OK ({len(response.content)//1024}KB)")
                return True
            else:
                print(f"           Pollinations 실패: status={response.status_code}, size={len(response.content)}")
                return False

        except Exception as e:
            print(f"           Pollinations 에러: {str(e)[:80]}")
            return False

    async def _generate_gemini(self, prompt: str, output_path: Path) -> bool:
        """Gemini Image API 폴백"""
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
                error_msg = str(e)
                print(f"           Gemini FAIL {key_label}: {error_msg[:60]}")
                if "429" in error_msg:
                    await asyncio.sleep(2)
                continue

        return False
