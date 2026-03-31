"""
engines/visual/multi_image.py – Multi-backend image generation engine
Priority: SiliconFlow (free FLUX.1-schnell) → Pollinations.ai → Gemini Image → black fallback
"""
from __future__ import annotations
import asyncio, json, time, urllib.parse
from pathlib import Path
from typing import Optional
import requests

from core.models import Part, PartType, Scene, Blueprint, Origin

# ─────────────────────────── Prompt Presets ───────────────────────────
IMAGE_PRESETS = {
    "documentary": (
        "A professional documentary-style photograph, "
        "shot on location with natural lighting, Canon EOS R5, "
        "wide angle 24mm lens, vivid true-to-life colors"
    ),
    "cinematic": (
        "A cinematic widescreen still frame, anamorphic lens flare, "
        "shallow depth of field, dramatic color grading, 35mm film grain"
    ),
    "aerial": (
        "An aerial drone photograph taken at golden hour, "
        "DJI Mavic 3 Pro, ultra-wide perspective, vivid landscape colors"
    ),
    "ghibli": (
        "A hand-painted illustration in Studio Ghibli anime style, "
        "soft watercolor textures, warm pastel palette, whimsical atmosphere"
    ),
    "disney": (
        "A 3D rendered scene in Disney Pixar animation style, "
        "vibrant colors, soft global illumination, cheerful mood"
    ),
    "oil_painting": (
        "A classical oil painting on canvas, rich impasto brushstrokes, "
        "Renaissance chiaroscuro lighting, museum-quality fine art"
    ),
    "minimal": (
        "A clean minimalist photograph with ample negative space, "
        "soft neutral tones, modern aesthetic"
    ),
}


class Engine:
    """Multi-backend visual engine with automatic fallback."""

    def __init__(
        self,
        pollinations_model: str = "flux",
        pollinations_enhance: bool = True,
        siliconflow_model: str = "black-forest-labs/FLUX.1-schnell",
        siliconflow_size: str = "1024x1024",
        siliconflow_steps: int = 4,
        image_preset: str = "documentary",
        custom_prompt_template: str = "",
        delay_between_scenes: int = 3,
        # injected by orchestrator
        api_key=None,
        siliconflow_key: str = "",
        **kwargs,
    ):
        self.pollinations_model = pollinations_model
        self.pollinations_enhance = pollinations_enhance
        self.sf_model = siliconflow_model
        self.sf_size = siliconflow_size
        self.sf_steps = siliconflow_steps
        self.preset = image_preset
        self.custom_template = custom_prompt_template
        self.delay = delay_between_scenes
        # Gemini keys (list or single string)
        self.gemini_keys = api_key if isinstance(api_key, list) else ([api_key] if api_key else [])
        self.sf_key = siliconflow_key
        self.style = IMAGE_PRESETS.get(self.preset, IMAGE_PRESETS["documentary"])

    # ───────────────────── Public API ─────────────────────
    async def generate_keyframes(self, blueprint: Blueprint, output_dir: Path) -> list[Part]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"      [설정] preset={self.preset}, SF model={self.sf_model}")
        print(f"      [설정] pollinations={self.pollinations_model}, enhance={self.pollinations_enhance}")
        print(f"      [백엔드 우선순위] SiliconFlow → Pollinations → Gemini → 검은배경")

        parts: list[Part] = []
        for i, scene in enumerate(blueprint.scenes):
            img_path = output_dir / f"scene_{scene.scene_number:02d}_keyframe.png"
            prompt = self._build_prompt(scene, blueprint.style_guide or "")
            print(f"      [IMG] scene_{scene.scene_number:02d}: {scene.title}")

            success = False

            # ── Backend 1: SiliconFlow ──
            if self.sf_key:
                success = await self._generate_siliconflow(prompt, img_path)
                if success:
                    print(f"           ✓ SiliconFlow 성공")

            # ── Backend 2: Pollinations ──
            if not success:
                success = await self._generate_pollinations(prompt, img_path)
                if success:
                    print(f"           ✓ Pollinations 성공")

            # ── Backend 3: Gemini Image ──
            if not success and self.gemini_keys:
                success = await self._generate_gemini(prompt, img_path)
                if success:
                    print(f"           ✓ Gemini 성공")

            if not success:
                print(f"           ✗ 모든 백엔드 실패 → 검은배경 폴백")

            if success:
                part = Part(
                    part_type=PartType.KEYFRAME,
                    scene_id=scene.scene_id,
                    file_path=img_path,
                    origin=Origin.AUTO,
                    engine_used="multi_image",
                    prompt_used=prompt[:200],
                )
                parts.append(part)

            # delay between scenes (not after last)
            if i < len(blueprint.scenes) - 1 and self.delay > 0:
                print(f"           ({self.delay}s 대기...)")
                await asyncio.sleep(self.delay)

        return parts

    # ───────────────────── Backend: SiliconFlow ─────────────────────
    async def _generate_siliconflow(self, prompt: str, img_path: Path) -> bool:
        """Call SiliconFlow /v1/images/generations (OpenAI-compatible)."""
        try:
            url = "https://api.siliconflow.cn/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {self.sf_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.sf_model,
                "prompt": prompt,
                "image_size": self.sf_size,
                "num_inference_steps": self.sf_steps,
            }
            resp = await asyncio.to_thread(
                requests.post, url, headers=headers, json=payload, timeout=120
            )
            if resp.status_code != 200:
                print(f"           SF FAIL ({resp.status_code}): {resp.text[:120]}")
                return False

            data = resp.json()
            images = data.get("images", [])
            if not images:
                print(f"           SF FAIL: 응답에 이미지 없음")
                return False

            # images[0] can have 'url' field
            image_url = images[0].get("url", "")
            if not image_url:
                print(f"           SF FAIL: 이미지 URL 없음")
                return False

            # Download the image
            img_resp = await asyncio.to_thread(
                requests.get, image_url, timeout=60
            )
            if img_resp.status_code == 200 and len(img_resp.content) > 1024:
                img_path.write_bytes(img_resp.content)
                return True
            else:
                print(f"           SF FAIL: 이미지 다운로드 실패 ({len(img_resp.content)} bytes)")
                return False

        except Exception as e:
            print(f"           SF ERROR: {e}")
            return False

    # ───────────────────── Backend: Pollinations ─────────────────────
    async def _generate_pollinations(self, prompt: str, img_path: Path) -> bool:
        """Call Pollinations.ai free image API (no key needed)."""
        try:
            encoded = urllib.parse.quote(prompt, safe="")
            enhance = "true" if self.pollinations_enhance else "false"
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1920&height=1080"
                f"&model={self.pollinations_model}"
                f"&enhance={enhance}&nologo=true"
            )
            resp = await asyncio.to_thread(
                requests.get, url, timeout=120
            )
            if resp.status_code == 200 and len(resp.content) > 1024:
                img_path.write_bytes(resp.content)
                return True
            else:
                print(f"           Poll FAIL: status={resp.status_code}, size={len(resp.content)}")
                return False
        except Exception as e:
            print(f"           Poll ERROR: {e}")
            return False

    # ───────────────────── Backend: Gemini Image ─────────────────────
    async def _generate_gemini(self, prompt: str, img_path: Path) -> bool:
        """Call Google Gemini Image API with key rotation."""
        try:
            from google import genai
            from google.genai import types

            for key in self.gemini_keys:
                try:
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-preview-04-17",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                        ),
                    )
                    if (
                        response.candidates
                        and response.candidates[0].content
                        and response.candidates[0].content.parts
                    ):
                        for part in response.candidates[0].content.parts:
                            if part.inline_data and part.inline_data.data:
                                img_path.write_bytes(part.inline_data.data)
                                return True
                except Exception as ge:
                    err_str = str(ge)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        continue
                    print(f"           Gemini ERROR: {err_str[:80]}")
                    continue
            return False
        except ImportError:
            print(f"           Gemini: google-genai 패키지 없음")
            return False

    # ───────────────────── Prompt Builder ─────────────────────
    def _build_prompt(self, scene: Scene, style_guide: str) -> str:
        if self.custom_template:
            return self.custom_template.replace("{scene}", scene.visual_prompt_en)

        return (
            f"{self.style}, {scene.visual_prompt_en}. "
            f"No text, no watermarks, no logos."
        )
