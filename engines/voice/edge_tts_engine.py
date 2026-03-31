"""
engines/voice/edge_tts_engine.py - Mutable voice engine
"""
from __future__ import annotations

from pathlib import Path

import edge_tts

from core.models import Origin, Part, PartType, Scene


class Engine:
    def __init__(self, voice: str = "ko-KR-SunHiNeural",
                 rate: str = "+0%", **kwargs):
        self.voice = voice
        self.rate = rate

    async def generate_narration(self, scene: Scene, output_path: Path, **kwargs) -> Part:
        communicate = edge_tts.Communicate(
            text=scene.narration_ko,
            voice=self.voice,
            rate=self.rate,
        )
        await communicate.save(str(output_path))

        return Part(
            part_type=PartType.NARRATION,
            scene_id=scene.scene_id,
            file_path=output_path,
            origin=Origin.AUTO,
            engine_used=f"edge_tts/{self.voice}",
            prompt_used=scene.narration_ko,
        )