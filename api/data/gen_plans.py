"""Generate api/data/plans.json programmatically from the DB's chapter lists.

Reading plans are derived from the actual canonical chapter structure in
scripture.db (BSB translation; M1 verified chapter counts identical across
all four translations), so every generated ref is valid by construction.
The script self-checks: each emitted ref is parsed through parser.py
against the real DB bounds, and any failure aborts the write.

Usage:
    cd ~/workspace/scripture-desk/api && .venv/bin/python data/gen_plans.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
from parser import RefError, parse_reference  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent
OUT_PATH = DATA_DIR / "plans.json"

PLAN_DEFS = [
    (
        "bible-in-a-year",
        "Bible in a Year",
        365,
        None,  # whole canon
        "The whole Bible in one year: a few chapters a day, Genesis to Revelation.",
    ),
    (
        "new-testament-90",
        "New Testament in 90 Days",
        90,
        "new_testament",
        "The full New Testament in 90 days, about three chapters a day.",
    ),
    (
        "psalms-proverbs-31",
        "Psalms & Proverbs in 31 Days",
        31,
        ("Psalms", "Proverbs"),
        "Worship and wisdom for a month: the Psalms and Proverbs.",
    ),
    (
        "gospels-30",
        "The Gospels in 30 Days",
        30,
        ("Matthew", "Mark", "Luke", "John"),
        "The life, death, and resurrection of Jesus in 30 days.",
    ),
]


def _canon_books() -> list[str]:
    return [b["book"] for b in db.get_books("BSB")]


def _chapters_for(selector) -> list[tuple[str, int]]:
    books = db.get_books("BSB")
    canon = [b["book"] for b in books]
    if selector is None:
        wanted = canon
    elif selector == "new_testament":
        wanted = canon[canon.index("Matthew"):]
    else:
        wanted = list(selector)
    chapters: list[tuple[str, int]] = []
    for b in books:
        if b["book"] in wanted:
            chapters.extend((b["book"], ch) for ch in range(1, b["chapters"] + 1))
    return chapters


def _chunk(chapters: list[tuple[str, int]], n_days: int):
    """Split the chapter stream into n_days chunks, as even as possible."""
    base, rem = divmod(len(chapters), n_days)
    days, i = [], 0
    for d in range(n_days):
        size = base + (1 if d < rem else 0)
        days.append(chapters[i : i + size])
        i += size
    return days


def _refs_for(day_chapters: list[tuple[str, int]]) -> list[str]:
    """Group consecutive chapters of the same book into chapter refs."""
    refs: list[str] = []
    run_book: str | None = None
    run_start = run_end = 0

    def flush():
        if run_book is None:
            return
        if run_start == run_end:
            refs.append(f"{run_book} {run_start}")
        else:
            refs.append(f"{run_book} {run_start}-{run_end}")

    for book, ch in day_chapters:
        if book == run_book and ch == run_end + 1:
            run_end = ch
        else:
            flush()
            run_book, run_start, run_end = book, ch, ch
    flush()
    return refs


def main() -> None:
    bounds = db.get_bounds("BSB")
    plans = []
    for plan_id, name, n_days, selector, description in PLAN_DEFS:
        chapters = _chapters_for(selector)
        schedule = []
        for day_no, day_chapters in enumerate(_chunk(chapters, n_days), start=1):
            refs = _refs_for(day_chapters)
            # Self-check: every emitted ref must parse against real DB bounds.
            for ref in refs:
                try:
                    parse_reference(ref, bounds)
                except RefError as exc:
                    raise SystemExit(
                        f"GEN FAILED: plan {plan_id} day {day_no} ref {ref!r}: {exc}"
                    )
            schedule.append({"day": day_no, "refs": refs})
        plans.append(
            {
                "id": plan_id,
                "name": name,
                "description": description,
                "days": n_days,
                "total_chapters": len(chapters),
                "schedule": schedule,
            }
        )
    payload = {
        "generated": date.today().isoformat(),
        "source": (
            "Chapter lists read from scripture.db (BSB). M1 verified chapter "
            "counts identical across BSB/KJV/WEB/ASV, so schedules apply to "
            "all translations."
        ),
        "plans": plans,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    for p in plans:
        print(f"{p['id']}: {p['days']} days, {p['total_chapters']} chapters")


if __name__ == "__main__":
    main()
