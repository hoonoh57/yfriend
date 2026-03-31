"""
engines/voice/edge_tts_engine.py - Mutable voice engine
나레이션 생성 + 단어별 타임스탬프 저장 (자막 동기화용)
"""
from __future__ import annotations

import json
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

        # 단어별 타임스탬프 수집
        timestamps = []
        audio_chunks = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                timestamps.append({
                    "text": chunk["text"],
                    "offset_ms": chunk["offset"] // 10000,  # 100ns -> ms
                    "duration_ms": chunk["duration"] // 10000,
                })

        # 오디오 저장
        with open(output_path, "wb") as f:
            for c in audio_chunks:
                f.write(c)

        # 타임스탬프 JSON 저장 (자막 동기화용)
        ts_path = output_path.with_suffix(".timestamps.json")
        with open(ts_path, "w", encoding="utf-8") as f:
            json.dump({
                "scene_id": scene.scene_id,
                "narration": scene.narration_ko,
                "words": timestamps,
            }, f, ensure_ascii=False, indent=2)

        return Part(
            part_type=PartType.NARRATION,
            scene_id=scene.scene_id,
            file_path=output_path,
            origin=Origin.AUTO,
            engine_used=f"edge_tts/{self.voice}",
            prompt_used=scene.narration_ko,
            metadata={"timestamps_file": str(ts_path)},
        )
