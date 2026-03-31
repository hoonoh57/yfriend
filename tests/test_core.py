"""
tests/test_core.py - Core module tests
Run: python tests/test_core.py
"""
import sys
from pathlib import Path

# add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_models():
    from core.models import PartType, PhaseType, QAStatus, Scene, Blueprint
    print("[TEST] models import ... OK")

    s = Scene(
        scene_id="scene_01", scene_number=1, title="Test",
        narration_ko="테스트 나레이션입니다.",
        visual_prompt_en="A beautiful sunset",
        duration_estimate_sec=10.0,
    )
    assert s.scene_id == "scene_01"
    print("[TEST] Scene creation ... OK")

    bp = Blueprint(topic="test", total_scenes=1, scenes=[s],
                   estimated_total_duration_sec=10.0)
    assert bp.total_scenes == 1
    print("[TEST] Blueprint creation ... OK")


def test_contracts():
    from core.contracts import CONTRACTS
    from core.models import PartType
    assert PartType.NARRATION in CONTRACTS
    assert ".mp3" in CONTRACTS[PartType.NARRATION]["allowed_formats"]
    print("[TEST] contracts ... OK")


def test_config():
    from core.config import load_config
    config = load_config()
    assert config.output_fps == 24
    assert "script" in config.engines
    print(f"[TEST] config loaded: {len(config.engines)} engines ... OK")


def test_project():
    import shutil
    from core.project import create_project
    p = create_project("_test_projects", "unit_test")
    assert (p / "01_script").exists()
    assert (p / "04_voice" / "_override").exists()
    assert (p / "state.db").exists()
    print(f"[TEST] project created: {p} ... OK")
    shutil.rmtree("_test_projects", ignore_errors=True)


def test_qa():
    from core.qa import inspect
    from core.models import Part, PartType, QAStatus
    p = Part(part_type=PartType.NARRATION, scene_id="scene_01",
             file_path=Path("nonexistent.mp3"))
    result = inspect(p)
    assert result.status == QAStatus.FAIL
    print("[TEST] QA inspect (missing file) ... OK")


if __name__ == "__main__":
    print("=" * 50)
    print("  yFriend Core Tests")
    print("=" * 50)
    test_models()
    test_contracts()
    test_config()
    test_project()
    test_qa()
    print("\n All tests passed!")