#!/usr/bin/env python3
"""Stage V2 devotional data (Spurgeon + Daily Light) into staging/devotionals.db.

Deterministic: stdlib + sqlite3 only. Reads raw sources read-only; never
touches data/scripture.db (read via api/db.py + api/parser.py for validation
only) and never creates study.db.

Sources:
  spurgeon    - data/raw_v2/spurgeon/m_e.json            (russianryebread/morning-and-evening)
  daily_light - data/raw_v2/daily_light/readings.json    (gm5dna/daily-light)
                + data/raw_v2/daily_light/ref_reconciliation.json

Output: staging/devotionals.db with the exact required schema.
"""

import hashlib
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

RAW = os.path.join(ROOT, "data", "raw_v2")
STAGING = os.path.join(ROOT, "staging")
DB_PATH = os.path.join(STAGING, "devotionals.db")

# Leap-year day-of-year (Feb has 29 days; Feb 29 = day 60, Dec 31 = 366).
MONTH_LEN = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTHS = ["january", "february", "march", "april", "may", "june",
          "july", "august", "september", "october", "november", "december"]


def day_of_year(month, day):
    assert 1 <= month <= 12 and 1 <= day <= MONTH_LEN[month - 1], (month, day)
    return sum(MONTH_LEN[: month - 1]) + day


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw(source_id, filename, prov_key):
    prov_path = os.path.join(RAW, source_id, "provenance.json")
    prov = json.load(open(prov_path, encoding="utf-8"))
    path = os.path.join(RAW, source_id, filename)
    digest = sha256_of(path)
    assert digest == prov[prov_key], (
        "SHA-256 mismatch for %s: got %s, provenance says %s"
        % (path, digest, prov[prov_key]))
    print("  sha256 OK: %s" % digest)
    return json.load(open(path, encoding="utf-8"))


def validate_anchor(anchor_ref, bounds, where):
    """Every ';'-separated piece must parse against KJV bounds."""
    assert anchor_ref and anchor_ref.strip(), "empty anchor_ref at %s" % where
    for piece in anchor_ref.split(";"):
        piece = piece.strip()
        assert piece, "empty ref piece in %r at %s" % (anchor_ref, where)
        try:
            phos_parser.parse_reference(piece, bounds)
        except Exception as exc:
            raise AssertionError(
                "anchor ref failed to parse at %s: %r (%s)" % (where, piece, exc))


# ---------------------------------------------------------------- Spurgeon

# Windows-1252 bytes misdecoded as Latin-1 C1 controls -> true Unicode.
C1_FIX = {0x92: 0x2019, 0x93: 0x201C, 0x94: 0x201D, 0x96: 0x2013, 0x97: 0x2014}
C1_RE = re.compile("[\u0080-\u009f]")
UTF8_MOJIBAKE_RE = re.compile("\u00e2[\u0080-\u009f]+")


def normalize_spurgeon_text(s):
    # Layer 1: UTF-8 bytes of curly quotes misdecoded as Latin-1
    # (e.g. '\u00e2\u0080\u009c' -> '"').
    def _fix(m):
        raw = m.group(0).encode("latin-1")
        return raw.decode("utf-8")  # raises if not valid UTF-8: fail loudly
    s = UTF8_MOJIBAKE_RE.sub(_fix, s)
    # Layer 2: lone C1 controls are Windows-1252 punctuation.
    def _c1(m):
        cp = ord(m.group(0))
        assert cp in C1_FIX, "unexpected C1 char U+%04X" % cp
        return chr(C1_FIX[cp])
    s = C1_RE.sub(_c1, s)
    # Layer 3: the single non-breaking space is an indent artifact.
    s = s.replace("\u00a0", " ")
    assert not C1_RE.search(s), "C1 chars remain after normalization"
    return s


HEADING_RE = re.compile(r"^[A-Za-z]+ \d+\S*\s*\u2009?\s*.\s*(Morning|Evening) Reading\n")


def clean_spurgeon_body(body_raw, keyverse, date, time):
    body = normalize_spurgeon_text(body_raw)
    body = body.replace("\r\n", "\n")
    lines = body.split("\n")
    # Line 0: date/part heading; line 1: key-verse line (== keyverse field);
    # line 2: blank. All verified before stripping.
    assert HEADING_RE.match(body), "heading pattern mismatch at %s %s" % (date, time)
    assert lines[1].strip() == normalize_spurgeon_text(keyverse).strip(), (
        "keyverse line mismatch at %s %s" % (date, time))
    assert lines[2].strip() == "", "expected blank line at %s %s" % (date, time)
    # Skip any further blank lines, then take the prose.
    i = 3
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    prose = "\n".join(lines[i:])
    paras = [p.strip() for p in re.split(r"\n{2,}", prose)]
    paras = [p for p in paras if p]
    assert paras, "empty body at %s %s" % (date, time)
    return "\n\n".join(paras)


def split_keyverse(keyverse):
    text, ref = keyverse.rsplit("\u2014", 1)  # em-dash separator
    text = text.strip()
    # The transcription wraps every key-verse in one layer of straight quotes.
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        text = text[1:-1]
    return text, ref.strip()


def build_spurgeon(bounds):
    print("spurgeon: loading raw")
    data = load_raw("spurgeon", "m_e.json", "sha256")
    real = [e for e in data if e]
    assert len(data) == 744 and len(real) == 732, (len(data), len(real))
    rows = []
    seen = set()
    for e in real:
        part = {"am": "morning", "pm": "evening"}[e["time"]]
        key = (e["month"], e["day"], part)
        assert key not in seen, "duplicate date/part: %s" % (key,)
        seen.add(key)
        kv_text, kv_ref = split_keyverse(normalize_spurgeon_text(e["keyverse"]))
        where = "spurgeon %d-%d %s" % (e["month"], e["day"], part)
        validate_anchor(kv_ref, bounds, where)
        body = clean_spurgeon_body(e["body"], e["keyverse"], e["date"], e["time"])
        rows.append({
            "source_id": "spurgeon",
            "day": day_of_year(e["month"], e["day"]),
            "part": part,
            "title": kv_text,
            "anchor_ref": kv_ref,
            "body": body,
        })
    parts = {}
    for r in rows:
        parts[r["part"]] = parts.get(r["part"], 0) + 1
    assert parts == {"morning": 366, "evening": 366}, parts
    assert {r["day"] for r in rows if r["part"] == "morning"} == set(range(1, 367))
    assert {r["day"] for r in rows if r["part"] == "evening"} == set(range(1, 367))
    # Feb 29 present (day 60).
    assert any(r["day"] == 60 for r in rows)
    print("spurgeon: 732 rows (366 morning + 366 evening), all anchors validated")
    return rows


# ---------------------------------------------------------------- Daily Light

def build_daily_light(bounds):
    print("daily_light: loading raw")
    data = load_raw("daily_light", "readings.json", "sha256")
    assert len(data) == 732, len(data)
    recon_path = os.path.join(RAW, "daily_light", "ref_reconciliation.json")
    recon = json.load(open(recon_path, encoding="utf-8"))
    assert len(recon) == 5656, len(recon)

    rows = []
    ri = 0
    seen = set()
    for entry in data:
        month_name, day_s = entry["date"].split("-")
        month = MONTHS.index(month_name) + 1
        daynum = int(day_s)
        part = entry["period"]
        assert part in ("morning", "evening"), part
        key = (month, daynum, part)
        assert key not in seen, "duplicate date/part: %s" % (key,)
        seen.add(key)

        items = [("theme", entry["themeVerse"])] + [
            ("verse", v) for v in entry["verses"]]
        final_refs = []
        texts = []
        for kind, item in items:
            r = recon[ri]
            ri += 1
            # Positional alignment: the reconciliation file is in raw item order.
            assert (r["date"], r["period"], r["kind"], r["source_ref"]) == (
                entry["date"], entry["period"], kind, item["reference"]), (
                "reconciliation misaligned at index %d" % (ri - 1))
            assert r["final_ref"] and r["final_ref"].strip(), (
                "empty final_ref at %s %s %s" % (entry["date"], part, kind))
            where = "daily_light %s %s %s" % (entry["date"], part, kind)
            validate_anchor(r["final_ref"], bounds, where)
            final_refs.append(r["final_ref"])
            texts.append(item["text"])
        rows.append({
            "source_id": "daily_light",
            "day": day_of_year(month, daynum),
            "part": part,
            "title": entry["themeVerse"]["text"],
            "anchor_ref": "; ".join(final_refs),
            "body": "\n\n".join(texts),
        })
    assert ri == len(recon) == 5656
    parts = {}
    for r in rows:
        parts[r["part"]] = parts.get(r["part"], 0) + 1
    assert parts == {"morning": 366, "evening": 366}, parts
    assert {r["day"] for r in rows if r["part"] == "morning"} == set(range(1, 367))
    assert {r["day"] for r in rows if r["part"] == "evening"} == set(range(1, 367))
    assert any(r["day"] == 60 for r in rows)
    print("daily_light: 732 rows (366 morning + 366 evening), all anchors validated")
    return rows


# ---------------------------------------------------------------- DB

SCHEMA = """CREATE TABLE devotionals (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  day INTEGER NOT NULL,
  part TEXT NOT NULL,
  title TEXT,
  anchor_ref TEXT NOT NULL,
  body TEXT NOT NULL
);"""
INDEX = "CREATE UNIQUE INDEX ux_devotionals ON devotionals(source_id, day, part);"

HTML_TAG_RE = re.compile(r"<[a-zA-Z/!][^>]*>")
HTML_ENTITY_RE = re.compile(r"&(#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);")
USFM_RE = re.compile(r"\\(id|h|toc|c|v|s|p|q|m|d|f|fr|ft|fk|x|w|zaln-s|k-s)\b")


def leak_check(rows):
    problems = []
    for r in rows:
        where = "%s day=%d %s" % (r["source_id"], r["day"], r["part"])
        for field in ("title", "body"):
            text = r[field] or ""
            if HTML_TAG_RE.search(text):
                problems.append((where, field, "HTML tag"))
            if HTML_ENTITY_RE.search(text):
                problems.append((where, field, "HTML entity"))
            if USFM_RE.search(text):
                problems.append((where, field, "USFM marker"))
    assert not problems, "leak check failures: %r" % problems[:5]
    print("leak checks: 0 HTML tags, 0 HTML entities, 0 USFM markers")


def main():
    os.makedirs(STAGING, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    bounds = phos_db.get_bounds("KJV")

    spurgeon_rows = build_spurgeon(bounds)
    dl_rows = build_daily_light(bounds)
    rows = spurgeon_rows + dl_rows
    assert len(rows) == 1464, len(rows)

    leak_check(rows)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(SCHEMA)
    cur.execute(INDEX)
    cur.executemany(
        "INSERT INTO devotionals (source_id, day, part, title, anchor_ref, body)"
        " VALUES (:source_id, :day, :part, :title, :anchor_ref, :body)", rows)
    con.commit()

    n = cur.execute("SELECT COUNT(*) FROM devotionals").fetchone()[0]
    assert n == 1464, n
    for sid in ("spurgeon", "daily_light"):
        c = cur.execute(
            "SELECT COUNT(*) FROM devotionals WHERE source_id=?", (sid,)).fetchone()[0]
        assert c == 732, (sid, c)
    # Unique index present and enforced.
    idx = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index'").fetchall()
    assert any(r[0] == "ux_devotionals" for r in idx), idx
    integ = cur.execute("PRAGMA integrity_check").fetchone()[0]
    assert integ == "ok", integ
    con.close()
    print("wrote %s: 1464 rows, unique index OK, integrity_check ok" % DB_PATH)


if __name__ == "__main__":
    main()
