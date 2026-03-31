"""
engines/assembly/ffmpeg_assembly.py – Assembly engine with synced subtitles
Sprint 2.5: keyframe images + word-synced ASS subtitles (1-2 lines at a time)
"""
from __future__ import annotations
import asyncio, json, os, re, subprocess
from pathlib import Path
from core.models import Part, PartType, Scene, Blueprint, Origin


class Engine:
    def __init__(
        self,
        font_size: int = 42,
        font_color: str = "white",
        bg_color: str = "black",
        subtitle_alignment: int = 2,
        max_chars_per_line: int = 20,
        motion_effect: str = "none",
        transition: str = "none",
        transition_duration: float = 0.5,
        **kwargs,
    ):
        self.font_size = font_size
        self.font_color = font_color
        self.bg_color = bg_color
        self.alignment = subtitle_alignment
        self.max_chars = max_chars_per_line
        self.motion = motion_effect
        self.transition = transition
        self.transition_dur = transition_duration

    async def assemble(
        self,
        blueprint: Blueprint,
        voice_dir: Path,
        output_dir: Path,
        keyframe_dir: Path | None = None,
    ) -> Part:
        voice_dir = Path(voice_dir)
        output_dir = Path(output_dir)
        keyframe_dir = Path(keyframe_dir) if keyframe_dir else None
        output_dir.mkdir(parents=True, exist_ok=True)

        scene_clips = []

        for scene in blueprint.scenes:
            sn = scene.scene_number
            mp3 = voice_dir / f"scene_{sn:02d}_narration.mp3"
            if not mp3.exists():
                print(f"      [WARN] {mp3.name} 없음, 건너뜀")
                continue

            duration_ms = await self._get_audio_duration_ms(mp3)
            duration_sec = duration_ms / 1000.0

            # Generate synced ASS subtitle
            ts_file = voice_dir / f"scene_{sn:02d}_narration.timestamps.json"
            ass_path = output_dir / f"scene_{sn:02d}.ass"

            if ts_file.exists():
                self._generate_synced_ass(scene, ts_file, ass_path, duration_sec)
            else:
                self._generate_simple_ass(scene, ass_path, duration_sec)

            # Find keyframe image
            img_path = None
            if keyframe_dir:
                candidate = keyframe_dir / f"scene_{sn:02d}_keyframe.png"
                if candidate.exists():
                    img_path = candidate

            clip_path = output_dir / f"scene_{sn:02d}_clip.mp4"
            await self._make_scene_clip(mp3, ass_path, img_path, clip_path, duration_sec)

            if clip_path.exists() and clip_path.stat().st_size > 0:
                scene_clips.append(clip_path)

        if not scene_clips:
            raise RuntimeError("사용 가능한 나레이션 파일 없음")

        final_path = output_dir / "final_prototype.mp4"
        await self._concat_clips(scene_clips, final_path)

        return Part(
            part_type=PartType.FINAL_VIDEO,
            scene_id="all",
            file_path=final_path,
            origin=Origin.AUTO,
            engine_used="ffmpeg_assembly",
            prompt_used=blueprint.topic,
        )

    # ─────────── Synced ASS (word-boundary timestamps) ───────────
    def _generate_synced_ass(
        self, scene: Scene, ts_file: Path, ass_path: Path, total_dur: float
    ):
        """Group words into short phrases (1-2 lines) and create timed ASS events."""
        with open(ts_file, "r", encoding="utf-8") as f:
            words = json.load(f)

        if not words:
            self._generate_simple_ass(scene, ass_path, total_dur)
            return

        # Group words into subtitle chunks
        chunks = []
        current_text = ""
        chunk_start_ms = words[0]["offset_ms"]

        for i, w in enumerate(words):
            candidate = (current_text + w["text"]).strip()

            # Break at punctuation or max length
            should_break = False
            if len(candidate) > self.max_chars:
                should_break = True
            elif w["text"].rstrip().endswith((",", ".", "!", "?", "。", "，", "!", "?", "~")):
                should_break = True  # break AFTER this word

            if should_break and current_text.strip():
                # If break due to length, save current WITHOUT this word
                if len(candidate) > self.max_chars:
                    end_ms = w["offset_ms"]
                    chunks.append({
                        "text": current_text.strip(),
                        "start_ms": chunk_start_ms,
                        "end_ms": end_ms,
                    })
                    current_text = w["text"]
                    chunk_start_ms = w["offset_ms"]
                else:
                    # Break after punctuation: include this word
                    current_text = candidate
                    end_ms = w["offset_ms"] + w["duration_ms"]
                    chunks.append({
                        "text": current_text.strip(),
                        "start_ms": chunk_start_ms,
                        "end_ms": end_ms,
                    })
                    current_text = ""
                    if i + 1 < len(words):
                        chunk_start_ms = words[i + 1]["offset_ms"]
            else:
                current_text = candidate

        # Remaining text
        if current_text.strip():
            end_ms = words[-1]["offset_ms"] + words[-1]["duration_ms"]
            chunks.append({
                "text": current_text.strip(),
                "start_ms": chunk_start_ms,
                "end_ms": min(end_ms, total_dur * 1000),
            })

        # Write ASS file
        self._write_ass_file(ass_path, chunks)

    def _generate_simple_ass(self, scene: Scene, ass_path: Path, total_dur: float):
        """Fallback: split narration into sentence-level chunks evenly."""
        text = scene.narration_ko
        sentences = re.split(r"(?<=[.!?。，,~])\s*", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            sentences = [text]

        dur_per = (total_dur * 1000) / len(sentences)
        chunks = []
        for i, s in enumerate(sentences):
            chunks.append({
                "text": s,
                "start_ms": i * dur_per,
                "end_ms": (i + 1) * dur_per,
            })

        self._write_ass_file(ass_path, chunks)

    def _write_ass_file(self, ass_path: Path, chunks: list[dict]):
        lines = []
        lines.append("[Script Info]")
        lines.append("ScriptType: v4.00+")
        lines.append("PlayResX: 1920")
        lines.append("PlayResY: 1080")
        lines.append("WrapStyle: 0")
        lines.append("")
        lines.append("[V4+ Styles]")
        lines.append(
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding"
        )
        lines.append(
            f"Style: Default,Malgun Gothic,{self.font_size},"
            f"&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
            f"1,0,0,0,100,100,0,0,1,3,1,"
            f"{self.alignment},40,40,60,1"
        )
        lines.append("")
        lines.append("[Events]")
        lines.append("Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text")

        for c in chunks:
            start = self._ms_to_ass_time(c["start_ms"])
            end = self._ms_to_ass_time(c["end_ms"])
            text = self._wrap_text(c["text"], self.max_chars)
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        ass_path.write_text("\n".join(lines), encoding="utf-8")


    def _wrap_text(self, text: str, max_len: int) -> str:
        """Wrap Korean text with \\N for ASS line breaks."""
        if len(text) <= max_len:
            return text
        lines = []
        while len(text) > max_len:
            # Find a natural break point
            bp = -1
            for ch in (",", " ", ".", "을", "를", "이", "가", "은", "는", "에", "의", "로", "고"):
                idx = text.rfind(ch, 0, max_len + 1)
                if idx > bp:
                    bp = idx
            if bp <= 0:
                bp = max_len
            else:
                bp += 1
            lines.append(text[:bp].strip())
            text = text[bp:].strip()
        if text:
            lines.append(text)
        return "\\N".join(lines)

    # ─────────── Scene clip creation ───────────
    async def _make_scene_clip(
        self, mp3: Path, ass: Path, img: Path | None, out: Path, dur: float
    ):
        ass_str = str(ass).replace("\\", "/").replace(":", "\\\\:")

        if img and img.exists():
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(img),
                "-i", str(mp3),
                "-filter_complex",
                f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,"
                f"ass='{ass_str}'[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-t", str(dur + 0.5),
                str(out),
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s=1920x1080:d={dur + 0.5}:r=24",
                "-i", str(mp3),
                "-filter_complex",
                f"[0:v]ass='{ass_str}'[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                str(out),
            ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                print(f"      [WARN] ffmpeg 실패, 폴백: {stderr.decode(errors='replace')[-200:]}")
                await self._make_fallback_clip(mp3, out, dur)
        except Exception as e:
            print(f"      [WARN] ffmpeg 오류: {e}")
            await self._make_fallback_clip(mp3, out, dur)


    async def _make_fallback_clip(self, mp3: Path, out: Path, dur: float):
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=1920x1080:d={dur + 0.5}:r=24",
            "-i", str(mp3),
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", str(out),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    # ─────────── Concat ───────────
    async def _concat_clips(self, clips: list[Path], output: Path):
        list_file = output.parent / "concat_list.txt"
        list_file.write_text(
            "\n".join(f"file '{c.name}'" for c in clips),
            encoding="utf-8",
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy", str(output),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            # Re-encode fallback
            cmd2 = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(list_file),
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac", "-b:a", "128k",
                str(output),
            ]
            proc2 = await asyncio.create_subprocess_exec(
                *cmd2, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc2.communicate()

    # ─────────── Helpers ───────────
    async def _get_audio_duration_ms(self, path: Path) -> float:
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration", "-of", "json", str(path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode())
        return float(data["format"]["duration"]) * 1000

    def _ms_to_ass_time(self, ms: float) -> str:
        total_s = ms / 1000.0
        h = int(total_s // 3600)
        m = int((total_s % 3600) // 60)
        s = total_s % 60
        return f"{h}:{m:02d}:{s:05.2f}"