"""
core/project.py - Immutable project structure
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


PHASE_DIRS = [
    "01_script",
    "02_visual",
    "03_motion",
    "04_voice",
    "05_music",
    "06_assembly",
    "07_post",
]


def create_project(base_dir: str | Path, topic: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in topic[:30])
    project_dir = Path(base_dir) / f"{ts}_{safe_topic}"
    project_dir.mkdir(parents=True, exist_ok=True)

    for d in PHASE_DIRS:
        (project_dir / d).mkdir(exist_ok=True)
        (project_dir / d / "_override").mkdir(exist_ok=True)

    db_path = project_dir / "state.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS phase_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase TEXT NOT NULL,
            engine TEXT,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS part_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_type TEXT NOT NULL,
            scene_id TEXT,
            file_path TEXT,
            origin TEXT DEFAULT 'auto',
            engine TEXT,
            qa_status TEXT,
            qa_issues TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pain_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pain_id TEXT,
            description TEXT,
            frequency INTEGER DEFAULT 1,
            resolution TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.close()

    return project_dir


def log_phase(project_dir: Path, phase: str, engine: str,
              started: str, finished: str, status: str, error: str = ""):
    db = project_dir / "state.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO phase_log (phase, engine, started_at, finished_at, status, error) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (phase, engine, started, finished, status, error),
    )
    conn.commit()
    conn.close()


def log_part(project_dir: Path, part, qa_result):
    db = project_dir / "state.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO part_log (part_type, scene_id, file_path, origin, engine, qa_status, qa_issues) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            part.part_type.value,
            part.scene_id,
            str(part.file_path),
            part.origin.value,
            part.engine_used,
            qa_result.status.value,
            "; ".join(qa_result.issues),
        ),
    )
    conn.commit()
    conn.close()