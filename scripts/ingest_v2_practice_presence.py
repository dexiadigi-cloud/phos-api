#!/usr/bin/env python3
"""Stage "The Practice of the Presence of God" (Brother Lawrence) into
data/staging/practice_presence.db.

Deterministic: stdlib + sqlite3 only. Reads the raw Gutenberg text
read-only; never touches data/scripture.db or data/study.db.

Source: Project Gutenberg eBook No. 13871
  data/raw_v2/practice_presence/pg13871.txt
  (sha256 asserted against provenance.json before parsing)

Output: data/staging/practice_presence.db with exact tables:
  devotionals (id, source_id, day, part, title, anchor_ref, body)
  sources     (source_id PK, kind, title, rights, rights_basis, version, sha256)

Content: 20 sections numbered day 1..20 (Preface, 4 Conversations,
15 Letters), part='morning' for each, anchor_ref='' (no scripture
anchors in these sections). Bodies are verbatim from the Gutenberg
text between the all-caps section headings; line endings normalized
CRLF -> LF, heading lines moved to the title field, division headings
(CONVERSATIONS., LETTERS.), license preamble and footer excluded.
"""

import hashlib
import json
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_DIR = os.path.join(ROOT, "data", "raw_v2", "practice_presence")
STAGING_DIR = os.path.join(ROOT, "data", "staging")
RAW_FILE = os.path.join(RAW_DIR, "pg13871.txt")
DB_PATH = os.path.join(STAGING_DIR, "practice_presence.db")

SOURCE_ID = "practice_presence"

ORDINAL = {
    "FIRST": "First", "SECOND": "Second", "THIRD": "Third", "FOURTH": "Fourth",
    "FIFTH": "Fifth", "SIXTH": "Sixth", "SEVENTH": "Seventh", "EIGHTH": "Eighth",
    "NINTH": "Ninth", "TENTH": "Tenth", "ELEVENTH": "Eleventh",
    "TWELFTH": "Twelfth", "THIRTEENTH": "Thirteenth",
    "FOURTEENTH": "Fourteenth", "FIFTEENTH": "Fifteenth",
}

EXPECTED_HEADINGS = (
    ["PREFACE."]
    + ["%s CONVERSATION." % o for o in
       ("FIRST", "SECOND", "THIRD", "FOURTH")]
    + ["%s LETTER." % o for o in ORDINAL]
)

EXPECTED_MARKS = (
    ["PREFACE.", "CONVERSATIONS."]
    + ["%s CONVERSATION." % o for o in
       ("FIRST", "SECOND", "THIRD", "FOURTH")]
    + ["LETTERS."]
    + ["%s LETTER." % o for o in ORDINAL]
)

MARK_RE = re.compile(
    r"^(PREFACE\.|CONVERSATIONS\.|LETTERS\.|"
    r"(?:FIRST|SECOND|THIRD|FOURTH) CONVERSATION\.|"
    r"(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|"
    r"TENTH|ELEVENTH|TWELFTH|THIRTEENTH|FOURTEENTH|FIFTEENTH) LETTER\.)$",
    re.M,
)

START_MARK = "*** START OF THE PROJECT GUTENBERG EBOOK"
END_MARK = "*** END OF THE PROJECT GUTENBERG EBOOK"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def heading_to_title(heading):
    if heading == "PREFACE.":
        return "Preface"
    core, kind = heading[:-1].rsplit(" ", 1)  # drop trailing '.'
    return "%s %s" % (ORDINAL[core], kind.capitalize())


def parse():
    prov = json.load(open(os.path.join(RAW_DIR, "provenance.json"),
                          encoding="utf-8"))
    digest = sha256_of(RAW_FILE)
    assert digest == prov["sha256"], (
        "SHA-256 mismatch: got %s, provenance says %s" % (digest, prov["sha256"]))
    print("  sha256 OK: %s" % digest)

    raw = open(RAW_FILE, "rb").read().decode("utf-8")
    text = raw.replace("\r\n", "\n")
    assert START_MARK in text, "missing START marker"
    assert END_MARK in text, "missing END marker"
    body_region = text.split(START_MARK, 1)[1].split(END_MARK, 1)[0]

    marks = MARK_RE.findall(body_region)
    assert marks == EXPECTED_MARKS, (
        "mark sequence mismatch:\n%r\nvs\n%r" % (marks, EXPECTED_MARKS))

    parts = MARK_RE.split(body_region)
    # split() with one capture group: [pre, mark1, chunk1, mark2, chunk2, ...]
    # The pre-PREFACE chunk is the Gutenberg title page (title, author,
    # translator, publisher); asserted as title page, then excluded.
    title_page = parts[0]
    for needle in ("THE PRACTICE OF THE PRESENCE", "BROTHER LAWRENCE.",
                   "FLEMING H. REVELL COMPANY", "Translated from the French"):
        assert needle in title_page, "title page missing %r" % needle
    assert "PREFACE." not in title_page, "PREFACE. in title page chunk"
    pairs = list(zip(parts[1::2], parts[2::2]))
    assert [m for m, _ in pairs] == EXPECTED_MARKS

    rows = []
    day = 0
    for mark, chunk in pairs:
        if mark in ("CONVERSATIONS.", "LETTERS."):
            assert chunk.strip() == "", (
                "unexpected text after division heading %s" % mark)
            continue
        day += 1
        body = chunk.strip()
        assert body, "empty body for %s" % mark
        rows.append({
            "source_id": SOURCE_ID,
            "day": day,
            "part": "morning",
            "title": heading_to_title(mark),
            "anchor_ref": "",
            "body": body,
        })
    assert day == 20, day
    assert [r["title"] for r in rows] == [heading_to_title(h)
                                         for h in EXPECTED_HEADINGS]
    return rows, digest


def leak_check(rows):
    problems = []
    html_re = re.compile(r"<[a-zA-Z/!][^>]*>")
    ent_re = re.compile(r"&(#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);")
    usfm_re = re.compile(
        r"\\(id|h|toc|c|v|s|p|q|m|d|f|fr|ft|fk|x|w|zaln-s|k-s)\b")
    for r in rows:
        where = "%s day=%d %s" % (r["source_id"], r["day"], r["part"])
        for field in ("title", "body"):
            t = r[field] or ""
            if html_re.search(t):
                problems.append((where, field, "HTML tag"))
            if ent_re.search(t):
                problems.append((where, field, "HTML entity"))
            if usfm_re.search(t):
                problems.append((where, field, "USFM marker"))
    assert not problems, "leak check failures: %r" % problems[:5]
    print("leak checks: 0 HTML tags, 0 HTML entities, 0 USFM markers")


SOURCES_ROW = (
    "practice_presence",
    "devotional",
    "Brother Lawrence, The Practice of the Presence of God",
    "Public Domain",
    ("Project Gutenberg eBook No. 13871 ('The Practice of the Presence of "
     "God the Best Rule of a Holy Life'); Gutenberg catalog marks it "
     "'Public domain in the USA.'; author Brother Lawrence (Nicolas "
     "Herman) died 1691, French work first published circa 1691/1694; "
     "retrieved 2026-09-20."),
    "Gutenberg eBook 13871, plain text, release 2004-10-26, updated 2024-10-28",
    None,  # sha256 filled in from provenance.json
)


def write_db(rows, digest):
    os.makedirs(STAGING_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""CREATE TABLE devotionals (
      id INTEGER PRIMARY KEY,
      source_id TEXT NOT NULL,
      day INTEGER NOT NULL,
      part TEXT NOT NULL,
      title TEXT,
      anchor_ref TEXT NOT NULL,
      body TEXT NOT NULL
    );""")
    cur.execute("CREATE UNIQUE INDEX ux_devotionals "
                "ON devotionals(source_id, day, part);")
    cur.execute("""CREATE TABLE sources (
      source_id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,
      title TEXT NOT NULL,
      rights TEXT NOT NULL,
      rights_basis TEXT NOT NULL,
      version TEXT,
      sha256 TEXT
    );""")
    cur.executemany(
        "INSERT INTO devotionals (source_id, day, part, title, anchor_ref, body)"
        " VALUES (:source_id, :day, :part, :title, :anchor_ref, :body)", rows)
    cur.execute(
        "INSERT INTO sources (source_id, kind, title, rights, rights_basis,"
        " version, sha256) VALUES (?,?,?,?,?,?,?)",
        SOURCES_ROW[:6] + (digest,))
    con.commit()

    n = cur.execute("SELECT COUNT(*) FROM devotionals").fetchone()[0]
    assert n == 20, n
    days = [r[0] for r in cur.execute(
        "SELECT day FROM devotionals ORDER BY day").fetchall()]
    assert days == list(range(1, 21)), days
    assert cur.execute(
        "SELECT COUNT(*) FROM devotionals WHERE anchor_ref IS NULL"
        ).fetchone()[0] == 0
    ns = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert ns == 1, ns
    idx = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    assert any(r[0] == "ux_devotionals" for r in idx), idx
    assert cur.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    con.close()
    print("wrote %s: 20 rows, 1 source row, unique index OK, integrity_check ok"
          % DB_PATH)


def main():
    rows, digest = parse()
    print("parsed 20 sections (Preface + 4 Conversations + 15 Letters)")
    leak_check(rows)
    write_db(rows, digest)


if __name__ == "__main__":
    main()
