"""
core/contracts.py - Immutable part contracts
"""
from core.models import PartType

CONTRACTS: dict[PartType, dict] = {
    PartType.SCRIPT: {
        "allowed_formats": [".json"],
        "max_size_mb": 1,
        "required_fields": ["topic", "scenes"],
    },
    PartType.KEYFRAME: {
        "allowed_formats": [".png", ".jpg", ".webp"],
        "max_size_mb": 10,
        "min_resolution": (1280, 720),
        "aspect_ratio": (16, 9),
    },
    PartType.MOTION_CLIP: {
        "allowed_formats": [".mp4", ".webm"],
        "max_size_mb": 500,
        "min_resolution": (1280, 720),
    },
    PartType.NARRATION: {
        "allowed_formats": [".mp3", ".wav", ".ogg"],
        "max_size_mb": 50,
        "min_sample_rate": 22050,
    },
    PartType.BGM: {
        "allowed_formats": [".mp3", ".wav", ".ogg"],
        "max_size_mb": 30,
    },
    PartType.SFX: {
        "allowed_formats": [".mp3", ".wav", ".ogg"],
        "max_size_mb": 10,
    },
    PartType.SUBTITLE: {
        "allowed_formats": [".srt", ".ass", ".vtt"],
        "max_size_mb": 1,
    },
}