"""Batch-3 translation tests: Weymouth New Testament (WEYMOUTH).

Fragment: not collected by pytest until assembled into the suite.
Conventions mirror api/tests/test_translations_batch2.py.
"""

import db


EXPECTED_WEYMOUTH_COUNT = 7957

# Canonical NT books in 0-based book_order (Genesis=0 .. Revelation=65).
WEYMOUTH_NT_BOOKS = [
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
    "Revelation",
]

# Raw `NNN:NNN` line counts per book from the Gutenberg ebooks
# (8828-8854); Luke count includes the mislabeled-Luke-8:23 correction.
WEYMOUTH_BOOK_COUNTS = {
    "Matthew": 1071, "Mark": 678, "Luke": 1151, "John": 879,
    "Acts": 1007, "Romans": 433, "1 Corinthians": 437,
    "2 Corinthians": 257, "Galatians": 149, "Ephesians": 155,
    "Philippians": 104, "Colossians": 95, "1 Thessalonians": 89,
    "2 Thessalonians": 47, "1 Timothy": 113, "2 Timothy": 83,
    "Titus": 46, "Philemon": 25, "Hebrews": 303, "James": 108,
    "1 Peter": 105, "2 Peter": 61, "1 John": 105, "2 John": 13,
    "3 John": 14, "Jude": 25, "Revelation": 404,
}

# Distinctive, DB-verified substrings per verse.
WEYMOUTH_SPOT_CHECKS = {
    ("John", 3, "16"): "For so greatly did God love the world",
    ("John", 1, "1"): "In the beginning was the Word, and the Word was with God",
    # Exercises the source-typo correction: pg8830.txt labels this verse
    # "002:023"; the ingest remaps it to Luke 8:23 (see PROVENANCE.md).
    ("Luke", 8, "23"): "there came down a squall",
}


def test_weymouth_count():
    counts = db.translation_counts()
    assert counts["WEYMOUTH"] == EXPECTED_WEYMOUTH_COUNT, \
        counts.get("WEYMOUTH")


def test_weymouth_spot_checks():
    for (book, chapter, verse), marker in WEYMOUTH_SPOT_CHECKS.items():
        row = db.get_verse("WEYMOUTH", book, chapter, verse)
        assert row is not None, (book, chapter, verse)
        assert marker in row["text"], (book, chapter, verse, row["text"][:80])


def test_weymouth_books_exactly_27_nt():
    books = db.get_books("WEYMOUTH")
    names = [b["book"] for b in books]
    assert len(names) == 27, names
    assert names == WEYMOUTH_NT_BOOKS
    assert "Genesis" not in names  # NT only; no OT books present
    assert "Malachi" not in names
    orders = {b["book"]: b["book_order"] for b in books}
    assert [orders[n] for n in WEYMOUTH_NT_BOOKS] == list(range(39, 66))


def test_weymouth_per_book_counts_sane():
    rows = db._query(
        "SELECT book, COUNT(*) FROM verses WHERE translation = ?"
        " GROUP BY book",
        ("WEYMOUTH",),
    )
    counts = {r["book"]: r["COUNT(*)"] for r in rows}
    assert counts == WEYMOUTH_BOOK_COUNTS, \
        {b: (counts.get(b), WEYMOUTH_BOOK_COUNTS[b])
         for b in WEYMOUTH_BOOK_COUNTS
         if counts.get(b) != WEYMOUTH_BOOK_COUNTS[b]}


def test_weymouth_no_empty_chapters():
    rows = db._query(
        "SELECT book, chapter, COUNT(*) AS c FROM verses"
        " WHERE translation = ? GROUP BY book, chapter",
        ("WEYMOUTH",),
    )
    assert rows, "no WEYMOUTH chapters found"
    empty = [(r["book"], r["chapter"]) for r in rows if r["c"] == 0]
    assert not empty, empty
    bad_chapter = [(r["book"], r["chapter"]) for r in rows
                   if r["chapter"] < 1]
    assert not bad_chapter, bad_chapter
    # no chapter gaps: every chapter 1..max has rows
    per_book = {}
    for r in rows:
        per_book.setdefault(r["book"], []).append(r["chapter"])
    gaps = []
    for book, chapters in per_book.items():
        hi = max(chapters)
        missing = [c for c in range(1, hi + 1) if c not in chapters]
        if missing:
            gaps.append((book, missing))
    assert not gaps, gaps
