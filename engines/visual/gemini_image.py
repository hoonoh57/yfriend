"""
engines/visual/gemini_image.py - Mutable visual engine
Gemini 2.5 Flash Image (Nano Banana) 기반 키프레임 이미지 생성
API키 로테이션 지원, 무료 티어 (~500장/일)
"""
from __future__ import annotations
import asyncio
import base64
import time
from pathlib import Path
from google import genai
from google.genai import types
from core.models import Blueprint, Part, PartType, Scene


class Engine:
    """Scene별 키프레임 이미지를 Gemini Image API로 생성"""

    def __init__(
        self,
        model: str = "gemini-2.5-flash-image",
        aspect_ratio: str = "16:9",
        style: str = "cinematic, photorealistic, 4K, vibrant colors",
        api_key=None,
        **kwargs,
    ):
        self.model = model
        self.aspect_ratio = aspect_ratio
        self.style = style

        # API키 로테이션 (기존 gemini_flash.py와 동일 패턴)
        if isinstance(api_key, list):
            self.api_keys = [k for k in api_key if k]
        elif isinstance(api_key, str) and api_key:
            self.api_keys = [api_key]
        else:
            self.api_keys = []

        if not self.api_keys:
            raise RuntimeError("Gemini API key not configured for visual engine")

    async def generate_keyframes(
        self, blueprint: Blueprint, output_dir: Path, **kwargs
    ) -> list[Part]:
        """Blueprint의 각 Scene에 대해 키프레임 이미지 1장씩 생성"""
        output_dir.mkdir(parents=True, exist_ok=True)
        parts = []

        for scene in blueprint.scenes:
            print(f"      [IMG] scene_{scene.scene_number:02d}: {scene.title}")
            image_path = output_dir / f"scene_{scene.scene_number:02d}_keyframe.png"

            # 프롬프트 구성: visual_prompt_en + 스타일 가이드
            prompt = self._build_prompt(scene, blueprint.style_guide)

            success = await self._generate_with_rotation(prompt, image_path)

            if success:
                part = Part(
                    part_type=PartType.KEYFRAME,
                    file_path=image_path,
                    scene_id=scene.scene_id,
                    metadata={
                        "model": self.model,
                        "prompt": prompt[:200],
                        "aspect_ratio": self.aspect_ratio,
                    },
                )
                parts.append(part)
                print(f"           -> {image_path.name} [OK]")
            else:
                print(f"           -> {image_path.name} [FAIL] 모든 키 실패")

        return parts

    def _build_prompt(self, scene: Scene, style_guide: str) -> str:
        """Scene 정보로 이미지 생성 프롬프트 구성"""
        prompt_parts = [
            f"Create a single high-quality image for a YouTube video scene.",
            f"Visual description: {scene.visual_prompt_en}",
            f"Style: {self.style}",
            f"Scene context: {scene.title}",
            f"Keywords: {', '.join(scene.keywords) if scene.keywords else 'cinematic'}",
            f"Aspect ratio: {self.aspect_ratio} (widescreen YouTube format)",
            f"Do NOT include any text, watermarks, or logos in the image.",
        ]
        if style_guide:
            prompt_parts.append(f"Overall style guide: {style_guide}")
        return "\n".join(prompt_parts)

    async def _generate_with_rotation(self, prompt: str, output_path: Path) -> bool:
        """API키 로테이션으로 이미지 생성 시도"""
        last_error = None

        for i, key in enumerate(self.api_keys):
            key_label = f"KEY_{i+1} ({key[:8]}...{key[-4:]})"
            try:
                client = genai.Client(api_key=key)

                # Gemini Image Generation API 호출
                response = client.models.generate_content(
                    model=self.model,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                    ),
                )

                # 응답에서 이미지 추출
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        # 이미지 데이터를 파일로 저장
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        output_path.write_bytes(image_data)
                        return True

                # 이미지가 없으면 텍스트만 반환된 경우
                print(f"           WARN {key_label}: 이미지 없이 텍스트만 반환됨")
                last_error = "No image in response"
                continue

            except Exception as e:
                last_error = e
                error_msg = str(e)
                print(f"           FAIL {key_label}: {error_msg[:80]}")

                # 429 Rate Limit → 잠시 대기 후 다음 키
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    await asyncio.sleep(2)
                continue

        return False
