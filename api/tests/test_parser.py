"""Parser unit tests: happy paths, aliases, and invalid references."""

import pytest

from parser import RefError, parse_reference


def k(bounds):
    """Key facts helper: (book, order, spans, display)."""
    def _p(ref):
        r = parse_reference(ref, bounds)
        return r.book, r.book_order, r.spans, r.display
    return _p


# --- happy paths ------------------------------------------------------------ #

def test_whole_chapter(bounds):
    book, order, spans, display = k(bounds)("John 14")
    assert (book, order, display) == ("John", 42, "John 14")
    assert spans == [(14, 1, 31)]


def test_single_verse(bounds):
    book, _, spans, display = k(bounds)("John 3:16")
    assert book == "John"
    assert spans == [(3, 16, 16)]
    assert display == "John 3:16"


def test_verse_range(bounds):
    _, _, spans, display = k(bounds)("Ps 23:1-3")
    assert spans == [(23, 1, 3)]
    assert display == "Psalms 23:1-3"


def test_romans_range(bounds):
    book, _, spans, display = k(bounds)("Romans 8:28-30")
    assert book == "Romans"
    assert spans == [(8, 28, 30)]
    assert display == "Romans 8:28-30"


def test_chapter_range(bounds):
    _, _, spans, display = k(bounds)("Genesis 1-2")
    assert spans == [(1, 1, 31), (2, 1, 25)]
    assert display == "Genesis 1-2"


def test_multi_chapter_verse_range(bounds):
    _, _, spans, display = k(bounds)("John 3:16-4:2")
    assert spans == [(3, 16, 36), (4, 1, 2)]
    assert display == "John 3:16-4:2"


def test_comma_list(bounds):
    _, _, spans, display = k(bounds)("Ps 23:1,3,5")
    assert spans == [(23, 1, 1), (23, 3, 3), (23, 5, 5)]
    assert display == "Psalms 23:1,3,5"


# --- aliases ---------------------------------------------------------------- #

def test_ps_aliases(bounds):
    for alias in ("Ps 23", "Psalm 23", "Psalms 23", "PSA 23"):
        book, _, _, display = k(bounds)(alias)
        assert book == "Psalms", alias
        assert display == "Psalms 23", alias


def test_song_of_solomon_alias(bounds):
    book, _, spans, display = k(bounds)("Song of Solomon 2:1")
    assert book == "Song of Songs"
    assert spans == [(2, 1, 1)]
    assert display == "Song of Songs 2:1"


def test_numbered_book_variants(bounds):
    for alias in ("1 John 1:9", "1John 1:9", "1 Jn 1:9", "I John 1:9"):
        book, _, spans, _ = k(bounds)(alias)
        assert book == "1 John", alias
        assert spans == [(1, 9, 9)], alias


def test_common_abbreviations(bounds):
    cases = {
        "Gen 1:1": "Genesis",
        "Exod 20:1": "Exodus",
        "Deut 6:4": "Deuteronomy",
        "1 Sam 3:9": "1 Samuel",
        "2 Kgs 5:1": "2 Kings",
        "1 Chr 1:1": "1 Chronicles",
        "Neh 8:1": "Nehemiah",
        "Prov 3:5": "Proverbs",
        "Eccl 3:1": "Ecclesiastes",
        "Isa 53:5": "Isaiah",
        "Matt 5:3": "Matthew",
        "Mk 1:1": "Mark",
        "Lk 2:1": "Luke",
        "Jn 1:1": "John",
        "Ac 2:1": "Acts",
        "Rom 8:28": "Romans",
        "1 Cor 13:4": "1 Corinthians",
        "Eph 2:8": "Ephesians",
        "Php 4:13": "Philippians",
        "1 Tim 2:5": "1 Timothy",
        "Heb 11:1": "Hebrews",
        "Jas 1:2": "James",
        "1 Pet 3:15": "1 Peter",
        "Rev 22:1": "Revelation",
    }
    for ref, expected in cases.items():
        assert k(bounds)(ref)[0] == expected, ref


# --- invalid references ----------------------------------------------------- #

def test_unknown_book(bounds):
    with pytest.raises(RefError, match="Unknown book"):
        parse_reference("Foo 1:1", bounds)


def test_chapter_out_of_range(bounds):
    with pytest.raises(RefError, match="out of range"):
        parse_reference("John 99:1", bounds)
    with pytest.raises(RefError, match="out of range"):
        parse_reference("Obadiah 2", bounds)


def test_verse_out_of_range(bounds):
    with pytest.raises(RefError, match="out of range"):
        parse_reference("Ps 23:999", bounds)
    with pytest.raises(RefError, match="out of range"):
        parse_reference("John 3:0", bounds)


def test_reversed_range(bounds):
    with pytest.raises(RefError, match="after end"):
        parse_reference("Ps 23:3-1", bounds)
    with pytest.raises(RefError, match="after end"):
        parse_reference("Genesis 2-1", bounds)


def test_garbage_and_empty(bounds):
    with pytest.raises(RefError):
        parse_reference("", bounds)
    with pytest.raises(RefError):
        parse_reference("not a reference", bounds)
    with pytest.raises(RefError):
        parse_reference("John", bounds)
