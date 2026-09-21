"""Local reading-plan check-in store (api/data/progress.db).

This database holds user progress metadata (which plan days were checked
in), NOT scripture text. The scripture corpus (data/scripture.db) is never
written to. Records are keyed by (plan_id, start_date, day): v1 has a single
API key, so one reader's progress per plan+start_date is the whole model.

The path can be overridden with the PHOS_PROGRESS_PATH environment variable
(the test suite points it at a temp file).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PROGRESS_PATH = Path(
    os.environ.get(
        "PHOS_PROGRESS_PATH",
        Path(__file__).resolve().parent / "data" / "progress.db",
    )
)

_SCHEMA = """CREATE TABLE IF NOT EXISTS checkins (
    plan_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    day INTEGER NOT NULL,
    checked_in_at TEXT NOT NULL,
    PRIMARY KEY (plan_id, start_date, day)
)"""


def _connect() -> sqlite3.Connection:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(PROGRESS_PATH)
    con.execute(_SCHEMA)
    return con


def checkin(plan_id: str, start_date: str, day: int) -> str:
    """Record a completed plan day. Idempotent; returns the timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO checkins "
            "(plan_id, start_date, day, checked_in_at) VALUES (?, ?, ?, ?)",
            (plan_id, start_date, day, now),
        )
    return now


def completed_days(plan_id: str, start_date: str) -> list[int]:
    """Sorted list of checked-in day numbers for a plan+start_date."""
    with _connect() as con:
        rows = con.execute(
            "SELECT day FROM checkins WHERE plan_id = ? AND start_date = ? "
            "ORDER BY day",
            (plan_id, start_date),
        ).fetchall()
    return [r[0] for r in rows]
