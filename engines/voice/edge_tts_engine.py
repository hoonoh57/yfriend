"""
engines/voice/edge_tts_engine.py – Edge TTS with word-level timestamps
"""
from __future__ import annotations
import asyncio, json
from pathlib import Path
import edge_tts
from core.models import Part, PartType, Origin, Scene


class Engine:
    def __init__(self, voice: str = "ko-KR-SunHiNeural", rate: str = "+0%", **kwargs):
        self.voice = voice
        self.rate = rate

    async def generate_narration(self, scene: Scene, output_path: Path) -> Part:
        output_path = Path(output_path)
        communicate = edge_tts.Communicate(
            text=scene.narration_ko,
            voice=self.voice,
            rate=self.rate,
        )

        audio_chunks = []
        word_boundaries = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "text": chunk["text"],
                    "offset_ms": chunk["offset"] / 10000,  # 100ns -> ms
                    "duration_ms": chunk["duration"] / 10000,
                })

        # Save audio
        audio_data = b"".join(audio_chunks)
        output_path.write_bytes(audio_data)

        # Save timestamps
        ts_path = output_path.with_suffix(".timestamps.json")
        ts_path.write_text(
            json.dumps(word_boundaries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return Part(
            part_type=PartType.NARRATION,
            scene_id=scene.scene_id,
            file_path=output_path,
            origin=Origin.AUTO,
            engine_used=f"edge_tts/{self.voice}",
            prompt_used=scene.narration_ko[:100],
            metadata={"timestamps_file": str(ts_path)},
        )