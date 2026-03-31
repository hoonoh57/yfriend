"""
engines/script/gemini_flash.py - Mutable script engine
Gemini API key rotation: tries up to 5 keys sequentially.
"""
from __future__ import annotations

import json, re
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
    '  "style_guide": "consistent visual style description used across ALL scenes",\n'
    '  "character_sheet": "detailed description of recurring characters (age, ethnicity, hair, clothing, build)",\n'
    '  "setting_sheet": "detailed description of the world/era/location style used across scenes",\n'
    '  "scenes": [\n'
    "    {{\n"
    '      "scene_id": "scene_01",\n'
    '      "scene_number": 1,\n'
    '      "title": "scene title in Korean",\n'
    '      "narration_ko": "Korean narration (2-4 sentences, natural spoken style)",\n'
    '      "visual_prompt_en": "Detailed English visual description for AI image generation",\n'
    '      "duration_estimate_sec": 10,\n'
    '      "keywords": ["keyword1", "keyword2"]\n'
    "    }}\n"
    "  ]\n"
    "}}\n"
    "\n"
    "=== CHARACTER & SETTING CONSISTENCY (MOST IMPORTANT) ===\n"
    "- You MUST define character_sheet and setting_sheet FIRST, then reference them in EVERY visual_prompt_en.\n"
    "- character_sheet example: 'A young East Asian man in his late 20s, lean athletic build, "
    "long black hair tied in a topknot, wearing a faded gray hanfu robe with a dark sash, "
    "carrying a worn leather-wrapped jian sword on his back'\n"
    "- setting_sheet example: 'Ancient Song Dynasty China, misty mountain valleys, bamboo forests, "
    "weathered stone temples, dirt paths, muted earth tones with jade green accents'\n"
    "- EVERY visual_prompt_en MUST start by describing the SAME character with the SAME appearance.\n"
    "- Characters must NEVER change ethnicity, age, clothing style, or hairstyle between scenes.\n"
    "- If the topic is about ancient China/Korea/Japan, characters MUST be East Asian wearing period-accurate clothing.\n"
    "- If the topic is about modern Korea, characters MUST be Korean wearing modern Korean fashion.\n"
    "- NEVER mix time periods: no modern clothing in historical scenes, no Western faces in Asian stories.\n"
    "- Maintain the SAME color palette, lighting mood, and art direction across all scenes.\n"
    "\n"
    "=== VISUAL PROMPT STRUCTURE (for each scene) ===\n"
    "Every visual_prompt_en must follow this exact structure:\n"
    "1. [Character]: Repeat the character description from character_sheet\n"
    "2. [Action]: What the character is doing in this specific scene\n"
    "3. [Setting]: Reference setting_sheet + scene-specific location details\n"
    "4. [Lighting/Mood]: Consistent lighting style with scene-specific variations\n"
    "5. [Camera]: Camera angle and composition\n"
    "Example: 'A young East Asian man in his late 20s with long black hair in a topknot, "
    "wearing a faded gray hanfu robe, stands at the edge of a misty cliff overlooking a bamboo valley. "
    "He grips his worn jian sword, wind blowing his robe. Ancient Song Dynasty China setting, "
    "dawn light breaking through fog, warm golden rays. Wide shot, low angle, cinematic composition.'\n"
    "\n"
    "=== CRITICAL NARRATION RULES ===\n"
    "- Maximum {max_scenes} scenes\n"
    "- narration_ko MUST be written EXACTLY as it will be read aloud by TTS.\n"
    "- NEVER use parentheses with explanations like '무(武)' or '협(俠)' or '(Spring)'.\n"
    "  Instead, naturally weave explanations into the sentence.\n"
    "  BAD:  '무협은 무(武)와 협(俠)의 합성어로'\n"
    "  GOOD: '무협이란 무술의 무, 의협의 협이 합쳐진 말로'\n"
    "- NEVER use quotation marks around words.\n"
    "- NEVER include English words in narration_ko. Write everything in pure Korean.\n"
    "- NEVER use abbreviations, symbols, or special characters.\n"
    "- Write numbers as Korean words.\n"
    "- Use natural conversational spoken Korean.\n"
    "- Each narration_ko should be 2-4 sentences, smooth and flowing.\n"
    "- Start with a compelling hook. End with a warm closing.\n"
    "\n"
    "=== STRUCTURE ===\n"
    "- Scene 1: Attention-grabbing hook.\n"
    "- Scenes 2-{last_scene}: Body with vivid descriptions and emotional appeal.\n"
    "- Final scene: Warm closing.\n"
    "- duration_estimate_sec: based on Korean reading speed (~3.5 chars/sec).\n"
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

                # Extract consistency sheets
                char_sheet = data.get("character_sheet", "")
                setting_sheet = data.get("setting_sheet", "")
                consistency_prefix = self._build_consistency_prefix(char_sheet, setting_sheet)

                scenes = []
                for s in data["scenes"]:
                    narration = self._clean_narration(s["narration_ko"])
                    # Prepend consistency info to visual prompt if not already included
                    visual = s["visual_prompt_en"]
                    if consistency_prefix and consistency_prefix[:30].lower() not in visual[:50].lower():
                        visual = consistency_prefix + " " + visual

                    scenes.append(Scene(
                        scene_id=s["scene_id"],
                        scene_number=s["scene_number"],
                        title=s["title"],
                        narration_ko=narration,
                        visual_prompt_en=visual,
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

                # Save full data including sheets
                out_path = output_dir / "blueprint.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print("      OK with " + key_label)
                if char_sheet:
                    print(f"      [캐릭터] {char_sheet[:80]}...")
                if setting_sheet:
                    print(f"      [배경설정] {setting_sheet[:80]}...")
                return blueprint

            except Exception as e:
                last_error = e
                print("      FAIL " + key_label + ": " + str(e))
                continue

        raise RuntimeError(
            "All " + str(len(self.api_keys)) + " API keys failed. Last error: " + str(last_error)
        )

    def _build_consistency_prefix(self, char_sheet: str, setting_sheet: str) -> str:
        """Build a prefix from character/setting sheets to prepend to every visual prompt."""
        parts = []
        if char_sheet:
            parts.append(char_sheet.strip().rstrip(".") + ".")
        if setting_sheet:
            parts.append(setting_sheet.strip().rstrip(".") + ".")
        return " ".join(parts)

    def _clean_narration(self, text: str) -> str:
        """Remove artifacts that cause TTS to read unnaturally."""
        # Remove content in parentheses
        text = re.sub(r"\([^)]*\)", "", text)
        # Remove content in square brackets
        text = re.sub(r"\[[^\]]*\]", "", text)
        # Remove various quotation marks
        text = re.sub(r"['\"\u2018\u2019\u201C\u201D]", "", text)
        # Remove stray special characters
        text = re.sub(r"[#*&%@~^]", "", text)
        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text).strip()
        return text
