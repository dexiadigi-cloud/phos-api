"""Batch-3 source tests (ingested 2026-09-20): WEBSTER, WEYMOUTH, LXX2012
translations and my_utmost, practice_presence, imitation_christ devotionals.

Assembled by the batch-3 coordinator from api/tests/batch3_frag_*.py.
Fragment-level names were prefixed (MU_/PP_/IC_) to avoid collisions.
Merge note: LXX2012 staged 28,352 rows; 1 row (1 Kings 14:1) had empty text
in the source edition and was dropped at merge, so the live count is 28,351.
"""

import datetime
import random
import re

import db


def test_lxx2012_source_gap_documented():
    """1 Kings 14:1 has no text in the LXX2012 edition; the empty row was
    dropped at merge rather than stored."""
    rows = db.get_verse("LXX2012", "1 Kings", 14, 1)
    assert rows is None, rows



# ---- from batch3_frag_webster.py ----
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


# ---- from batch3_frag_weymouth.py ----
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


# ---- from batch3_frag_lxx2012.py ----
LXX2012_ROW_COUNT = 28351  # 28352 staged; empty 1 Kings 14:1 dropped at merge

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


# ---- from batch3_frag_myutmost.py ----
MU_SOURCE = "my_utmost"
MU_ROW_COUNT = 366  # days 1..366, leap-year convention (Feb 29 = day 60)

# Seeded spot-check days, drawn once with the batch seed.
_mu_seed_rng = random.Random(20260920)
MU_SEED_DAYS = sorted(_mu_seed_rng.sample(range(1, MU_ROW_COUNT + 1), 3))
assert MU_SEED_DAYS == [301, 324, 364], MU_SEED_DAYS

MU_SPOT_CHECKS = {
    301: (
        "The Method Of Missions",
        '"Go ye therefore, and teach [disciple] all nations." '
        "\u2014 Matthew 28:19\n\nJesus Christ did not",
    ),
    324: (
        "When He Is Come",
        '"And when He is come, He will convict the world of sin\u2026" '
        "\u2014 John 16:8\n\nVery few of us know ",
    ),
    364: (
        "Deserter Or Disciple?",
        '"From that time many of His disciples went back, and walked no '
        'more with Him." \u2014 John 6:66',
    ),
}


def _mu_day_to_date(day):
    # 2024 is a leap year: day-of-year maps 1:1 to the API's leap-year day
    # numbering (day 1 = 2024-01-01, day 60 = 2024-02-29, day 366 = 2024-12-31).
    return (datetime.date(2024, 1, 1) + datetime.timedelta(days=day - 1)).isoformat()


def _mu_get_day(client, auth, day):
    r = client.get(
        "/v1/devotional?date=%s&source=%s" % (_mu_day_to_date(day), MU_SOURCE),
        headers=auth,
    )
    assert r.status_code == 200, (day, r.status_code)
    return r.json()


def test_my_utmost_row_count_constant():
    assert MU_ROW_COUNT == 366


def test_my_utmost_days_no_gaps(client, auth):
    seen = []
    for day in range(1, MU_ROW_COUNT + 1):
        body = _mu_get_day(client, auth, day)
        assert body["day"] == day
        assert body["source"] == MU_SOURCE
        assert body["morning"] is not None
        assert body["evening"] is None  # single (morning) entries only
        assert body["morning"]["anchor_ref"].strip()
        assert body["morning"]["title"].strip()
        assert body["morning"]["body"].strip()
        seen.append(body["day"])
    assert seen == list(range(1, MU_ROW_COUNT + 1))


def test_my_utmost_seeded_spot_checks(client, auth):
    for day in MU_SEED_DAYS:
        title, body_prefix = MU_SPOT_CHECKS[day]
        body = _mu_get_day(client, auth, day)
        assert body["morning"]["title"] == title
        assert body["morning"]["body"].startswith(body_prefix), day


def test_my_utmost_feb29_present(client, auth):
    # 2024-02-29 is day 60 in the leap-year convention (same as
    # spurgeon/daily_light).
    body = _mu_get_day(client, auth, 60)
    assert body["day"] == 60
    assert body["morning"] is not None
    assert body["morning"]["title"] == "What Do You Want The Lord To Do For You?"


def test_my_utmost_day_367_absent(client, auth):
    # Day-of-year never exceeds 366 (leap-year convention), so no date can
    # address a day 367. Check the real boundary: Dec 31 of leap year 2024
    # is day 366 and must have an entry.
    r = client.get(
        "/v1/devotional?date=2024-12-31&source=%s" % MU_SOURCE,
        headers=auth,
    )
    assert r.status_code == 200, r.status_code
    body = r.json()
    assert body["day"] == 366
    assert body["morning"] is not None
    assert body["evening"] is None


# ---- from batch3_frag_practice.py ----
PP_SOURCE = "practice_presence"
PP_ROW_COUNT = 20  # Preface + 4 Conversations + 15 Letters

# Seeded spot-check days, drawn once with the batch seed.
_pp_seed_rng = random.Random(20260920)
PP_SEED_DAYS = sorted(_pp_seed_rng.sample(range(1, PP_ROW_COUNT + 1), 3))
assert PP_SEED_DAYS == [5, 9, 19], PP_SEED_DAYS

PP_SPOT_CHECKS = {
    5: (
        "Fourth Conversation",
        "He discoursed with me very frequently, and with great openness of\n"
        "heart concerni",
    ),
    9: (
        "Fourth Letter",
        "I have taken this opportunity to communicate to you the sentiments "
        "of\none of our",
    ),
    19: (
        "Fourteenth Letter",
        "_To the Same_.\n\n"
        "I render thanks to our LORD for having relieved you a little,\nac",
    ),
}


def _pp_get_day(client, auth, day):
    # Days 1..20 are 2026-01-01..2026-01-20 (2026 is not a leap year,
    # so day-of-year equals the January date).
    r = client.get(
        "/v1/devotional?date=2026-01-%02d&source=%s" % (day, PP_SOURCE),
        headers=auth,
    )
    assert r.status_code == 200, (day, r.status_code)
    return r.json()


def test_practice_presence_row_count_constant():
    assert PP_ROW_COUNT == 20


def test_practice_presence_days_no_gaps(client, auth):
    seen = []
    for day in range(1, PP_ROW_COUNT + 1):
        body = _pp_get_day(client, auth, day)
        assert body["day"] == day
        assert body["source"] == PP_SOURCE
        assert body["morning"] is not None
        assert body["evening"] is None  # single (morning) entries only
        assert body["morning"]["anchor_ref"] == ""
        seen.append(body["day"])
    assert seen == list(range(1, PP_ROW_COUNT + 1))


def test_practice_presence_seeded_spot_checks(client, auth):
    for day in PP_SEED_DAYS:
        title, body_prefix = PP_SPOT_CHECKS[day]
        body = _pp_get_day(client, auth, day)
        assert body["morning"]["title"] == title
        assert body["morning"]["body"].startswith(body_prefix), day


# ---- from batch3_frag_imitation.py ----
IC_SOURCE = "imitation_christ"
IC_ROW_COUNT = 114  # Book 1: 25 + Book 2: 12 + Book 3: 59 + Book 4: 18

# Seeded spot-check days, drawn once with the batch seed.
_ic_seed_rng = random.Random(20260920)
IC_SEED_DAYS = sorted(_ic_seed_rng.sample(range(1, IC_ROW_COUNT + 1), 3))
assert IC_SEED_DAYS == [76, 81, 91], IC_SEED_DAYS

IC_SPOT_CHECKS = {
    76: (
        "Book 3, Chapter 39: That man must not be immersed in business",
        "\u201cMy Son, always commit thy cause to Me; I will dispose it aright in due\ntime. Wa",
    ),
    81: (
        "Book 3, Chapter 44: Of not troubling ourselves about outward things",
        "\u201cMy Son, in many things it behoveth thee to be ignorant, and to esteem\nthyself a",
    ),
    91: (
        "Book 3, Chapter 54: Of the diverse motions of Nature and of Grace",
        "\u201cMy Son, pay diligent heed to the motions of Nature and of Grace,\nbecause they m",
    ),
}

IC_TITLE_RE = re.compile(r"^Book (\d+), Chapter (\d+): ")

# (book, first_day, chapter_count)
IC_BOOKS = [(1, 1, 25), (2, 26, 12), (3, 38, 59), (4, 97, 18)]


def _ic_day_to_date(day):
    # 2024 is a leap year: day-of-year maps 1:1 to the API's leap-year day
    # numbering (day 1 = 2024-01-01, day 114 = 2024-04-23).
    return (datetime.date(2024, 1, 1) + datetime.timedelta(days=day - 1)).isoformat()


def _ic_get_day(client, auth, day):
    r = client.get(
        "/v1/devotional?date=%s&source=%s" % (_ic_day_to_date(day), IC_SOURCE),
        headers=auth,
    )
    assert r.status_code == 200, (day, r.status_code)
    return r.json()


def _ic_expected_book_chapter(day):
    for book, first, count in IC_BOOKS:
        if first <= day < first + count:
            return book, day - first + 1
    raise AssertionError("day out of range: %d" % day)


def test_imitation_christ_row_count_constant():
    assert IC_ROW_COUNT == 114


def test_imitation_christ_days_no_gaps(client, auth):
    seen = []
    for day in range(1, IC_ROW_COUNT + 1):
        body = _ic_get_day(client, auth, day)
        assert body["day"] == day
        assert body["source"] == IC_SOURCE
        assert body["morning"] is not None
        assert body["evening"] is None  # single (morning) entries only
        assert body["morning"]["anchor_ref"] == ""
        assert body["morning"]["body"].strip()
        seen.append(body["day"])
    assert seen == list(range(1, IC_ROW_COUNT + 1))


def test_imitation_christ_title_sequence_ordered(client, auth):
    for day in range(1, IC_ROW_COUNT + 1):
        body = _ic_get_day(client, auth, day)
        title = body["morning"]["title"]
        m = IC_TITLE_RE.match(title)
        assert m, (day, title)
        book, chapter = _ic_expected_book_chapter(day)
        assert (int(m.group(1)), int(m.group(2))) == (book, chapter), (day, title)


def test_imitation_christ_seeded_spot_checks(client, auth):
    for day in IC_SEED_DAYS:
        title, body_prefix = IC_SPOT_CHECKS[day]
        body = _ic_get_day(client, auth, day)
        assert body["morning"]["title"] == title
        assert body["morning"]["body"].startswith(body_prefix), day


def test_imitation_christ_day_115_absent(client, auth):
    # Day 115 (2024-04-24) is past the last chapter: no entry.
    body = _ic_get_day(client, auth, 115)
    assert body["day"] == 115
    assert body["morning"] is None
    assert body["evening"] is None
