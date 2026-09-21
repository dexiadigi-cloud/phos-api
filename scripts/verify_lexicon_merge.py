"""Seeded raw-to-merged verification for the lexicon merge.

- Strong's: raw IA djvu.txt heading lines vs merged definition
- BDB: data/raw_v2/bdb/HebrewStrong.xml entries vs merged rows
- STEPBible: raw Lexicons/*.txt TSV vs merged rows (incl. HTML-sanitize check)

Usage: python3 scripts/verify_lexicon_merge.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDY_DB = ROOT / "data" / "study.db"
STRONGS_DIR = ROOT / "data" / "raw_v2" / "strongs"
BDB_XML = ROOT / "data" / "raw_v2" / "bdb" / "HebrewStrong.xml"
LEXDIR = ROOT / "data" / "raw_v2" / "stepbible" / "step" / "Lexicons"

sys.path.insert(0, str(ROOT / "scripts"))
from merge_lexicons import sanitize_stepbible  # noqa: E402

STEP_FILES = {
    "step_tbesh": ("TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt", "Meaning"),
    "step_tbesg": ("TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt", None),
    "step_tflsj": ("TFLSJ  0-5624 - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt", "LSJ Meaning"),
    "step_tflsjx": ("TFLSJ extra - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt", "LSJ Meaning"),
}

passed = failed = 0
log_lines: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        log_lines.append(f"PASS {name} {detail}".rstrip())
    else:
        failed += 1
        log_lines.append(f"FAIL {name} {detail}".rstrip())


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def main() -> int:
    con = sqlite3.connect(f"file:{STUDY_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    merged = {}
    for r in con.execute("SELECT source_id, strongs_number, lemma, definition, gloss FROM lexicon"):
        merged.setdefault((r["source_id"], r["strongs_number"]), []).append(dict(r))

    # ---- 1. Strong's -------------------------------------------------------
    # Robust direction: merged definition snippet must occur in the raw OCR
    # text (the raw headings themselves are mangled, so regex-matching them
    # is unreliable). Known repair artifacts: G500's entry_text retains the
    # OCR's "600." while correctly assigned to G500 (antichristos); H430 was
    # manually recovered from heading "r430i".
    greek_txt = (STRONGS_DIR / "StrongGreekDictionary_djvu.txt").read_text(encoding="utf-8", errors="replace")
    heb_txt = (STRONGS_DIR / "StrongHebrewDictionary_djvu.txt").read_text(encoding="utf-8", errors="replace")
    strongs_seeds = [
        ("G1", greek_txt), ("G100", greek_txt), ("G500", greek_txt),
        ("G1000", greek_txt), ("G2000", greek_txt), ("G3056", greek_txt),
        ("G4000", greek_txt), ("G5000", greek_txt), ("G5624", greek_txt),
        ("H1", heb_txt), ("H430", heb_txt), ("H1000", heb_txt),
        ("H5000", heb_txt), ("H8674", heb_txt),
    ]
    for key, txt in strongs_seeds:
        rows = merged.get(("strongs", key))
        ok = False
        detail = ""
        if rows is not None and len(rows) == 1:
            definition = rows[0]["definition"] or ""
            # distinctive snippet: skip the number heading, take 40 chars
            body = re.sub(r"^[\d\-\.\s]+", "", definition)
            snip = norm_ws(body[:40])
            ok = len(snip) >= 20 and snip in norm_ws(txt)
            detail = f"snip={snip[:40]!r}"
        check(f"strongs/{key}", ok, detail)

    # ---- 2. BDB ------------------------------------------------------------
    ns = {"x": "http://openscriptures.github.com/morphhb/namespace"}
    tree = ET.parse(BDB_XML)
    entries = {}
    for e in tree.getroot().findall("x:entry", ns):
        eid = e.get("id")
        w = e.find("x:w", ns)
        entries[eid] = (w.text if w is not None else "", "".join(e.itertext()))
    for key in ["H1", "H100", "H430", "H1000", "H2000", "H3000",
                "H4000", "H5000", "H6000", "H7000", "H8000", "H8674"]:
        rows = merged.get(("bdb", key))
        lemma, full = entries.get(key, ("", ""))
        # lemma must match exactly; definition carries the parsed entry text
        ok = rows is not None and len(rows) == 1 and rows[0]["lemma"] == lemma
        check(f"bdb/{key}", ok, f"lemma={lemma[:20]!r}")

    # ---- 3. STEPBible ------------------------------------------------------
    for sid, (fname, meaning_col) in STEP_FILES.items():
        lines = (LEXDIR / fname).read_text(encoding="utf-8-sig").split("\n")
        hdr = next(i for i, l in enumerate(lines) if re.match(r"eStrong#?\tdStrong", l))
        cols = lines[hdr].split("\t")
        ek = "eStrong" if "eStrong" in cols else "eStrong#"
        mcol = meaning_col or next(c for c in cols if "Abbott-Smith" in c)
        raw_rows = []
        for l in lines[hdr + 1:]:
            if not l.strip() or l.strip().startswith("="):
                continue
            parts = l.split("\t")
            if len(parts) < 8:
                continue
            d = dict(zip(cols, parts))
            if re.match(r"^[GH]\d", d[ek].strip()):
                raw_rows.append((d[ek].strip(), d.get(mcol, "").strip()))
        # pick 3 spread seeds
        idxs = [0, len(raw_rows) // 2, len(raw_rows) - 1]
        for i in idxs:
            num, raw_def = raw_rows[i]
            rows = merged.get((sid, num))
            expect = sanitize_stepbible(raw_def)
            ok = (
                rows is not None and len(rows) >= 1
                and any(r["definition"] == expect for r in rows)
            )
            tag_left = any(re.search(r"</?(b|i|a|br|ref|level[1-4]|re|author)\b", r["definition"] or "", re.I) for r in (rows or []))
            check(f"{sid}/{num}", ok and not tag_left,
                  f"len(raw)={len(raw_def)} len(clean)={len(rows[0]['definition']) if rows else -1}")

    print(f"\nseeded: {passed} passed, {failed} failed (of {passed + failed})")
    for line in log_lines:
        print(" ", line)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
