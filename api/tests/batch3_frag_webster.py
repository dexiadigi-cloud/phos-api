"""Batch-3 fragment: WEBSTER (Noah Webster 1833, eBible engwebster USFM).

NOT collected by pytest until assembled into the suite. Conventions follow
api/tests/conftest.py (db helpers) and test_translations_batch2.py.
Staged source: data/staging/webster.db; deterministic verification in
data/staging/webster-VERIFY.md (seed 20260920, 55/55 three-way checks).
"""

import db

WEBSTER_COUNT = 31102

# Seeded spot-checks (deterministic sample run, seed 20260920): DB-verified
# substrings of the staged text.
WEBSTER_SPOT_CHECKS = {
    ("Jeremiah", 10, "14"): "Every man is brutish in his knowledge",
    ("Ezekiel", 13, "15"): "daubed it with untempered mortar",
    ("Matthew", 5, "25"): "Agree with thy adversary quickly",
}

# Mandatory anchors.
WEBSTER_ANCHORS = {
    ("Genesis", 1, "1"): "In the beginning God created the heaven and the earth.",
    ("John", 3, "16"): "only-begotten Son",  # Webster's hyphenated form
    ("Revelation", 22, "21"): "The grace of our Lord Jesus Christ be with you all.",
}


def test_webster_count():
    counts = db.translation_counts()
    assert counts["WEBSTER"] == WEBSTER_COUNT, counts.get("WEBSTER")


def test_webster_seeded_spot_checks():
    for (book, chapter, verse), marker in WEBSTER_SPOT_CHECKS.items():
        row = db.get_verse("WEBSTER", book, chapter, verse)
        assert row is not None, (book, chapter, verse)
        assert marker in row["text"], (book, chapter, verse, row["text"][:80])


def test_webster_anchors():
    for (book, chapter, verse), marker in WEBSTER_ANCHORS.items():
        row = db.get_verse("WEBSTER", book, chapter, verse)
        assert row is not None, (book, chapter, verse)
        assert marker in row["text"], (book, chapter, verse, row["text"][:80])


def test_webster_all_66_books():
    books = [b["book"] for b in db.get_books("WEBSTER")]
    assert len(books) == 66
    for name in ("Genesis", "1 Chronicles", "Song of Songs",
                 "Revelation", "Psalms"):
        assert name in books
    orders = {b["book"]: b["book_order"] for b in db.get_books("WEBSTER")}
    assert orders["Genesis"] == 0
    assert orders["Revelation"] == 65
    assert orders["Song of Songs"] == 21
