"""
core/config.py - Immutable config loader
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class EngineConfig:
    name: str
    module: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class YFriendConfig:
    projects_dir: str
    output_resolution: str
    output_fps: int
    api_keys: dict
    engines: dict[str, EngineConfig]


def load_config(path: str | Path = "config.yaml") -> YFriendConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    engines = {}
    for phase_name, eng_data in raw.get("engines", {}).items():
        engines[phase_name] = EngineConfig(
            name=eng_data["name"],
            module=eng_data["module"],
            params=eng_data.get("params", {}),
        )

    return YFriendConfig(
        projects_dir=raw.get("projects_dir", "projects"),
        output_resolution=raw.get("output_resolution", "1920x1080"),
        output_fps=raw.get("output_fps", 24),
        api_keys=raw.get("api_keys", {}),
        engines=engines,
    )