"""
engines/assembly/ffmpeg_assembly.py - Mutable assembly engine
Sprint 2.5: 키프레임 이미지 배경 지원
장면별 이미지가 있으면 이미지 배경, 없으면 검은 배경
"""
from __future__ import annotations
import asyncio
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
        **kwargs,
    ):
        self.font_size = font_size
        self.font_color = font_color
        self.bg_color = bg_color
        self.resolution = "1920x1080"
        self.fps = 24

    async def assemble(
        self, blueprint: Blueprint, voice_dir: Path, output_dir: Path,
        keyframe_dir: Path = None, **kwargs
    ) -> Part:
        voice_dir = Path(voice_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. 장면별 나레이션 파일 수집 및 길이 측정
        scene_data = []
        for scene in blueprint.scenes:
            mp3_file = voice_dir / f"scene_{scene.scene_number:02d}_narration.mp3"
            if not mp3_file.exists():
                print(f"      WARN: {mp3_file.name} 없음, 건너뜀")
                continue

            duration_ms = self._get_audio_duration_ms(mp3_file)
            duration_sec = duration_ms / 1000.0

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
                "duration_sec": duration_sec,
                "keyframe": keyframe_path,
            })

        if not scene_data:
            raise RuntimeError("사용 가능한 나레이션 파일 없음")

        # 2. 장면별 클립 생성
        clip_files = []
        for idx, sd in enumerate(scene_data):
            clip_path = output_dir / f"_clip_{idx:02d}.mp4"
            self._make_scene_clip(sd, clip_path)
            if clip_path.exists():
                clip_files.append(clip_path)

        if not clip_files:
            raise RuntimeError("클립 생성 실패")

        # 3. 클립 연결 (concat)
        final_path = output_dir / "final_prototype.mp4"
        self._concat_clips(clip_files, final_path)

        # 4. 임시 클립 삭제
        for cf in clip_files:
            cf.unlink(missing_ok=True)

        return Part(
            part_type=PartType.MOTION_CLIP,
            file_path=final_path,
            scene_id="final",
            metadata={"scenes": len(scene_data)},
        )

    def _make_scene_clip(self, scene_data: dict, output_path: Path):
        """개별 장면 클립 생성 (이미지 배경 또는 검은 배경)"""
        mp3 = scene_data["mp3"]
        duration = scene_data["duration_sec"]
        keyframe = scene_data["keyframe"]
        scene: Scene = scene_data["scene"]

        # ASS 자막 생성
        ass_path = output_path.with_suffix(".ass")
        self._generate_scene_ass(scene.narration_ko, duration, ass_path)

        w, h = self.resolution.split("x")

        if keyframe:
            # 키프레임 이미지 배경 사용
            # 이미지를 loop하여 나레이션 길이만큼 영상 생성
            ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(keyframe),
                "-i", str(mp3),
                "-shortest",
                "-vf", (
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={self.bg_color},"
                    f"ass='{ass_escaped}'"
                ),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-r", str(self.fps),
                str(output_path),
            ]
        else:
            # 검은 배경
            ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
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
            # 폴백: 자막 없이 시도
            self._make_fallback_clip(mp3, keyframe, duration, output_path)

        # ASS 임시파일 삭제
        ass_path.unlink(missing_ok=True)

    def _make_fallback_clip(self, mp3: Path, keyframe, duration: float, output_path: Path):
        """자막 없이 클립 생성 (폴백)"""
        w, h = self.resolution.split("x")
        if keyframe:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(keyframe),
                "-i", str(mp3),
                "-shortest",
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
                "-i", str(mp3),
                "-shortest",
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
        """장면 클립들을 하나로 연결"""
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
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            print(f"      Concat 에러: {stderr[:200]}")
            # 폴백: 재인코딩으로 concat
            cmd_fallback = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                str(output_path),
            ]
            subprocess.run(cmd_fallback, capture_output=True, check=True, timeout=300)

        concat_list.unlink(missing_ok=True)

    def _generate_scene_ass(self, narration: str, duration_sec: float, ass_path: Path):
        """단일 장면용 ASS 자막 생성"""
        wrapped = self._wrap_text(narration, max_chars=25)
        start_time = self._sec_to_ass_time(0)
        end_time = self._sec_to_ass_time(duration_sec)

        ass_content = f"""[Script Info]
Title: yFriend Scene Subtitle
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Malgun Gothic,{self.font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,5,30,30,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{wrapped}
"""
        ass_path.write_text(ass_content, encoding="utf-8-sig")

    def _wrap_text(self, text: str, max_chars: int = 25) -> str:
        """한국어 자연스러운 줄바꿈"""
        if len(text) <= max_chars:
            return text

        lines = []
        current = ""
        particles = "은는이가을를에서도로의며고와과"

        for char in text:
            current += char
            if len(current) >= max_chars:
                # 조사 뒤에서 자르기
                cut_pos = -1
                for j in range(len(current) - 1, max(0, len(current) - 8), -1):
                    if current[j] in particles and j < len(current) - 1:
                        cut_pos = j + 1
                        break
                if cut_pos > 0:
                    lines.append(current[:cut_pos].strip())
                    current = current[cut_pos:]
                else:
                    # 공백에서 자르기
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

    def _get_audio_duration_ms(self, audio_path: Path) -> int:
        """ffprobe로 오디오 길이(ms) 측정"""
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
            return 10000  # 기본 10초

    def _sec_to_ass_time(self, seconds: float) -> str:
        """초 -> ASS 타임코드 (H:MM:SS.cc)"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
