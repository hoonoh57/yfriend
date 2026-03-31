"""프로젝트 데이터 모델 - 트랙, 클립, 이펙트를 관리"""
from __future__ import annotations
import json, uuid, copy
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ClipEffect:
    effect_type: str = ""          # "fade_in", "fade_out", "kenburns", "color_filter"
    params: dict = field(default_factory=dict)


@dataclass
class Clip:
    clip_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    file_path: str = ""            # 원본 파일 경로
    track_id: str = ""
    start_frame: float = 0.0       # 타임라인 상 시작 (초)
    duration: float = 5.0          # 클립 길이 (초)
    in_point: float = 0.0          # 소스 내 시작점
    out_point: float = 0.0         # 소스 내 끝점
    clip_type: str = "video"       # "video", "image", "audio", "text", "bgm"
    volume: float = 1.0
    opacity: float = 1.0
    effects: list[ClipEffect] = field(default_factory=list)
    text_content: str = ""         # text 클립인 경우
    text_style: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class Track:
    track_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "Track"
    track_type: str = "video"      # "video", "audio", "text", "bgm"
    clips: list[Clip] = field(default_factory=list)
    muted: bool = False
    locked: bool = False
    visible: bool = True
    height: int = 60

    def add_clip(self, clip: Clip):
        clip.track_id = self.track_id
        self.clips.append(clip)
        self.clips.sort(key=lambda c: c.start_frame)

    def remove_clip(self, clip_id: str):
        self.clips = [c for c in self.clips if c.clip_id != clip_id]

    @property
    def end_time(self) -> float:
        if not self.clips:
            return 0.0
        return max(c.start_frame + c.duration for c in self.clips)


@dataclass
class ProjectModel:
    project_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Untitled"
    width: int = 1920
    height: int = 1080
    fps: float = 25.0
    tracks: list[Track] = field(default_factory=list)
    project_dir: str = ""
    topic: str = ""

    @property
    def total_duration(self) -> float:
        if not self.tracks:
            return 0.0
        return max(t.end_time for t in self.tracks)

    def add_track(self, track: Track):
        self.tracks.append(track)

    def remove_track(self, track_id: str):
        self.tracks = [t for t in self.tracks if t.track_id != track_id]

    def get_track(self, track_id: str) -> Optional[Track]:
        for t in self.tracks:
            if t.track_id == track_id:
                return t
        return None

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        for t in self.tracks:
            for c in t.clips:
                if c.clip_id == clip_id:
                    return c
        return None

    def save(self, path: Path):
        data = {
            "project_id": self.project_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "project_dir": self.project_dir,
            "topic": self.topic,
            "tracks": [],
        }
        for t in self.tracks:
            td = {
                "track_id": t.track_id,
                "name": t.name,
                "track_type": t.track_type,
                "muted": t.muted,
                "locked": t.locked,
                "visible": t.visible,
                "height": t.height,
                "clips": [],
            }
            for c in t.clips:
                cd = {
                    "clip_id": c.clip_id,
                    "name": c.name,
                    "file_path": c.file_path,
                    "start_frame": c.start_frame,
                    "duration": c.duration,
                    "in_point": c.in_point,
                    "out_point": c.out_point,
                    "clip_type": c.clip_type,
                    "volume": c.volume,
                    "opacity": c.opacity,
                    "text_content": c.text_content,
                    "text_style": c.text_style,
                    "effects": [{"effect_type": e.effect_type, "params": e.params} for e in c.effects],
                    "metadata": c.metadata,
                }
                td["clips"].append(cd)
            data["tracks"].append(td)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ProjectModel":
        data = json.loads(path.read_text(encoding="utf-8"))
        proj = cls(
            project_id=data.get("project_id", ""),
            name=data.get("name", "Untitled"),
            width=data.get("width", 1920),
            height=data.get("height", 1080),
            fps=data.get("fps", 25.0),
            project_dir=data.get("project_dir", ""),
            topic=data.get("topic", ""),
        )
        for td in data.get("tracks", []):
            track = Track(
                track_id=td["track_id"],
                name=td["name"],
                track_type=td.get("track_type", "video"),
                muted=td.get("muted", False),
                locked=td.get("locked", False),
                visible=td.get("visible", True),
                height=td.get("height", 60),
            )
            for cd in td.get("clips", []):
                clip = Clip(
                    clip_id=cd["clip_id"],
                    name=cd["name"],
                    file_path=cd.get("file_path", ""),
                    track_id=track.track_id,
                    start_frame=cd.get("start_frame", 0),
                    duration=cd.get("duration", 5),
                    in_point=cd.get("in_point", 0),
                    out_point=cd.get("out_point", 0),
                    clip_type=cd.get("clip_type", "video"),
                    volume=cd.get("volume", 1.0),
                    opacity=cd.get("opacity", 1.0),
                    text_content=cd.get("text_content", ""),
                    text_style=cd.get("text_style", {}),
                    effects=[ClipEffect(**e) for e in cd.get("effects", [])],
                    metadata=cd.get("metadata", {}),
                )
                track.clips.append(clip)
            proj.tracks.append(track)
        return proj

    @classmethod
    @classmethod
    def from_yfriend_project(cls, project_dir: Path) -> "ProjectModel":
        """기존 yFriend 파이프라인 결과물을 ProjectModel로 변환"""
        proj = cls()
        proj.project_dir = str(project_dir)
        proj.name = project_dir.name

        # 블루프린트 읽기
        bp_file = None
        for sub in sorted(project_dir.iterdir()):
            if sub.is_dir() and "script" in sub.name.lower():
                for f in sorted(sub.glob("*.json")):
                    bp_file = f
                    break
            if bp_file:
                break

        scenes = []
        if bp_file and bp_file.exists():
            bp_data = json.loads(bp_file.read_text(encoding="utf-8"))
            scenes = bp_data.get("scenes", [])
            proj.topic = bp_data.get("topic", "")

        # ─── 폴더 자동 탐색 (번호 고정이 아닌 이름 기반) ───
        visual_dir = None
        voice_dir = None
        assembly_dir = None
        music_dir = None

        for sub in sorted(project_dir.iterdir()):
            if not sub.is_dir():
                continue
            name_lower = sub.name.lower()
            if "visual" in name_lower or "image" in name_lower:
                visual_dir = sub
            elif "voice" in name_lower or "narration" in name_lower or "tts" in name_lower:
                voice_dir = sub
            elif "assembly" in name_lower or "output" in name_lower:
                assembly_dir = sub
            elif "music" in name_lower or "bgm" in name_lower:
                music_dir = sub

        # fallback: 번호 기반
        if not visual_dir:
            for p in project_dir.glob("*visual*"):
                if p.is_dir(): visual_dir = p; break
        if not voice_dir:
            for p in project_dir.glob("*voice*"):
                if p.is_dir(): voice_dir = p; break

        print(f"[PROJECT] visual={visual_dir}, voice={voice_dir}, assembly={assembly_dir}, music={music_dir}")

        # 트랙 생성
        video_track = Track(name="Video 1", track_type="video")
        text_track = Track(name="Subtitles", track_type="text")
        audio_track = Track(name="Narration", track_type="audio")
        bgm_track = Track(name="BGM", track_type="bgm")

        current_time = 0.0
        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i + 1)
            sid = f"{scene_num:02d}"
            dur_est = scene.get("duration_estimate_sec", 10.0)

            # ─── 이미지 클립 ───
            keyframe = None
            if visual_dir:
                for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                    candidate = visual_dir / f"scene_{sid}_keyframe{ext}"
                    if candidate.exists():
                        keyframe = candidate
                        break

            # ─── 나레이션 → 실제 길이 측정 ───
            narration = None
            if voice_dir:
                for ext in [".mp3", ".wav", ".ogg"]:
                    candidate = voice_dir / f"scene_{sid}_narration{ext}"
                    if candidate.exists():
                        narration = candidate
                        break

            actual_dur = dur_est
            if narration and narration.exists():
                import subprocess
                try:
                    r = subprocess.run(
                        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                         "-of", "csv=p=0", str(narration)],
                        capture_output=True, text=True, timeout=10
                    )
                    actual_dur = float(r.stdout.strip())
                except Exception:
                    pass

            # 비디오 클립
            if keyframe and keyframe.exists():
                video_track.add_clip(Clip(
                    name=f"Scene {sid}",
                    file_path=str(keyframe),
                    start_frame=current_time,
                    duration=actual_dur,
                    clip_type="image",
                    metadata={"scene_number": scene_num,
                              "visual_prompt": scene.get("visual_prompt_en", "")},
                ))

            # 나레이션 클립
            if narration and narration.exists():
                audio_track.add_clip(Clip(
                    name=f"Narration {sid}",
                    file_path=str(narration),
                    start_frame=current_time,
                    duration=actual_dur,
                    clip_type="audio",
                    volume=1.0,
                ))

            # 자막 클립
            narration_ko = scene.get("narration_ko", "")
            if narration_ko:
                text_track.add_clip(Clip(
                    name=f"Sub {sid}",
                    start_frame=current_time,
                    duration=actual_dur,
                    clip_type="text",
                    text_content=narration_ko,
                    text_style={"font": "Malgun Gothic", "size": 42, "color": "#FFFFFF"},
                ))

            current_time += actual_dur

        # ─── BGM ───
        if music_dir and music_dir.exists():
            for bgm_file in music_dir.glob("*.mp3"):
                bgm_track.add_clip(Clip(
                    name=bgm_file.stem,
                    file_path=str(bgm_file),
                    start_frame=0,
                    duration=current_time,
                    clip_type="bgm",
                    volume=0.12,
                ))
                break

        proj.add_track(video_track)
        proj.add_track(text_track)
        proj.add_track(audio_track)
        if bgm_track.clips:
            proj.add_track(bgm_track)

        return proj

