"""Validate every topic and reading-plan ref against the real DB.

Resolves each ref through parser.py against the BSB bounds from the live
database, and confirms every single verse in each resolved span actually
exists in the DB. Exits 1 (failing the build) on the first invalid ref,
listing all failures.

Usage:
    cd ~/workspace/scripture-desk/api && .venv/bin/python data/validate_refs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
from parser import RefError, parse_reference  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent
TRANSLATION = "BSB"


def check_refs(label: str, refs: list[str], bounds: dict) -> list[str]:
    errors: list[str] = []
    for ref in refs:
        try:
            parsed = parse_reference(ref, bounds)
        except RefError as exc:
            errors.append(f"{label}: ref {ref!r} failed to parse: {exc}")
            continue
        if ":" in ref:
            # Verse-level ref (topics): every verse key must exist.
            for ch, vs, ve in parsed.spans:
                for v in range(vs, ve + 1):
                    if db.get_verse(TRANSLATION, parsed.book, ch, v) is None:
                        errors.append(
                            f"{label}: ref {ref!r} -> verse {parsed.book} {ch}:{v} "
                            f"not present in {TRANSLATION}"
                        )
        else:
            # Chapter-level ref (plans): the chapter must exist and hold at
            # least one verse. Individual verse keys may be absent for
            # textual-critical reasons (BSB omits e.g. Matthew 17:21, as do
            # WEB/ASV); fetch_spans returns the verses that do exist.
            for ch, vs, ve in parsed.spans:
                if db.get_verse(TRANSLATION, parsed.book, ch, 1) is None:
                    errors.append(
                        f"{label}: ref {ref!r} -> chapter {parsed.book} {ch} "
                        f"has no verses in {TRANSLATION}"
                    )
    return errors


def main() -> int:
    bounds = db.get_bounds(TRANSLATION)
    errors: list[str] = []
    n_refs = 0

    topics = json.loads((DATA_DIR / "topics.json").read_text())
    for topic in topics["topics"]:
        n_refs += len(topic["refs"])
        errors.extend(check_refs(f"topic '{topic['id']}'", topic["refs"], bounds))

    plans = json.loads((DATA_DIR / "plans.json").read_text())
    for plan in plans["plans"]:
        for day in plan["schedule"]:
            n_refs += len(day["refs"])
            errors.extend(
                check_refs(
                    f"plan '{plan['id']}' day {day['day']}", day["refs"], bounds
                )
            )

    if errors:
        print(f"VALIDATION FAILED: {len(errors)} bad ref(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {n_refs} refs validated against {TRANSLATION} DB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
