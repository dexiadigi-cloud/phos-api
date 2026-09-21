"""Read-only access to the Phos study database (``data/study.db``).

Holds public-domain study resources, separate from the scripture corpus::

    sources(source_id PK, kind, title, rights, rights_basis, version, sha256)
    commentaries(id, source_id, book, book_order, start_chapter, start_verse,
                 end_chapter, end_verse, text)  -- verse 0 = whole chapter
    crossrefs(book, book_order, chapter, verse,
              ref_book, ref_book_order, ref_chapter, ref_verse)
    devotionals(id, source_id, day 1..366, part, title, anchor_ref, body)
    liturgy_sources(id, edition, title, source_url, retrieved_utc, rights_basis)
    liturgy(id, source_id, office, section, label, seq, speaker, kind,
            text, sidenote)
    lexicon_sources(source_id PK, title, rights, rights_basis, attribution,
                    commit_hash, retrieved, sha256)
    lexicon(id, strongs_number, language, lemma, transliteration, definition,
            gloss, source_id, extra)  -- Strong's/BDB/STEPBible word studies

The database is opened in read-only URI mode and never written to.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(
    os.environ.get(
        "PHOS_STUDY_DB_PATH",
        Path(__file__).resolve().parent.parent / "data" / "study.db",
    )
)

COMMENTARY_SOURCES = (
    "matthew_henry",
    "jfb",
    "barnes_nt",
    "gill",
    "clarke",
    "calvin",
    "keil_delitzsch",
    "treasury_of_david",
)
DICTIONARY_SOURCES = (
    "easton",
    "isbe",
    "naves",
    "torrey",
)
DEVOTIONAL_SOURCES = ("spurgeon", "daily_light", "my_utmost",
                      "practice_presence", "imitation_christ")
PRAYER_EDITIONS = ("1662", "1928")
PRAYER_OFFICES = ("morning", "evening")
LEXICON_SOURCES = (
    "strongs",
    "bdb",
    "step_tbesh",
    "step_tbesg",
    "step_tflsj",
    "step_tflsjx",
)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _query(sql: str, params: tuple = ()) -> list[dict]:
    with _connect() as con:
        return [dict(row) for row in con.execute(sql, params)]


def get_sources() -> list[dict]:
    """Rights metadata for every ingested study source."""
    return _query(
        "SELECT source_id, kind, title, rights, rights_basis, version "
        "FROM sources ORDER BY kind, source_id"
    )


def commentaries_covering(
    book_order: int,
    chapter: int,
    verse: int,
    source_id: str | None = None,
) -> list[dict]:
    """Commentary entries whose range covers one verse key.

    ``start_verse = 0`` means the start of the chapter; ``end_verse = 0``
    means the end of the chapter. Whole-chapter comments (both 0) therefore
    cover every verse of the chapter.
    """
    params: list = [book_order]
    source_filter = ""
    if source_id is not None:
        source_filter = "AND source_id = ?"
        params.append(source_id)
    params += [chapter, chapter, verse, chapter, chapter, verse]
    return _query(
        f"""SELECT id, source_id, book, start_chapter, start_verse,
                   end_chapter, end_verse, text
            FROM commentaries
            WHERE book_order = ? {source_filter}
              AND (start_chapter < ? OR (start_chapter = ? AND start_verse <= ?))
              AND (end_chapter > ?
                   OR (end_chapter = ? AND (end_verse = 0 OR end_verse >= ?)))
            ORDER BY start_chapter, start_verse, id""",
        tuple(params),
    )


def crossrefs_for(
    book_order: int, chapter: int, verse: int
) -> list[dict]:
    """TSK cross-references for one verse key, in canonical order."""
    return _query(
        """SELECT ref_book, ref_chapter, ref_verse
           FROM crossrefs
           WHERE book_order = ? AND chapter = ? AND verse = ?
           ORDER BY ref_book_order, ref_chapter, ref_verse""",
        (book_order, chapter, verse),
    )


def devotional(source_id: str, day: int) -> dict[str, dict | None]:
    """Morning and evening devotional entries for one leap-year day number."""
    rows = _query(
        """SELECT part, title, anchor_ref, body FROM devotionals
           WHERE source_id = ? AND day = ?""",
        (source_id, day),
    )
    out: dict[str, dict | None] = {"morning": None, "evening": None}
    for r in rows:
        out[r["part"]] = {
            "title": r["title"],
            "anchor_ref": r["anchor_ref"],
            "body": r["body"],
        }
    return out


def prayer_office(edition: str, office: str) -> tuple[dict, list[dict]]:
    """One BCP office as ordered liturgy blocks plus its edition metadata.

    ``edition`` is the API-facing "1662"/"1928"; the DB keys editions
    as "bcp1662"/"bcp1928".
    """
    db_edition = f"bcp{edition}"
    meta = _query(
        "SELECT edition, title, rights_basis FROM liturgy_sources WHERE edition = ?",
        (db_edition,),
    )
    blocks = _query(
        """SELECT l.section, l.label, l.speaker, l.kind, l.text, l.sidenote
           FROM liturgy l
           JOIN liturgy_sources s ON s.id = l.source_id
           WHERE s.edition = ? AND l.office = ?
           ORDER BY l.seq""",
        (db_edition, f"{office}_prayer"),
    )
    return (meta[0] if meta else {}), blocks


def get_lexicon_sources() -> list[dict]:
    """Rights metadata plus entry counts for every lexicon source."""
    return _query(
        """SELECT s.source_id, s.title, s.rights, s.rights_basis, s.attribution,
                  COUNT(l.id) AS entries
           FROM lexicon_sources s
           LEFT JOIN lexicon l ON l.source_id = s.source_id
           GROUP BY s.source_id ORDER BY s.source_id"""
    )


def lookup_word(canonical: str, source_id: str | None = None) -> list[dict]:
    """Lexicon entries for one canonical Strong's number ('G3056').

    Number formats differ per source ('G3056' vs 'G0001'); the comparison
    normalizes both sides to letter + integer. Returns entries ordered by
    source, each joined with its source's rights metadata.
    """
    source_filter = ""
    params: list = [canonical]
    if source_id is not None:
        source_filter = "AND l.source_id = ?"
        params.append(source_id)
    return _query(
        f"""SELECT l.strongs_number, l.language, l.lemma, l.transliteration,
                   l.definition, l.gloss, l.source_id,
                   s.title AS source_title, s.rights AS source_rights,
                   s.attribution AS source_attribution
            FROM lexicon l
            JOIN lexicon_sources s ON s.source_id = l.source_id
            WHERE substr(l.strongs_number, 1, 1)
                      || CAST(substr(l.strongs_number, 2) AS INTEGER) = ?
              {source_filter}
            ORDER BY l.source_id, l.id""",
        tuple(params),
    )


def get_dictionary_sources() -> list[dict]:
    """Rights metadata plus entry counts for every dictionary source."""
    return _query(
        """SELECT s.source_id, s.title, s.rights, s.rights_basis, s.attribution,
                  COUNT(d.id) AS entries
           FROM dictionary_sources s
           LEFT JOIN dictionaries d ON d.source_id = s.source_id
           GROUP BY s.source_id ORDER BY s.source_id"""
    )


def lookup_dictionary(term: str, source_id: str | None = None) -> list[dict]:
    """Dictionary entries for one term (case-insensitive).

    Returns entries ordered by source, each joined with its source's rights
    metadata.
    """
    source_filter = ""
    params: list = [term.strip().lower()]
    if source_id is not None:
        source_filter = "AND d.source_id = ?"
        params.append(source_id)
    return _query(
        f"""SELECT d.term, d.text, d.source_id,
                   s.title AS source_title, s.rights AS source_rights,
                   s.attribution AS source_attribution
            FROM dictionaries d
            JOIN dictionary_sources s ON s.source_id = d.source_id
            WHERE lower(d.term) = ?
              {source_filter}
            ORDER BY d.source_id, d.id""",
        tuple(params),
    )


def all_devotionals() -> list[dict]:
    """Every devotional row, for verse-anchor matching."""
    return _query(
        "SELECT id, source_id, part, title, anchor_ref, body "
        "FROM devotionals ORDER BY id"
    )


INTERLINEAR_SOURCES = ("step_tagnt", "step_tahot")


def get_interlinear(book: str, chapter: int, verse: int) -> dict:
    """Word-by-word interlinear for one KJV verse.

    Returns the selected reading (main) as an ordered word list, plus any
    variant readings grouped by manuscript tradition. Verses absent from the
    critical text (e.g. Mark 16:9-20) have no main reading; their variant
    words are returned with reading='variant'.
    """
    main = _query(
        """SELECT position, word, transliteration, gloss, strongs,
                  morphology, lemma, testament, src_ref
           FROM interlinear_words
           WHERE book = ? AND chapter = ? AND verse = ? AND is_variant = 0
           ORDER BY position""",
        (book, chapter, verse),
    )
    var_rows = _query(
        """SELECT position, word, transliteration, gloss, strongs,
                  morphology, lemma, testament, variant_kind, src_ref
           FROM interlinear_words
           WHERE book = ? AND chapter = ? AND verse = ? AND is_variant = 1
           ORDER BY variant_kind, position""",
        (book, chapter, verse),
    )
    variants: dict[str, list[dict]] = {}
    for r in var_rows:
        variants.setdefault(r["variant_kind"], []).append(r)
    testament = None
    if main:
        testament = main[0]["testament"]
    elif var_rows:
        testament = var_rows[0]["testament"]
    sources = _query(
        """SELECT source_id, title, rights, rights_basis
           FROM sources WHERE source_id IN ('step_tagnt', 'step_tahot')
           ORDER BY source_id"""
    )
    return {
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "testament": testament,
        "reading": "main" if main else ("variant" if var_rows else "none"),
        "words": main,
        "variants": [
            {"kind": kind, "words": rows} for kind, rows in variants.items()
        ],
        "sources": sources,
    }
