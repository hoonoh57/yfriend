"""
engines/visual/multi_image.py – Multi-backend image generation engine
Priority: SiliconFlow (Kolors) → Pollinations (Flux) → Gemini → black fallback

Features:
- Professional photorealistic prompts with anti-artifact directives
- Negative prompts for SiliconFlow (Kolors supports it natively)
- Character/scene consistency via shared style anchors
- Automatic prompt enhancement
"""
from __future__ import annotations
import asyncio, json, time, urllib.parse
from pathlib import Path
from typing import Optional
import requests

from core.models import Part, PartType, Scene, Blueprint, Origin

# ───────────────── Master Negative Prompt (SiliconFlow Kolors) ─────────────────
NEGATIVE_PROMPT = (
    "deformed, distorted, disfigured, mutated, extra limbs, extra fingers, "
    "fused fingers, missing fingers, bad hands, poorly drawn hands, "
    "malformed hands, extra arms, extra legs, bad anatomy, wrong proportions, "
    "asymmetric face, ugly face, blurry face, low quality face, "
    "cross-eyed, lazy eye, unnatural eye color, "
    "bad teeth, open mouth artifact, double chin artifact, "
    "unnatural hair, floating hair, bald patches, "
    "watermark, text, logo, signature, caption, UI elements, "
    "low quality, low resolution, blurry, pixelated, jpeg artifacts, "
    "noise, grain, overexposed, underexposed, oversaturated, "
    "cartoon, painting, illustration, anime, 3d render, CGI, "
    "duplicate, clone, copy, tiling, cropped, "
    "bad composition, out of frame, cut off"
)

# ───────────────── Anti-artifact Positive Suffix ─────────────────
# Embedded in ALL prompts (Flux doesn't support negative_prompt)
QUALITY_SUFFIX = (
    "photorealistic, ultra high definition 8K, shot on Sony A7R V, "
    "85mm f/1.4 prime lens, natural lighting, anatomically correct, "
    "correct number of fingers, natural hand poses, symmetrical face, "
    "detailed sharp facial features, natural skin texture, "
    "professional color grading, cinematic depth of field"
)

# ───────────────── Prompt Presets ─────────────────
IMAGE_PRESETS = {
    "documentary": (
        "A professional documentary-style photograph, "
        "shot on location with natural ambient lighting, "
        "Canon EOS R5 Mark II, wide angle 24mm f/2.8 lens, "
        "vivid true-to-life colors, editorial quality"
    ),
    "cinematic": (
        "A cinematic widescreen still frame from a feature film, "
        "Arri Alexa 65 camera, anamorphic Cooke S7/i lens, "
        "shallow depth of field, dramatic volumetric lighting, "
        "teal and orange color grading, 2.39:1 aspect ratio feel"
    ),
    "portrait": (
        "A professional portrait photograph, "
        "shot in a studio with softbox lighting, "
        "Canon EOS R5, 85mm f/1.2 lens, "
        "shallow depth of field, creamy bokeh background, "
        "natural skin tones, catch light in eyes"
    ),
    "aerial": (
        "An aerial drone photograph taken at golden hour, "
        "DJI Mavic 3 Pro Hasselblad camera, "
        "ultra-wide perspective, vivid landscape colors, "
        "sharp horizon line, no lens distortion"
    ),
    "street": (
        "A candid street photography shot, "
        "Leica Q3, 28mm f/1.7 Summilux lens, "
        "natural urban lighting, decisive moment composition, "
        "authentic atmosphere, sharp subject with soft background"
    ),
    "food": (
        "A professional food photography shot, "
        "overhead 45-degree angle, Canon EOS R5, 100mm macro lens, "
        "soft diffused natural window light, shallow depth of field, "
        "vibrant appetizing colors, steam and texture detail"
    ),
    "landscape": (
        "A breathtaking landscape photograph, "
        "Nikon Z9, 14-24mm f/2.8 ultra-wide lens, "
        "golden hour natural light, deep depth of field f/11, "
        "vivid colors, sharp foreground to infinity focus"
    ),
    "ghibli": (
        "A hand-painted illustration in Studio Ghibli anime style, "
        "soft watercolor textures, warm pastel palette, "
        "whimsical atmosphere, detailed background scenery"
    ),
    "disney": (
        "A 3D rendered scene in Disney Pixar animation style, "
        "vibrant saturated colors, soft global illumination, "
        "cheerful mood, expressive characters"
    ),
    "oil_painting": (
        "A classical oil painting on canvas, "
        "rich impasto brushstrokes, Renaissance chiaroscuro lighting, "
        "museum-quality fine art, gilded frame worthy"
    ),
    "minimal": (
        "A clean minimalist photograph with ample negative space, "
        "soft neutral tones, modern Scandinavian aesthetic"
    ),
}

# ───────────────── Scene Consistency Anchors ─────────────────
# These help maintain visual coherence across scenes
CONSISTENCY_ANCHORS = {
    "korean_seasons": "Korean peninsula, temperate East Asian landscape, Korean architecture and nature, ",
    "korean_food": "Korean traditional setting, wooden table, ceramic dishes, ",
    "korean_culture": "Korean traditional hanbok clothing, Korean architecture, ",
    "travel": "travel documentary style, real locations, authentic atmosphere, ",
    "default": "",
}


class Engine:
    """Multi-backend visual engine with professional photorealistic prompts."""

    def __init__(
        self,
        pollinations_model: str = "flux",
        pollinations_enhance: bool = True,
        siliconflow_model: str = "Kwai-Kolors/Kolors",
        siliconflow_size: str = "1024x1024",
        siliconflow_steps: int = 20,
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
        self.gemini_keys = api_key if isinstance(api_key, list) else ([api_key] if api_key else [])
        self.sf_key = siliconflow_key
        self.style = IMAGE_PRESETS.get(self.preset, IMAGE_PRESETS["documentary"])

    # ───────────────────── Public API ─────────────────────
    async def generate_keyframes(self, blueprint: Blueprint, output_dir: Path) -> list[Part]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Detect consistency anchor from topic
        anchor = self._detect_anchor(blueprint.topic)

        print(f"      [설정] preset={self.preset}, SF={self.sf_model}")
        print(f"      [설정] pollinations={self.pollinations_model}, enhance={self.pollinations_enhance}")
        print(f"      [설정] consistency_anchor={'있음' if anchor else '없음'}")
        print(f"      [백엔드] SiliconFlow → Pollinations → Gemini → 검은배경")

        parts: list[Part] = []
        for i, scene in enumerate(blueprint.scenes):
            img_path = output_dir / f"scene_{scene.scene_number:02d}_keyframe.png"
            prompt = self._build_prompt(scene, blueprint.style_guide or "", anchor)
            neg = NEGATIVE_PROMPT
            print(f"      [IMG] scene_{scene.scene_number:02d}: {scene.title}")

            success = False

            # ── Backend 1: SiliconFlow (with negative prompt) ──
            if self.sf_key:
                success = await self._generate_siliconflow(prompt, neg, img_path)
                if success:
                    print(f"           ✓ SiliconFlow 성공")

            # ── Backend 2: Pollinations (negative embedded in prompt) ──
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

            if i < len(blueprint.scenes) - 1 and self.delay > 0:
                print(f"           ({self.delay}s 대기...)")
                await asyncio.sleep(self.delay)

        return parts

    # ───────────────── Prompt Builder ─────────────────
    def _build_prompt(self, scene: Scene, style_guide: str, anchor: str) -> str:
        if self.custom_template:
            return self.custom_template.replace("{scene}", scene.visual_prompt_en)

        # Build a structured, professional prompt
        prompt_parts = [
            self.style,                          # Camera/style preset
            anchor,                              # Consistency anchor
            scene.visual_prompt_en,              # Scene-specific content
            QUALITY_SUFFIX,                      # Anti-artifact quality tags
            "no text, no watermark, no logo, no signature, no UI elements",
        ]
        return ", ".join(p for p in prompt_parts if p)

    def _detect_anchor(self, topic: str) -> str:
        """Auto-detect consistency anchor from topic keywords."""
        topic_lower = topic.lower()
        if any(k in topic_lower for k in ["korea", "한국", "korean"]):
            if any(k in topic_lower for k in ["food", "음식", "cuisine", "dish"]):
                return CONSISTENCY_ANCHORS["korean_food"]
            if any(k in topic_lower for k in ["culture", "문화", "tradition"]):
                return CONSISTENCY_ANCHORS["korean_culture"]
            return CONSISTENCY_ANCHORS["korean_seasons"]
        if any(k in topic_lower for k in ["travel", "여행", "trip", "tour"]):
            return CONSISTENCY_ANCHORS["travel"]
        return CONSISTENCY_ANCHORS["default"]

    # ───────────────── Backend: SiliconFlow ─────────────────
    async def _generate_siliconflow(self, prompt: str, negative: str, img_path: Path) -> bool:
        try:
            url = "https://api.siliconflow.cn/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {self.sf_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.sf_model,
                "prompt": prompt,
                "negative_prompt": negative,
                "image_size": self.sf_size,
                "num_inference_steps": self.sf_steps,
                "guidance_scale": 7.5,
                "batch_size": 1,
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

            image_url = images[0].get("url", "")
            if not image_url:
                print(f"           SF FAIL: URL 없음")
                return False

            img_resp = await asyncio.to_thread(requests.get, image_url, timeout=60)
            if img_resp.status_code == 200 and len(img_resp.content) > 1024:
                img_path.write_bytes(img_resp.content)
                return True
            return False

        except Exception as e:
            print(f"           SF ERROR: {e}")
            return False

    # ───────────────── Backend: Pollinations ─────────────────
    async def _generate_pollinations(self, prompt: str, img_path: Path) -> bool:
        try:
            encoded = urllib.parse.quote(prompt, safe="")
            enhance = "true" if self.pollinations_enhance else "false"
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1920&height=1080"
                f"&model={self.pollinations_model}"
                f"&enhance={enhance}&nologo=true"
            )
            resp = await asyncio.to_thread(requests.get, url, timeout=120)
            if resp.status_code == 200 and len(resp.content) > 1024:
                img_path.write_bytes(resp.content)
                return True
            else:
                print(f"           Poll FAIL: status={resp.status_code}, size={len(resp.content)}")
                return False
        except Exception as e:
            print(f"           Poll ERROR: {e}")
            return False

    # ───────────────── Backend: Gemini Image ─────────────────
    async def _generate_gemini(self, prompt: str, img_path: Path) -> bool:
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
            return False
