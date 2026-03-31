"""
engines/advisor/self_improve.py - Self-Improvement Advisor
프로젝트 결과를 분석하고 다음 개선점을 스스로 제안하는 엔진.

사용법: python -m engines.advisor.self_improve projects/[프로젝트폴더]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def analyze_project(project_dir: Path) -> dict:
    """프로젝트 결과물을 분석하여 현황 리포트를 생성."""
    report = {
        "project": str(project_dir),
        "phases": {},
        "files": {},
        "quality": {},
        "issues": [],
        "scores": {},
    }

    # 1. Blueprint 분석
    bp_path = project_dir / "01_script" / "blueprint.json"
    if bp_path.exists():
        with open(bp_path, "r", encoding="utf-8") as f:
            bp = json.load(f)
        report["phases"]["script"] = "OK"
        report["files"]["blueprint"] = {
            "scenes": bp.get("total_scenes", 0),
            "estimated_duration": bp.get("estimated_total_duration_sec", 0),
        }

        # 나레이션 품질 체크
        for scene in bp.get("scenes", []):
            narr = scene.get("narration_ko", "")
            if len(narr) < 20:
                report["issues"].append({
                    "phase": "script",
                    "scene": scene["scene_id"],
                    "issue": "narration too short (" + str(len(narr)) + " chars)",
                    "severity": "warning",
                })
            if len(narr) > 200:
                report["issues"].append({
                    "phase": "script",
                    "scene": scene["scene_id"],
                    "issue": "narration too long (" + str(len(narr)) + " chars) - may cause subtitle overflow",
                    "severity": "warning",
                })
    else:
        report["phases"]["script"] = "MISSING"
        report["issues"].append({
            "phase": "script",
            "scene": "all",
            "issue": "blueprint.json not found",
            "severity": "critical",
        })

    # 2. Voice 분석
    voice_dir = project_dir / "04_voice"
    if voice_dir.exists():
        mp3_files = sorted(voice_dir.glob("*.mp3"))
        report["phases"]["voice"] = "OK" if mp3_files else "MISSING"
        report["files"]["narrations"] = len(mp3_files)

        total_duration_ms = 0
        for mp3 in mp3_files:
            dur = get_duration_ms(mp3)
            total_duration_ms += dur
            if dur < 3000:
                report["issues"].append({
                    "phase": "voice",
                    "scene": mp3.stem,
                    "issue": "audio too short (" + str(dur) + "ms)",
                    "severity": "warning",
                })

        report["quality"]["total_audio_duration_sec"] = round(total_duration_ms / 1000, 1)
    else:
        report["phases"]["voice"] = "MISSING"

    # 3. Visual 분석 (Sprint 2에서는 없음)
    visual_dir = project_dir / "02_visual"
    if visual_dir.exists():
        images = list(visual_dir.glob("*.png")) + list(visual_dir.glob("*.jpg"))
        report["phases"]["visual"] = "OK" if images else "NOT_IMPLEMENTED"
        report["files"]["images"] = len(images)
    else:
        report["phases"]["visual"] = "NOT_IMPLEMENTED"

    # 4. Motion 분석 (Sprint 2에서는 없음)
    motion_dir = project_dir / "03_motion"
    if motion_dir.exists():
        clips = list(motion_dir.glob("*.mp4"))
        report["phases"]["motion"] = "OK" if clips else "NOT_IMPLEMENTED"
        report["files"]["motion_clips"] = len(clips)
    else:
        report["phases"]["motion"] = "NOT_IMPLEMENTED"

    # 5. Music 분석 (Sprint 2에서는 없음)
    music_dir = project_dir / "05_music"
    if music_dir.exists():
        bgm = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
        report["phases"]["music"] = "OK" if bgm else "NOT_IMPLEMENTED"
        report["files"]["bgm"] = len(bgm)
    else:
        report["phases"]["music"] = "NOT_IMPLEMENTED"

    # 6. Final video 분석
    final = project_dir / "06_assembly" / "final_prototype.mp4"
    if final.exists():
        report["phases"]["assembly"] = "OK"
        dur = get_duration_ms(final)
        size_mb = final.stat().st_size / (1024 * 1024)
        report["quality"]["final_duration_sec"] = round(dur / 1000, 1)
        report["quality"]["final_size_mb"] = round(size_mb, 1)

        # 해상도 확인
        res = get_resolution(final)
        report["quality"]["resolution"] = res
    else:
        report["phases"]["assembly"] = "FAIL"
        report["issues"].append({
            "phase": "assembly",
            "scene": "final",
            "issue": "final MP4 not generated",
            "severity": "critical",
        })

    # 7. 점수 계산
    scores = {}
    scores["script"] = 80 if report["phases"].get("script") == "OK" else 0
    scores["voice"] = 80 if report["phases"].get("voice") == "OK" else 0
    scores["visual"] = 70 if report["phases"].get("visual") == "OK" else 0
    scores["motion"] = 0  # not yet implemented
    scores["music"] = 0   # not yet implemented
    scores["assembly"] = 70 if report["phases"].get("assembly") == "OK" else 0

    # 감점
    for issue in report["issues"]:
        phase = issue["phase"]
        if issue["severity"] == "critical":
            scores[phase] = max(0, scores.get(phase, 0) - 30)
        elif issue["severity"] == "warning":
            scores[phase] = max(0, scores.get(phase, 0) - 5)

    scores["overall"] = round(sum(scores.values()) / 6, 1)
    report["scores"] = scores

    return report


def generate_improvement_plan(report: dict) -> list[dict]:
    """분석 결과를 기반으로 개선 계획을 자동 생성."""
    plan = []
    scores = report.get("scores", {})

    # Priority 1: 미구현 기능 (가장 큰 품질 향상)
    if scores.get("visual", 0) == 0:
        plan.append({
            "priority": 1,
            "phase": "visual",
            "title": "Phase 2: AI Keyframe Generation",
            "description": "Add AI image generation for each scene using FLUX or Stable Diffusion",
            "impact": "Black screen -> actual visuals (+40 quality points)",
            "effort": "Medium (new engine file)",
            "next_action": "Create engines/visual/flux_engine.py that generates one image per scene",
            "estimated_score_gain": 40,
        })

    if scores.get("motion", 0) == 0:
        plan.append({
            "priority": 2,
            "phase": "motion",
            "title": "Phase 3: Ken Burns / Zoom Animation",
            "description": "Add pan/zoom animation to keyframe images using FFmpeg",
            "impact": "Static images -> subtle motion (+30 quality points)",
            "effort": "Low (FFmpeg filter chain)",
            "next_action": "Create engines/motion/kenburns_engine.py",
            "estimated_score_gain": 30,
        })

    if scores.get("music", 0) == 0:
        plan.append({
            "priority": 3,
            "phase": "music",
            "title": "Phase 5: Background Music",
            "description": "Add royalty-free BGM from Pixabay or generate with AI",
            "impact": "Silent background -> atmospheric audio (+20 quality points)",
            "effort": "Low (API call or local file)",
            "next_action": "Create engines/music/pixabay_engine.py",
            "estimated_score_gain": 20,
        })

    # Priority 2: 기존 기능 품질 향상
    if scores.get("script", 0) < 90:
        plan.append({
            "priority": 4,
            "phase": "script",
            "title": "Script Quality: Hook + Pacing",
            "description": "Improve prompt to generate stronger hooks and better scene pacing",
            "impact": "Better viewer retention in first 10 seconds",
            "effort": "Low (prompt engineering)",
            "next_action": "Update SYSTEM_PROMPT in gemini_flash.py with hook/pacing rules",
            "estimated_score_gain": 10,
        })

    if scores.get("assembly", 0) < 90:
        plan.append({
            "priority": 5,
            "phase": "assembly",
            "title": "Assembly: Scene Transitions",
            "description": "Add crossfade transitions between scenes instead of hard cuts",
            "impact": "Smoother viewing experience",
            "effort": "Low (FFmpeg xfade filter)",
            "next_action": "Add transition options in ffmpeg_assembly.py",
            "estimated_score_gain": 10,
        })

    # Priority 3: 보조 기능
    plan.append({
        "priority": 6,
        "phase": "post",
        "title": "Auto Thumbnail Generation",
        "description": "Generate YouTube thumbnail from best keyframe + title text overlay",
        "impact": "Saves 10-15 min manual work per video",
        "effort": "Medium",
        "next_action": "Create engines/post/thumbnail_engine.py",
        "estimated_score_gain": 5,
    })

    plan.append({
        "priority": 7,
        "phase": "assembly",
        "title": "Subtitle Style Improvement",
        "description": "Word-by-word highlight sync, better font, shadow, positioning",
        "impact": "More professional subtitle appearance",
        "effort": "Low (ASS style tuning)",
        "next_action": "Update ASS style in ffmpeg_assembly.py",
        "estimated_score_gain": 5,
    })

    # Issues 기반 추가 개선
    for issue in report.get("issues", []):
        if issue["severity"] == "critical":
            plan.insert(0, {
                "priority": 0,
                "phase": issue["phase"],
                "title": "CRITICAL FIX: " + issue["issue"],
                "description": "Must fix before other improvements",
                "impact": "System stability",
                "effort": "Depends",
                "next_action": "Debug and fix " + issue["phase"] + " phase",
                "estimated_score_gain": 0,
            })

    return sorted(plan, key=lambda x: x["priority"])


def print_report(report: dict, plan: list[dict]):
    """분석 결과와 개선 계획을 출력."""
    print("")
    print("=" * 70)
    print("  yFriend Self-Improvement Report")
    print("  Project: " + report["project"])
    print("=" * 70)

    # Phase status
    print("")
    print("  [Phase Status]")
    for phase, status in report["phases"].items():
        if status == "OK":
            icon = "[OK]"
        elif status == "NOT_IMPLEMENTED":
            icon = "[--]"
        elif status == "MISSING":
            icon = "[!!]"
        else:
            icon = "[XX]"
        print("    " + icon + " " + phase)

    # Quality
    print("")
    print("  [Quality Metrics]")
    q = report.get("quality", {})
    for k, v in q.items():
        print("    " + k + ": " + str(v))

    # Scores
    print("")
    print("  [Scores]")
    scores = report.get("scores", {})
    bar_width = 30
    for phase in ["script", "voice", "visual", "motion", "music", "assembly"]:
        score = scores.get(phase, 0)
        filled = int(bar_width * score / 100)
        bar = "#" * filled + "-" * (bar_width - filled)
        print("    " + phase.ljust(12) + " [" + bar + "] " + str(score) + "/100")
    print("")
    overall = scores.get("overall", 0)
    print("    OVERALL: " + str(overall) + " / 100")

    # Issues
    if report["issues"]:
        print("")
        print("  [Issues Found]")
        for issue in report["issues"]:
            icon = "[!!]" if issue["severity"] == "critical" else "[?]"
            print("    " + icon + " " + issue["phase"] + "/" + issue["scene"] + ": " + issue["issue"])

    # Improvement Plan
    print("")
    print("=" * 70)
    print("  [Next Improvements - Ranked by Priority]")
    print("=" * 70)
    for i, item in enumerate(plan):
        print("")
        print("  #" + str(i + 1) + " " + item["title"])
        print("     Phase: " + item["phase"])
        print("     Impact: " + item["impact"])
        print("     Effort: " + item["effort"])
        print("     Score Gain: +" + str(item["estimated_score_gain"]))
        print("     Next: " + item["next_action"])

    # Recommendation
    if plan:
        top = plan[0]
        print("")
        print("=" * 70)
        print("  RECOMMENDATION: Start with #1 - " + top["title"])
        print("  Expected score: " + str(overall) + " -> " + str(overall + top["estimated_score_gain"]))
        print("=" * 70)
    print("")


def get_duration_ms(path: Path) -> int:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True, text=True,
        )
        data = json.loads(result.stdout)
        return int(float(data["format"]["duration"]) * 1000)
    except Exception:
        return 0


def get_resolution(path: Path) -> str:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "json", str(path)],
            capture_output=True, text=True,
        )
        data = json.loads(result.stdout)
        s = data["streams"][0]
        return str(s["width"]) + "x" + str(s["height"])
    except Exception:
        return "unknown"


def find_latest_project(base: Path) -> Path:
    projects_dir = base / "projects"
    if not projects_dir.exists():
        return None
    dirs = sorted([d for d in projects_dir.iterdir() if d.is_dir()], reverse=True)
    return dirs[0] if dirs else None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        project_dir = Path(sys.argv[1])
    else:
        project_dir = find_latest_project(Path("."))

    if project_dir is None or not project_dir.exists():
        print("No project found. Run main.py first.")
        sys.exit(1)

    report = analyze_project(project_dir)
    plan = generate_improvement_plan(report)
    print_report(report, plan)

    # Save report
    report_path = project_dir / "self_improvement_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"report": report, "plan": [p for p in plan]}, f, ensure_ascii=False, indent=2)
    print("Report saved: " + str(report_path))
