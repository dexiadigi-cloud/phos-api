"""Read-only SQLite access for the Phos scripture corpus.

The database at ``data/scripture.db`` is opened in read-only URI mode and
never written to. Schema (M1)::

    verses(translation TEXT, book TEXT, book_order INT, chapter INT,
           verse TEXT, text TEXT)
    verses_fts  -- FTS5(porter unicode61) over verses.text

Every function opens its own short-lived connection, so concurrent
FastAPI workers/threads never share a cursor.
"""

from __future__ import annotations

import os
import sqlite3
from functools import lru_cache
from pathlib import Path

DB_PATH = Path(
    os.environ.get(
        "PHOS_DB_PATH",
        Path(__file__).resolve().parent.parent / "data" / "scripture.db",
    )
)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _query(sql: str, params: tuple = ()) -> list[dict]:
    with _connect() as con:
        return [dict(row) for row in con.execute(sql, params)]


def translation_counts() -> dict[str, int]:
    """Verse row counts per translation code."""
    rows = _query("SELECT translation, COUNT(*) AS n FROM verses GROUP BY translation")
    return {r["translation"]: r["n"] for r in rows}


def total_verse_count() -> int:
    return _query("SELECT COUNT(*) AS n FROM verses")[0]["n"]


def get_books(translation: str) -> list[dict]:
    """Canonical book list for a translation: order, name, chapter count."""
    rows = _query(
        """SELECT book_order, book, MAX(chapter) AS chapters
           FROM verses WHERE translation = ?
           GROUP BY book_order, book ORDER BY book_order""",
        (translation,),
    )
    return [
        {"book_order": r["book_order"], "book": r["book"], "chapters": r["chapters"]}
        for r in rows
    ]


@lru_cache(maxsize=8)
def get_bounds(translation: str) -> dict:
    """Per-book chapter/verse limits for parser validation.

    Returns ``{book: {"order": int, "chapters": int,
    "max_verse": {chapter: max_verse}}}``.
    """
    rows = _query(
        """SELECT book, book_order, chapter, MAX(CAST(verse AS INTEGER)) AS vmax
           FROM verses WHERE translation = ?
           GROUP BY book, book_order, chapter""",
        (translation,),
    )
    bounds: dict = {}
    for r in rows:
        info = bounds.setdefault(
            r["book"],
            {"order": r["book_order"], "chapters": 0, "max_verse": {}},
        )
        info["chapters"] = max(info["chapters"], r["chapter"])
        info["max_verse"][r["chapter"]] = r["vmax"]
    return bounds


def fetch_spans(
    translation: str, book: str, spans: list[tuple[int, int, int]]
) -> list[dict]:
    """Fetch verses for parsed spans ``[(chapter, first_verse, last_verse)]``.

    Verse keys are numeric strings in the DB; comparison is numeric so
    ``'10'`` sorts after ``'9'``. Returns rows ordered canonically.
    """
    out: list[dict] = []
    for ch, vs, ve in spans:
        rows = _query(
            """SELECT book, chapter, verse, text FROM verses
               WHERE translation = ? AND book = ? AND chapter = ?
                 AND CAST(verse AS INTEGER) BETWEEN ? AND ?
               ORDER BY CAST(verse AS INTEGER)""",
            (translation, book, ch, vs, ve),
        )
        out.extend(rows)
    return out


def get_verse(translation: str, book: str, chapter: int, verse: int) -> dict | None:
    rows = _query(
        """SELECT book, chapter, verse, text FROM verses
           WHERE translation = ? AND book = ? AND chapter = ?
             AND CAST(verse AS INTEGER) = ?""",
        (translation, book, chapter, verse),
    )
    return rows[0] if rows else None


def search_verses(translation: str, fts_query: str, limit: int) -> list[dict]:
    """Full-text search via the FTS5 index, best matches first.

    ``fts_query`` must already be sanitized (quoted terms joined by spaces).
    """
    return _query(
        """SELECT v.book, v.chapter, v.verse, v.text,
                  snippet(verses_fts, 0, '<em>', '</em>', '...', 12) AS snippet
           FROM verses_fts
           JOIN verses v ON v.rowid = verses_fts.rowid
           WHERE verses_fts MATCH ? AND v.translation = ?
           ORDER BY rank
           LIMIT ?""",
        (fts_query, translation, limit),
    )


def verse_by_offset(translation: str, offset: int) -> dict:
    """The Nth verse of a translation in canonical order (0-based offset)."""
    rows = _query(
        """SELECT book, chapter, verse, text FROM verses
           WHERE translation = ?
           ORDER BY book_order, chapter, CAST(verse AS INTEGER)
           LIMIT 1 OFFSET ?""",
        (translation, offset),
    )
    return rows[0]
