"""
engines/voice/edge_tts_engine.py – Edge TTS with word-level timestamps
Includes narration text cleaning to prevent TTS artifacts.
"""
from __future__ import annotations
import asyncio, json, re
from pathlib import Path
import edge_tts
from core.models import Part, PartType, Origin, Scene


class Engine:
    def __init__(self, voice: str = "ko-KR-SunHiNeural", rate: str = "+0%", **kwargs):
        self.voice = voice
        self.rate = rate

    async def generate_narration(self, scene: Scene, output_path: Path) -> Part:
        output_path = Path(output_path)

        # Clean text for TTS
        clean_text = self._clean_for_tts(scene.narration_ko)

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=self.voice,
            rate=self.rate,
        )

        audio_chunks = []
        word_boundaries = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                wb_text = chunk["text"].strip()
                # Filter out junk tokens: pure punctuation, quotes, single chars
                if self._is_valid_subtitle_text(wb_text):
                    word_boundaries.append({
                        "text": wb_text,
                        "offset_ms": chunk["offset"] / 10000,
                        "duration_ms": chunk["duration"] / 10000,
                    })

        audio_data = b"".join(audio_chunks)
        output_path.write_bytes(audio_data)

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
            prompt_used=clean_text[:100],
            metadata={"timestamps_file": str(ts_path)},
        )

    def _clean_for_tts(self, text: str) -> str:
        """Clean narration text so TTS reads naturally."""
        # Remove parenthesized content: 무(武) -> 무
        text = re.sub(r"\([^)]*\)", "", text)
        # Remove bracketed content: [참고] -> empty
        text = re.sub(r"\[[^\]]*\]", "", text)
        # Remove all quotation marks (prevents "따옴표" being read)
        text = re.sub(r"['\"\u2018\u2019\u201C\u201D\u300C\u300D\u300E\u300F]", "", text)
        # Remove stray symbols
        text = re.sub(r"[#*&%@~^]", "", text)
        # Normalize ellipsis to pause
        text = re.sub(r"\.{2,}", ".", text)
        # Collapse multiple spaces/newlines
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _is_valid_subtitle_text(self, text: str) -> bool:
        """Filter out tokens that shouldn't become subtitle chunks."""
        if not text:
            return False
        # Reject pure punctuation / quotes / symbols
        cleaned = re.sub(r"[.,!?\-;:'\"\u2018\u2019\u201C\u201D\s]", "", text)
        if not cleaned:
            return False
        # Reject single character tokens (usually artifacts)
        if len(cleaned) <= 1 and not cleaned.isalnum():
            return False
        return True
