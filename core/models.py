"""
core/models.py - Immutable data models
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class PartType(str, Enum):
    BLUEPRINT = "blueprint"
    NARRATION = "narration"
    KEYFRAME = "keyframe"
    MOTION_CLIP = "motion_clip"
    BGM = "bgm"
    FINAL_VIDEO = "final_video"


class PhaseType(str, Enum):
    SCRIPT = "1_script"
    VISUAL = "2_visual"
    VOICE = "4_voice"
    ASSEMBLY = "6_assembly"


class QAStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class Origin(str, Enum):
    AUTO = "auto"
    USER_OVERRIDE = "user_override"


@dataclass
class Scene:
    scene_id: str
    scene_number: int
    title: str
    narration_ko: str
    visual_prompt_en: str
    duration_estimate_sec: float
    keywords: list[str] = field(default_factory=list)


@dataclass
class Blueprint:
    topic: str
    total_scenes: int
    scenes: list[Scene]
    estimated_total_duration_sec: float
    style_guide: str = ""


@dataclass
class Part:
    part_type: PartType
    scene_id: str
    file_path: Path
    origin: Origin = Origin.AUTO
    engine_used: str = ""
    prompt_used: str = ""
    duration_ms: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class QAResult:
    part: Part
    status: QAStatus
    issues: list[str] = field(default_factory=list)


@dataclass
class PhaseResult:
    phase: PhaseType
    success: bool
    parts: list[Part] = field(default_factory=list)
    qa_results: list[QAResult] = field(default_factory=list)
    error: Optional[str] = None
    duration_sec: float = 0.0
