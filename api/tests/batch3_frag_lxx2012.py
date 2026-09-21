"""Batch-3 fragment (LXX2012): row count, seeded spot-checks, deuterocanon,
no-NT check. Not collected until assembled into the API test suite."""

import db


LXX2012_ROW_COUNT = 28352

# Distinctive, staging-DB-verified substrings per verse.
LXX2012_SPOT_CHECKS = {
    ("Genesis", 1, "1"): "In the beginning God made the heaven and the earth",
    # LXX/Greek Psalm numbering: this is Hebrew Psalm 24.
    ("Psalms", 23, "1"): "The earth is the Lord's and the fullness thereof",
    ("Tobit", 12, "7"): "It is good to keep close the secret of a king",
    ("Wisdom", 3, "1"): "the souls of the righteous are in the hand of God",
}

# All 15 deuterocanonical/apocryphal books in LXX2012. The first 7 share
# DRB's names and book_order values; the last 8 continue the numbering.
LXX2012_DEUTEROCANON = [
    ("Tobit", 66), ("Judith", 67), ("Wisdom", 68), ("Sirach", 69),
    ("Baruch", 70), ("1 Maccabees", 71), ("2 Maccabees", 72),
    ("Epistle of Jeremy", 73), ("Prayer of Azarias", 74),
    ("Susanna", 75), ("Bel and the Dragon", 76), ("1 Esdras", 77),
    ("Prayer of Manasses", 78), ("3 Maccabees", 79), ("4 Maccabees", 80),
]

LXX2012_BOOK_COUNT = 54


def test_lxx2012_count():
    counts = db.translation_counts()
    assert counts["LXX2012"] == LXX2012_ROW_COUNT


def test_lxx2012_spot_checks():
    for (book, chapter, verse), marker in LXX2012_SPOT_CHECKS.items():
        row = db.get_verse("LXX2012", book, chapter, verse)
        assert row is not None, (book, chapter, verse)
        assert marker in row["text"], (book, chapter, verse, row["text"][:80])


def test_lxx2012_deuterocanon_present():
    books = [b["book"] for b in db.get_books("LXX2012")]
    assert len(books) == LXX2012_BOOK_COUNT
    orders = {b["book"]: b["book_order"] for b in db.get_books("LXX2012")}
    for name, order in LXX2012_DEUTEROCANON:
        assert name in books, name
        assert orders[name] == order, (name, orders[name])


def test_lxx2012_deuterocanon_verse():
    row = db.get_verse("LXX2012", "Sirach", 1, "27")
    assert row is not None and "fear of the Lord" in row["text"]


def test_lxx2012_no_nt_books():
    books = [b["book"] for b in db.get_books("LXX2012")]
    for nt in ("Matthew", "Mark", "Luke", "John", "Acts", "Romans",
               "Revelation"):
        assert nt not in books, nt


def test_lxx2012_greek_psalm_numbering():
    # LXX2012 keeps Greek versification: 151 psalms, so Psalm 151 exists
    # and Psalm 23 holds the Hebrew Psalm 24 text.
    row = db.get_verse("LXX2012", "Psalms", 151, "1")
    assert row is not None and row["text"]
