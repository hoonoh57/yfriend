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
    "You are a YouTube video script writer.\n"
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
    "Rules:\n"
    "- Maximum {max_scenes} scenes\n"
    "- narration_ko: natural spoken Korean\n"
    "- visual_prompt_en: detailed English image description\n"
    "- duration_estimate_sec: based on narration reading time\n"
    "- Structure: hook intro -> body -> closing CTA\n"
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
        system = SYSTEM_PROMPT.format(max_scenes=self.max_scenes)

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
                    scenes.append(Scene(
                        scene_id=s["scene_id"],
                        scene_number=s["scene_number"],
                        title=s["title"],
                        narration_ko=s["narration_ko"],
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
