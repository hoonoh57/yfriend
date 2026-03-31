"""
core/interfaces.py - Immutable engine interfaces
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from core.models import Blueprint, Part, Scene


@runtime_checkable
class ScriptEngine(Protocol):
    async def generate_blueprint(self, topic: str, output_dir: Path, **kwargs) -> Blueprint:
        ...


@runtime_checkable
class VoiceEngine(Protocol):
    async def generate_narration(self, scene: Scene, output_path: Path, **kwargs) -> Part:
        ...


@runtime_checkable
class AssemblyEngine(Protocol):
    async def assemble(
        self,
        blueprint: Blueprint,
        parts: list[Part],
        output_path: Path,
        **kwargs,
    ) -> Part:
        ...