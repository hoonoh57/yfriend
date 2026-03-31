"""
core/orchestrator.py - Immutable orchestration controller
Sprint 2.5: SCRIPT -> VISUAL -> VOICE -> ASSEMBLY
"""
from __future__ import annotations
import asyncio
import importlib
import time
from pathlib import Path
from core.config import load_config
from core.project import create_project, log_phase
from core.models import PhaseType, Blueprint


# Sprint 2.5 phases (VISUAL 추가)
SPRINT_PHASES = [
    (PhaseType.SCRIPT, "script", "01_script"),
    (PhaseType.VISUAL, "visual", "02_visual"),
    (PhaseType.VOICE, "voice", "04_voice"),
    (PhaseType.ASSEMBLY, "assembly", "06_assembly"),
]


class Orchestrator:
    """Runs each phase in sequence, logs results"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)

    async def run(self, topic: str) -> str:
        return await self._run_async(topic)


    async def _run_async(self, topic: str) -> str:
        project_dir = create_project(self.config.projects_dir, topic)
        print(f"\n{'='*60}")
        print(f"  yFriend Prototype - Sprint 2.5")
        print(f"  Topic : {topic}")
        print(f"  Project: {project_dir}")
        print(f"{'='*60}\n")

        blueprint = None
        keyframe_parts = []

        for phase_type, config_key, sub_dir in SPRINT_PHASES:
            phase_dir = Path(project_dir) / sub_dir
            phase_dir.mkdir(parents=True, exist_ok=True)

            engine_config = self.config.engines.get(config_key)
            if engine_config is None:
                print(f"  >> {phase_type.value} ({config_key}) - 설정 없음, 건너뜀")
                continue

            phase_label = f"phase_{phase_type.value}_{config_key}"
            print(f"  >> {phase_label} ({engine_config.name})")
            t0 = time.time()

            try:
                # API키 전달 (script, visual 엔진용)
                api_key_val = self.config.api_keys.get("gemini", "")
                extra = {}
                if config_key in ("script", "visual"):
                    extra["api_key"] = api_key_val

                engine = self._load_engine(engine_config, **extra)

                if config_key == "script":
                    blueprint = await engine.generate_blueprint(topic, phase_dir)
                    print(f"    [OK] Blueprint: {blueprint.total_scenes} scenes, ~{blueprint.estimated_total_duration_sec}s")

                elif config_key == "visual":
                    if blueprint is None:
                        raise RuntimeError("Blueprint 없음. Script 단계를 먼저 실행하세요.")
                    keyframe_parts = await engine.generate_keyframes(blueprint, phase_dir)
                    print(f"    [OK] Keyframes: {len(keyframe_parts)}/{blueprint.total_scenes} 생성 완료")

                elif config_key == "voice":
                    if blueprint is None:
                        raise RuntimeError("Blueprint 없음. Script 단계를 먼저 실행하세요.")
                    for scene in blueprint.scenes:
                        part = await engine.generate_voice(scene, phase_dir)
                        print(f"    [OK] {scene.scene_id} -> {part.file_path.name} [PASS]")

                elif config_key == "assembly":
                    if blueprint is None:
                        raise RuntimeError("Blueprint 없음. Script 단계를 먼저 실행하세요.")
                    # 키프레임 이미지 경로 전달
                    keyframe_dir = Path(project_dir) / "02_visual"
                    voice_dir = Path(project_dir) / "04_voice"
                    result = await engine.assemble(
                        blueprint, voice_dir, phase_dir,
                        keyframe_dir=keyframe_dir,
                    )
                    print(f"    [OK] Final: {result.file_path.name}")

            except Exception as e:
                print(f"    [FAIL] Error: {e}")

            elapsed = time.time() - t0
            print(f"    Time: {elapsed:.1f}s\n")

        result_path = Path(project_dir) / "06_assembly" / "final_prototype.mp4"
        print(f"{'='*60}")
        print(f"  Done! Result: {project_dir}")
        print(f"{'='*60}\n")
        return str(result_path)

    def _load_engine(self, engine_config, **extra):
        """엔진 모듈을 동적 로드"""
        module = importlib.import_module(engine_config.module)
        params = {**engine_config.params, **extra}
        return module.Engine(**params)
