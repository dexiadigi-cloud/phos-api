#!/usr/bin/env python3
"""Parse My Utmost for His Highest (original 1927 text, utmost.org "classic"
post type) into staging rows for the devotionals table.

Deterministic: stdlib + sqlite3 only. Reads raw sources read-only; never
touches data/scripture.db (read via api/db.py + api/parser.py for validation
only) and never creates study.db.

Sources:
  data/raw_v2/my_utmost/utmost_classic_raw.json  (WP REST dump, 367 posts)
  data/raw_v2/my_utmost/anchor_verses.json       (anchor verse blocks scraped
                                                 from the rendered pages)

Output: data/staging/my_utmost.db with the exact required schema:
  devotionals(source_id, day, part, title, anchor_ref, body)
  sources(source_id, kind, title, rights, rights_basis, version, sha256)
"""

import hashlib
import html as html_module
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "api"))
import db as phos_db
import parser as phos_parser

RAW = os.path.join(ROOT, "data", "raw_v2", "my_utmost")
STAGING = os.path.join(ROOT, "data", "staging")
DB_PATH = os.path.join(STAGING, "my_utmost.db")

# Leap-year day-of-year (Feb has 29 days; Feb 29 = day 60, Dec 31 = 366).
MONTH_LEN = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def day_of_year(month, day):
    assert 1 <= month <= 12 and 1 <= day <= MONTH_LEN[month - 1], (month, day)
    return sum(MONTH_LEN[: month - 1]) + day


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


TAG_RE = re.compile(r"<[a-zA-Z/!][^>]*>")
ENTITY_RE = re.compile(r"&(#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);")
USFM_RE = re.compile(r"\\(id|h|toc|c|v|s|p|q|m|d|f|fr|ft|fk|x|w|zaln-s|k-s)\b")


def strip_html(s):
    """Tags -> '', entities unescaped, whitespace normalized."""
    s = TAG_RE.sub("", s)
    s = html_module.unescape(s)
    s = s.replace("\u00a0", " ")
    return s


def html_to_paragraphs(content_html):
    """Split rendered WP content into clean paragraphs."""
    # Split on block boundaries first so list items etc. stay separate.
    chunks = re.split(r"</(?:p|h[1-6]|li|blockquote|div)>", content_html)
    paras = []
    for ch in chunks:
        text = strip_html(ch)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = text.strip(" \n")
        # Collapse internal single newlines; keep paragraph separation.
        text = re.sub(r"\n+", " ", text).strip()
        if text:
            paras.append(text)
    # Drop pure separator lines (e.g. lone em-dashes used as dividers).
    paras = [p for p in paras if not re.fullmatch(r"[\s\u2014\u2013\-*]+", p)]
    return paras


def validate_anchor(anchor_ref, bounds, where):
    """Validate an anchor ref string via api/parser.py; return normalized form.

    Handles the one site quirk found in the corpus: a comma verse list
    ("2 Peter 1:5, 7") is expanded to "2 Peter 1:5; 2 Peter 1:7".
    """
    anchor_ref = re.sub(
        r"^(.+?)\s+(\d+):(\d+),\s*(\d+)$",
        lambda m: "%s %s:%s; %s %s:%s" % (
            m.group(1), m.group(2), m.group(3),
            m.group(1), m.group(2), m.group(4)),
        anchor_ref.strip())
    # Single-chapter books cited as "Jude 20" mean verse 20 of chapter 1.
    one_ch = {b for b, info in bounds.items() if info["chapters"] == 1}
    pieces = []
    for piece in (x.strip() for x in anchor_ref.split(";")):
        m = re.match(r"^(.+?)\s+(\d+)$", piece)
        if m and ":" not in piece and m.group(1) in one_ch:
            piece = "%s 1:%s" % (m.group(1), m.group(2))
        piece = piece.rstrip(".")  # site quirk: "Romans 14:7."
        pieces.append(piece)
    anchor_ref = "; ".join(pieces)
    for piece in anchor_ref.split(";"):
        piece = piece.strip()
        assert piece, "empty ref piece in %r at %s" % (anchor_ref, where)
        try:
            phos_parser.parse_reference(piece, bounds)
        except Exception as exc:
            raise AssertionError(
                "anchor ref failed to parse at %s: %r (%s)" % (where, piece, exc))
    return "; ".join(p.strip() for p in anchor_ref.split(";"))


def build_rows(bounds):
    posts = json.load(
        open(os.path.join(RAW, "utmost_classic_raw.json"), encoding="utf-8"))
    anchors = json.load(
        open(os.path.join(RAW, "anchor_verses.json"), encoding="utf-8"))

    rows = []
    seen_days = set()
    for p in posts:
        slug = p["slug"]
        if slug == "today":
            continue  # empty-content redirect placeholder, not a reading
        date = p["date"][:10]
        month, daynum = int(date[5:7]), int(date[8:10])
        day = day_of_year(month, daynum)
        assert day not in seen_days, "duplicate day: %s (%s)" % (date, slug)
        seen_days.add(day)

        title = strip_html(p["title"]["rendered"])
        title = re.sub(r"\s+", " ", title).strip()
        assert title, "empty title at %s" % slug

        a = anchors.get(slug)
        assert a is not None, "no anchor block for %s" % slug
        assert a["ref"], "empty anchor ref for %s" % slug
        assert a["verse"], "empty anchor verse text for %s" % slug
        where = "my_utmost %s %s" % (date, slug)
        anchor_ref = validate_anchor(a["ref"], bounds, where)

        verse_para = '"%s" \u2014 %s%s%s' % (
            a["verse"], anchor_ref,
            " (%s)" % a["version"] if a["version"] else "",
            " %s" % a["trail"] if a.get("trail") else "")
        paras = html_to_paragraphs(p["content"]["rendered"])
        assert paras, "empty body at %s" % where
        body = verse_para + "\n\n" + "\n\n".join(paras)

        rows.append({
            "source_id": "my_utmost",
            "day": day,
            "part": "morning",
            "title": title,
            "anchor_ref": anchor_ref,
            "body": body,
        })
    rows.sort(key=lambda r: r["day"])
    assert len(rows) == 366, len(rows)
    assert [r["day"] for r in rows] == list(range(1, 367))
    assert any(r["day"] == 60 for r in rows)  # Feb 29 present
    print("my_utmost: 366 rows, days 1..366, all anchors validated")
    return rows


def leak_check(rows):
    problems = []
    for r in rows:
        where = "%s day=%d %s" % (r["source_id"], r["day"], r["part"])
        for field in ("title", "body"):
            text = r[field] or ""
            if TAG_RE.search(text):
                problems.append((where, field, "HTML tag"))
            if ENTITY_RE.search(text):
                problems.append((where, field, "HTML entity"))
            if USFM_RE.search(text):
                problems.append((where, field, "USFM marker"))
    assert not problems, "leak check failures: %r" % problems[:5]
    print("leak checks: 0 HTML tags, 0 HTML entities, 0 USFM markers")


DEVOTIONAL_SCHEMA = """CREATE TABLE devotionals (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  day INTEGER NOT NULL,
  part TEXT NOT NULL,
  title TEXT,
  anchor_ref TEXT NOT NULL,
  body TEXT NOT NULL
);"""
SOURCES_SCHEMA = """CREATE TABLE sources (
  source_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  rights TEXT NOT NULL,
  rights_basis TEXT NOT NULL,
  version TEXT,
  sha256 TEXT NOT NULL
);"""
INDEX = "CREATE UNIQUE INDEX ux_devotionals ON devotionals(source_id, day, part);"


def main():
    os.makedirs(STAGING, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    bounds = phos_db.get_bounds("KJV")

    rows = build_rows(bounds)
    leak_check(rows)

    raw_sha = sha256_of(os.path.join(RAW, "utmost_classic_raw.json"))
    source_row = {
        "source_id": "my_utmost",
        "kind": "devotional",
        "title": "Oswald Chambers, My Utmost for His Highest",
        "rights": "Public Domain",
        "rights_basis": (
            "Original 1927 text (Simpkin & Marshall, England; 1935 Dodd, "
            "Mead, US); author d. 1917; US public domain since 2023-01-01. "
            "Transcribed from utmost.org official-publisher 'classic' post "
            "type (WP REST API), retrieved 2026-09-20. Edition verified as "
            "the original (not the 1992 Reimann updated edition): see "
            "data/raw_v2/my_utmost/PROVENANCE.md."),
        "version": "original-1927",
        "sha256": raw_sha,
    }

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(DEVOTIONAL_SCHEMA)
    cur.execute(SOURCES_SCHEMA)
    cur.execute(INDEX)
    cur.executemany(
        "INSERT INTO devotionals (source_id, day, part, title, anchor_ref, body)"
        " VALUES (:source_id, :day, :part, :title, :anchor_ref, :body)", rows)
    cur.execute(
        "INSERT INTO sources (source_id, kind, title, rights, rights_basis,"
        " version, sha256) VALUES (:source_id, :kind, :title, :rights,"
        " :rights_basis, :version, :sha256)", source_row)
    con.commit()

    n = cur.execute("SELECT COUNT(*) FROM devotionals").fetchone()[0]
    assert n == 366, n
    days = [r[0] for r in cur.execute(
        "SELECT day FROM devotionals ORDER BY day").fetchall()]
    assert days == list(range(1, 367)), "day gaps"
    s = cur.execute("SELECT * FROM sources").fetchall()
    assert len(s) == 1 and s[0][0] == "my_utmost", s
    integ = cur.execute("PRAGMA integrity_check").fetchone()[0]
    assert integ == "ok", integ
    con.close()
    print("wrote %s: 366 rows + sources row, unique index OK, integrity_check ok"
          % DB_PATH)


if __name__ == "__main__":
    main()
