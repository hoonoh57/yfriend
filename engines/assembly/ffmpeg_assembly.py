"""
engines/assembly/ffmpeg_assembly.py - Mutable assembly engine
Sprint 2.5: 키프레임 이미지 + 문장 단위 자막 동기화
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path
from core.models import Blueprint, Part, PartType, Scene


class Engine:
    def __init__(
        self,
        font_size: int = 28,
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
        self.motion_effect = motion_effect
        self.transition = transition
        self.transition_duration = transition_duration
        self.resolution = "1920x1080"
        self.fps = 24

    async def assemble(
        self, blueprint: Blueprint, voice_dir: Path, output_dir: Path,
        keyframe_dir: Path = None, **kwargs
    ) -> Part:
        voice_dir = Path(voice_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        scene_data = []
        for scene in blueprint.scenes:
            mp3_file = voice_dir / f"scene_{scene.scene_number:02d}_narration.mp3"
            if not mp3_file.exists():
                print(f"      WARN: {mp3_file.name} 없음, 건너뜀")
                continue

            duration_ms = self._get_audio_duration_ms(mp3_file)

            # 타임스탬프 파일 확인
            ts_file = mp3_file.with_suffix(".timestamps.json")
            timestamps = None
            if ts_file.exists():
                with open(ts_file, "r", encoding="utf-8") as f:
                    timestamps = json.load(f)

            # 키프레임 이미지 확인
            keyframe_path = None
            if keyframe_dir:
                kf = Path(keyframe_dir) / f"scene_{scene.scene_number:02d}_keyframe.png"
                if kf.exists():
                    keyframe_path = kf

            scene_data.append({
                "scene": scene,
                "mp3": mp3_file,
                "duration_ms": duration_ms,
                "duration_sec": duration_ms / 1000.0,
                "keyframe": keyframe_path,
                "timestamps": timestamps,
            })

        if not scene_data:
            raise RuntimeError("사용 가능한 나레이션 파일 없음")

        # 장면별 클립 생성
        clip_files = []
        for idx, sd in enumerate(scene_data):
            clip_path = output_dir / f"_clip_{idx:02d}.mp4"
            self._make_scene_clip(sd, clip_path)
            if clip_path.exists():
                clip_files.append(clip_path)

        if not clip_files:
            raise RuntimeError("클립 생성 실패")

        # 클립 연결
        final_path = output_dir / "final_prototype.mp4"
        self._concat_clips(clip_files, final_path)

        # 임시 클립 삭제
        for cf in clip_files:
            cf.unlink(missing_ok=True)

        return Part(
            part_type=PartType.MOTION_CLIP,
            file_path=final_path,
            scene_id="final",
            metadata={"scenes": len(scene_data)},
        )

    def _make_scene_clip(self, scene_data: dict, output_path: Path):
        mp3 = scene_data["mp3"]
        duration = scene_data["duration_sec"]
        keyframe = scene_data["keyframe"]
        scene: Scene = scene_data["scene"]
        timestamps = scene_data["timestamps"]

        # 자막 생성: 타임스탬프가 있으면 문장 단위 동기화, 없으면 전체 표시
        ass_path = output_path.with_suffix(".ass")
        if timestamps and timestamps.get("words"):
            self._generate_synced_ass(timestamps, duration, ass_path)
        else:
            self._generate_simple_ass(scene.narration_ko, duration, ass_path)

        w, h = self.resolution.split("x")
        ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

        if keyframe:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(keyframe),
                "-i", str(mp3),
                "-shortest",
                "-vf", (
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={self.bg_color},"
                    f"ass='{ass_escaped}'"
                ),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-r", str(self.fps),
                str(output_path),
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c={self.bg_color}:s={self.resolution}:r={self.fps}",
                "-i", str(mp3),
                "-shortest",
                "-vf", f"ass='{ass_escaped}'",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            print(f"      FFmpeg 클립 에러: {stderr[:200]}")
            self._make_fallback_clip(mp3, keyframe, output_path)

        ass_path.unlink(missing_ok=True)

    def _generate_synced_ass(self, timestamps: dict, total_duration: float, ass_path: Path):
        """단어 타임스탬프 기반 문장 단위 동기화 자막"""
        words = timestamps.get("words", [])
        if not words:
            self._generate_simple_ass(timestamps.get("narration", ""), total_duration, ass_path)
            return

        # 단어들을 문장/구 단위로 그룹핑
        segments = self._group_words_to_segments(words)

        # ASS 이벤트 생성
        events = []
        for seg in segments:
            start = self._ms_to_ass_time(seg["start_ms"])
            end = self._ms_to_ass_time(seg["end_ms"])
            text = self._wrap_text(seg["text"])
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        ass_content = self._build_ass_header() + "\n".join(events) + "\n"
        ass_path.write_text(ass_content, encoding="utf-8-sig")

    def _group_words_to_segments(self, words: list[dict]) -> list[dict]:
        """단어 타임스탬프를 문장/구 단위로 그룹핑"""
        segments = []
        current_text = ""
        current_start = None

        for i, word in enumerate(words):
            w_text = word["text"]
            w_start = word["offset_ms"]
            w_end = w_start + word["duration_ms"]

            if current_start is None:
                current_start = w_start

            current_text += w_text

            # 분할 조건: 문장 끝(. ! ? ~), 쉼표, 또는 글자수 초과
            is_sentence_end = any(current_text.rstrip().endswith(p) for p in [".", "!", "?", "~", "다.", "요.", "죠.", "까?"])
            is_comma = current_text.rstrip().endswith(",") or current_text.rstrip().endswith("、")
            is_too_long = len(current_text.strip()) >= self.max_chars * 2
            is_last = (i == len(words) - 1)

            if is_sentence_end or is_comma or is_too_long or is_last:
                text = current_text.strip()
                if text:
                    # 여유 시간 추가 (다음 단어 시작까지 또는 +300ms)
                    if i + 1 < len(words):
                        next_start = words[i + 1]["offset_ms"]
                        end_time = min(next_start, w_end + 300)
                    else:
                        end_time = w_end + 500

                    segments.append({
                        "text": text,
                        "start_ms": current_start,
                        "end_ms": end_time,
                    })
                current_text = ""
                current_start = None

        return segments

    def _generate_simple_ass(self, narration: str, duration_sec: float, ass_path: Path):
        """타임스탬프 없을 때 전체 표시 (폴백)"""
        wrapped = self._wrap_text(narration)
        start = self._ms_to_ass_time(0)
        end = self._ms_to_ass_time(int(duration_sec * 1000))
        events = f"Dialogue: 0,{start},{end},Default,,0,0,0,,{wrapped}"
        ass_content = self._build_ass_header() + events + "\n"
        ass_path.write_text(ass_content, encoding="utf-8-sig")

    def _build_ass_header(self) -> str:
        # alignment: 2=하단중앙, 5=화면중앙, 8=상단중앙
        margin_v = 50 if self.alignment == 2 else 30
        return f"""[Script Info]
Title: yFriend Subtitle
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Malgun Gothic,{self.font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,{self.alignment},30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def _wrap_text(self, text: str) -> str:
        if len(text) <= self.max_chars:
            return text

        lines = []
        current = ""
        particles = "은는이가을를에서도로의며고와과"

        for char in text:
            current += char
            if len(current) >= self.max_chars:
                cut_pos = -1
                for j in range(len(current) - 1, max(0, len(current) - 8), -1):
                    if current[j] in particles and j < len(current) - 1:
                        cut_pos = j + 1
                        break
                if cut_pos > 0:
                    lines.append(current[:cut_pos].strip())
                    current = current[cut_pos:]
                else:
                    space_pos = current.rfind(" ", 0, len(current))
                    if space_pos > 0:
                        lines.append(current[:space_pos].strip())
                        current = current[space_pos + 1:]
                    else:
                        lines.append(current.strip())
                        current = ""

        if current.strip():
            lines.append(current.strip())

        return "\\N".join(lines)

    def _make_fallback_clip(self, mp3: Path, keyframe, output_path: Path):
        w, h = self.resolution.split("x")
        if keyframe:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(keyframe),
                "-i", str(mp3), "-shortest",
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={self.bg_color}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-r", str(self.fps),
                str(output_path),
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c={self.bg_color}:s={self.resolution}:r={self.fps}",
                "-i", str(mp3), "-shortest",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        except Exception as e2:
            print(f"      폴백도 실패: {e2}")

    def _concat_clips(self, clip_files: list[Path], output_path: Path):
        concat_list = output_path.with_name("_concat_list.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for clip in clip_files:
                escaped = str(clip.resolve()).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        except subprocess.CalledProcessError:
            cmd_fb = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ]
            subprocess.run(cmd_fb, capture_output=True, check=True, timeout=300)

        concat_list.unlink(missing_ok=True)

    def _get_audio_duration_ms(self, audio_path: Path) -> int:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(audio_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return int(float(result.stdout.strip()) * 1000)
        except Exception:
            return 10000

    def _ms_to_ass_time(self, ms: int) -> str:
        h = ms // 3600000
        m = (ms % 3600000) // 60000
        s = (ms % 60000) // 1000
        cs = (ms % 1000) // 10
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
