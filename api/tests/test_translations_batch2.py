"""Batch-2 translation tests: counts, seeded verse spot-checks, DRB deuterocanon."""

import db
from parser import resolve_book


EXPECTED_COUNTS = {
    "YLT": 31102, "DARBY": 31099, "DRB": 35811, "BBE": 31102,
    "GENEVA": 31090, "AKJV": 31102, "OEB": 13894,
}

# Distinctive, DB-verified substrings of John 3:16 per translation.
JOHN_3_16_MARKERS = {
    "YLT": "for God did so love the world",
    "DARBY": "only-begotten Son",
    "DRB": "as to give his only begotten Son",
    "BBE": "such love for the world",
    "GENEVA": "loued the worlde",  # original 1599 spelling
    "AKJV": "whoever believes in him should not perish",
    "OEB": "may not be lost, but have eternal life",
}


def test_batch2_counts():
    counts = db.translation_counts()
    for code, expected in EXPECTED_COUNTS.items():
        assert counts[code] == expected, (code, counts.get(code))


def test_batch2_john_3_16_markers():
    for code, marker in JOHN_3_16_MARKERS.items():
        row = db.get_verse(code, "John", 3, "16")
        assert row is not None, code
        assert marker in row["text"], (code, row["text"][:80])


def test_drb_deuterocanon_books():
    books = [b["book"] for b in db.get_books("DRB")]
    assert len(books) == 73
    for name in ("Tobit", "Judith", "Wisdom", "Sirach", "Baruch",
                 "1 Maccabees", "2 Maccabees"):
        assert name in books
    orders = {b["book"]: b["book_order"] for b in db.get_books("DRB")}
    assert [orders[n] for n in ("Tobit", "Judith", "Wisdom", "Sirach",
                                "Baruch", "1 Maccabees", "2 Maccabees")] == \
        [66, 67, 68, 69, 70, 71, 72]


def test_drb_deuterocanon_verse():
    row = db.get_verse("DRB", "Tobit", 12, "7")
    assert row is not None and row["text"]


def test_parser_resolves_deuterocanon():
    assert resolve_book("Tobit") == "Tobit"
    assert resolve_book("1 Maccabees") == "1 Maccabees"
    assert resolve_book("2macc") == "2 Maccabees"
    assert resolve_book("Ecclesiasticus") == "Sirach"


def test_oeb_partial_books():
    books = [b["book"] for b in db.get_books("OEB")]
    assert len(books) == 44
    assert "Matthew" in books and "Psalms" in books
    assert "Leviticus" not in books  # OEB OT was never finished


def test_search_covers_new_translations(client, auth):
    r = client.get("/v1/search",
                   params={"q": "grace", "translation": "GENEVA"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["translation"] == "GENEVA"
    assert len(r.json()["hits"]) > 0


def test_passage_drb_tobit(client, auth):
    r = client.get("/v1/passage",
                   params={"ref": "Tobit 1:1-3", "translation": "DRB"},
                   headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["book"] == "Tobit"
    assert len(body["verses"]) == 3


def test_books_drb_count(client, auth):
    r = client.get("/v1/books", params={"translation": "DRB"}, headers=auth)
    assert r.status_code == 200
    assert len(r.json()) == 73
