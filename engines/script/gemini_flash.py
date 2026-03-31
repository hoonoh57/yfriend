"""
engines/script/gemini_flash.py - Mutable script engine
Gemini API key rotation: tries up to 5 keys sequentially.
"""
from __future__ import annotations

import json
from pathlib import Path

from google import genai

from core.models import Blueprint, Scene


SYSTEM_PROMPT = (
    "You are a professional YouTube video narrator and scriptwriter.\n"
    "Write a Korean narration script for the given topic.\n"
    "\n"
    "Respond ONLY with this JSON format (no other text):\n"
    "{{\n"
    '  "topic": "topic",\n'
    '  "total_scenes": N,\n'
    '  "estimated_total_duration_sec": N,\n'
    '  "style_guide": "style description",\n'
    '  "scenes": [\n'
    "    {{\n"
    '      "scene_id": "scene_01",\n'
    '      "scene_number": 1,\n'
    '      "title": "scene title in Korean",\n'
    '      "narration_ko": "Korean narration (2-4 sentences, natural spoken style)",\n'
    '      "visual_prompt_en": "Detailed English visual description for image generation",\n'
    '      "duration_estimate_sec": 10,\n'
    '      "keywords": ["keyword1", "keyword2"]\n'
    "    }}\n"
    "  ]\n"
    "}}\n"
    "\n"
    "=== CRITICAL NARRATION RULES ===\n"
    "- Maximum {max_scenes} scenes\n"
    "- narration_ko MUST be written EXACTLY as it will be read aloud by TTS.\n"
    "- NEVER use parentheses with explanations like '무(武)' or '협(俠)' or '(Spring)'.\n"
    "  Instead, naturally weave explanations into the sentence.\n"
    "  BAD:  '무협은 무(武)와 협(俠)의 합성어로'\n"
    "  GOOD: '무협이란 무술의 무, 의협의 협이 합쳐진 말로'\n"
    "- NEVER use quotation marks like '이것' or \"이것\" around words.\n"
    "- NEVER include English words in narration_ko. Write everything in pure Korean.\n"
    "  BAD:  '한국의 사계절(Four Seasons)은'\n"
    "  GOOD: '한국의 사계절은'\n"
    "- NEVER use abbreviations, symbols, or special characters (%, &, #, *, etc.).\n"
    "- Write numbers as Korean words: '세 가지' not '3가지', '열두 달' not '12달'.\n"
    "- Use natural conversational spoken Korean, as if talking to a friend.\n"
    "- Each narration_ko should be 2-4 sentences, smooth and flowing.\n"
    "- Start with a compelling hook that grabs attention in the first 3 seconds.\n"
    "- End with a warm, memorable closing that invites viewers to subscribe.\n"
    "\n"
    "=== VISUAL PROMPT RULES ===\n"
    "- visual_prompt_en: detailed English scene description for AI image generation.\n"
    "- Describe the scene cinematically: subject, action, setting, lighting, mood.\n"
    "- If people appear, describe: gender, approximate age, clothing, posture, expression.\n"
    "- Maintain visual consistency across scenes (same season, same location style).\n"
    "- NEVER include text or words in the visual description.\n"
    "\n"
    "=== STRUCTURE ===\n"
    "- Scene 1: Attention-grabbing hook with a question or surprising fact.\n"
    "- Scenes 2-{last_scene}: Body content with vivid descriptions and emotional appeal.\n"
    "- Final scene: Warm closing + implicit subscribe encouragement.\n"
    "- Vary pacing: mix short punchy scenes with longer reflective ones.\n"
    "- duration_estimate_sec: estimate based on Korean reading speed (~3.5 chars/sec).\n"
)


class Engine:
    def __init__(self, model: str = "gemini-2.5-flash",
                 max_scenes: int = 8, language: str = "ko",
                 api_key=None, **kwargs):
        self.model = model
        self.max_scenes = max_scenes

        if isinstance(api_key, list):
            self.api_keys = [k for k in api_key if k]
        elif isinstance(api_key, str) and api_key:
            self.api_keys = [api_key]
        else:
            self.api_keys = []

        if not self.api_keys:
            raise RuntimeError("Gemini API key not configured. Edit config.yaml")

    async def generate_blueprint(self, topic: str, output_dir: Path, **kwargs) -> Blueprint:
        prompt = "Topic: " + topic
        system = SYSTEM_PROMPT.format(
            max_scenes=self.max_scenes,
            last_scene=self.max_scenes - 1,
        )

        last_error = None

        for i, key in enumerate(self.api_keys):
            key_label = "KEY_" + str(i + 1) + " (" + key[:8] + "..." + key[-4:] + ")"
            try:
                print("      Trying " + key_label)
                client = genai.Client(api_key=key)

                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=0.7,
                        response_mime_type="application/json",
                    ),
                )

                raw_text = response.text.strip()
                data = json.loads(raw_text)

                scenes = []
                for s in data["scenes"]:
                    # Clean narration before saving
                    narration = self._clean_narration(s["narration_ko"])
                    scenes.append(Scene(
                        scene_id=s["scene_id"],
                        scene_number=s["scene_number"],
                        title=s["title"],
                        narration_ko=narration,
                        visual_prompt_en=s["visual_prompt_en"],
                        duration_estimate_sec=s.get("duration_estimate_sec", 10),
                        keywords=s.get("keywords", []),
                    ))

                blueprint = Blueprint(
                    topic=data["topic"],
                    total_scenes=data["total_scenes"],
                    scenes=scenes,
                    estimated_total_duration_sec=data.get("estimated_total_duration_sec", 0),
                    style_guide=data.get("style_guide", ""),
                )

                out_path = output_dir / "blueprint.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print("      OK with " + key_label)
                return blueprint

            except Exception as e:
                last_error = e
                print("      FAIL " + key_label + ": " + str(e))
                continue

        raise RuntimeError(
            "All " + str(len(self.api_keys)) + " API keys failed. Last error: " + str(last_error)
        )

    def _clean_narration(self, text: str) -> str:
        """Remove artifacts that cause TTS to read unnaturally."""
        import re

        # Remove content in parentheses: 무(武) -> 무, 사계절(Four Seasons) -> 사계절
        text = re.sub(r"\([^)]*\)", "", text)

        # Remove content in square brackets: [참고] -> empty
        text = re.sub(r"\[[^\]]*\]", "", text)

        # Remove various quotation marks wrapping single words
        text = re.sub(r"['\u2018\u2019\u201C\u201D\"]+", "", text)

        # Remove stray special characters
        text = re.sub(r"[#*&%@~^]", "", text)

        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text
