"""Parse STEPBible TAHOT/TAGNT tagged texts into a staging SQLite DB.

Reads the six files in data/staging/interlinear/, maps references to KJV
verse keys, selects the main reading, and writes data/staging/
interlinear_staging.db. Research-verified format notes are in
verification/v2/interlinear-source-hunt-report.md.

Mapping decisions (documented):
- TAGNT refs use NRSV versification; [x.y] brackets give the KJV
  equivalent (e.g. Act.2.11[2.10] -> Acts 2:10). (x.y) NA brackets and
  {x.y} Majority-text placements keep the primary (NRSV) ref, which
  matches KJV at those verses.
- TAHOT refs: primary is the English (NRSV) ref; (x.y) is the Hebrew
  versification, ignored for KJV mapping. Verse 0 rows are Psalm titles;
  KJV has no verse 0 (titles join verse 1), so v.0 -> v.1 with src_verse=0
  kept for ordering title words before verse-1 words.
- Main reading: TAGNT types {NKO, NK(O), NK(o)} (words identical in
  virtually all manuscripts); TAHOT types starting with L or Q (Leningrad
  main text incl. minor variants; Qere where Q/K choice exists; the file
  already resolves each position to a single row). X (LXX-derived) and R
  (restored) rows are kept with is_main=0, as are non-NKO Greek variants.
- Spanish translation and sub-meaning columns are excluded (unverified
  third-party provenance).
- Gloss: TAGNT primary = "Dictionary form = Gloss" (TBESG-derived);
  secondary = English translation column (BSB-derived). TAHOT gloss =
  Translation column (STEPBible's own).
- Strong's: sStrong+Instance column (TAGNT) / Root dStrong+Instance
  (TAHOT); instance marks (_A, _b) stripped; comma-separated multiples
  preserved.
- Lemma: TAGNT from "dictform=gloss"; TAHOT from the braced root segment
  of Expanded Strong tags ({Hxxxx=lemma=...}), NULL when absent.
"""

import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

STAGING = Path(__file__).resolve().parent.parent / "data" / "staging"
SRC = STAGING / "interlinear"
OUT = STAGING / "interlinear_staging.db"

BOOK_MAP = {
    "Gen": "Genesis", "Exo": "Exodus", "Lev": "Leviticus", "Num": "Numbers",
    "Deu": "Deuteronomy", "Jos": "Joshua", "Jdg": "Judges", "Rut": "Ruth",
    "1Sa": "1 Samuel", "2Sa": "2 Samuel", "1Ki": "1 Kings", "2Ki": "2 Kings",
    "1Ch": "1 Chronicles", "2Ch": "2 Chronicles", "Ezr": "Ezra",
    "Neh": "Nehemiah", "Est": "Esther", "Job": "Job", "Psa": "Psalms",
    "Pro": "Proverbs", "Ecc": "Ecclesiastes", "Sng": "Song of Songs",
    "Isa": "Isaiah", "Jer": "Jeremiah", "Lam": "Lamentations",
    "Ezk": "Ezekiel", "Dan": "Daniel", "Hos": "Hosea", "Jol": "Joel",
    "Amo": "Amos", "Oba": "Obadiah", "Jon": "Jonah", "Mic": "Micah",
    "Nam": "Nahum", "Hab": "Habakkuk", "Zep": "Zephaniah", "Hag": "Haggai",
    "Zec": "Zechariah", "Mal": "Malachi",
    "Mat": "Matthew", "Mrk": "Mark", "Luk": "Luke", "Jhn": "John",
    "Act": "Acts", "Rom": "Romans", "1Co": "1 Corinthians",
    "2Co": "2 Corinthians", "Gal": "Galatians", "Eph": "Ephesians",
    "Php": "Philippians", "Col": "Colossians", "1Th": "1 Thessalonians",
    "2Th": "2 Thessalonians", "1Ti": "1 Timothy", "2Ti": "2 Timothy",
    "Tit": "Titus", "Phm": "Philemon", "Heb": "Hebrews", "Jas": "James",
    "1Pe": "1 Peter", "2Pe": "2 Peter", "1Jn": "1 John", "2Jn": "2 John",
    "3Jn": "3 John", "Jud": "Jude", "Rev": "Revelation",
}

REF = re.compile(
    r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)"
    r"((?:\[[^\]]*\]|\{[^\}]*\}|\([^\)]*\))*)"
    r"#(\d+)=([A-Za-z()+]+)$"
)
BRK = re.compile(r"\[([^\]]*)\]|\{([^\}]*)\}|\(([^\)]*)\)")
INST = re.compile(r"_[A-Za-z]$")
LEMMA_BRACE = re.compile(r"\{H\d+[A-Z]?\s*=\s*([^=]+?)\s*=")

# Main-reading rule (documented edition selection):
# - TAGNT: any word attested in the Nestle-Aland/SBL critical text, i.e. its
#   type contains 'N' or 'n' (NKO, N(k)O, NO, no, n, ...). K-only / O-only
#   types (Byzantine/Majority/TR-only readings) are variants. Verified:
#   N(k)O and 'no' words (e.g. Mat 1:18#06; 1Co 3:5#07) appear in NA28.
# - TAHOT: Leningrad main text (L...) incl. translators' Qere choice (Q...).
#   X/R rows are variants.
TAGNT_MAIN_RE = re.compile(r"[Nn]")


def clean_strongs(raw: str) -> str:
    """Strip STEPBible instance suffixes (_A, _b) and the trailing uppercase
    sub-entry letter (H7225G -> H7225) so the number works directly in
    /v1/word. Preserves comma-separated multiple numbers."""
    parts = []
    for p in raw.split(","):
        p = p.strip()
        p = INST.sub("", p)
        p = re.sub(r"[A-Z]$", "", p)  # sub-entry letter -> base number
        if p:
            parts.append(p)
    return ", ".join(parts)


def split_word_translit(cell: str):
    m = re.match(r"^(.*) \(([^)]*)\)$", cell)
    if m:
        return m.group(1), m.group(2)
    return cell, ""


def parse_tagnt_row(cols):
    ref = cols[0]
    m = REF.match(ref)
    code, ch, vs, brackets, pos, wtype = (
        m.group(1), int(m.group(2)), int(m.group(3)),
        m.group(4), int(m.group(5)), m.group(6),
    )
    kjv_ch, kjv_vs = ch, vs
    for sq, cu, pa in BRK.findall(brackets):
        if sq and "." in sq:  # KJV bracket wins
            kjv_ch, kjv_vs = (int(x) for x in sq.split("."))
    word, translit = split_word_translit(cols[1])
    gloss_alt = cols[2] if len(cols) > 2 else ""
    dsm = cols[3] if len(cols) > 3 else ""
    strongs_d, morph = (dsm.split("=", 1) + [""])[:2] if "=" in dsm else ("", dsm)
    lg = cols[4] if len(cols) > 4 else ""
    lemma = lg.split("=", 1)[0] if "=" in lg else ""
    gloss = lg.split("=", 1)[1] if "=" in lg else ""
    strongs = clean_strongs(cols[11]) if len(cols) > 11 else ""
    return {
        "book": BOOK_MAP[code], "chapter": kjv_ch, "verse": kjv_vs,
        "src_ch": ch, "src_verse": vs, "heb_ch": ch, "heb_verse": vs,
        "position": pos, "word": word,
        "transliteration": translit, "gloss": gloss, "gloss_alt": gloss_alt,
        "strongs": strongs, "morphology": morph, "lemma": lemma,
        "word_type": wtype, "is_main": 1 if TAGNT_MAIN_RE.search(wtype) else 0,
        "src_ref": ref,
    }


def parse_tahot_row(cols):
    ref = cols[0]
    m = REF.match(ref)
    code, ch, vs, brackets, pos, wtype = (
        m.group(1), int(m.group(2)), int(m.group(3)),
        m.group(4), int(m.group(5)), m.group(6),
    )
    kjv_vs = vs if vs != 0 else 1  # psalm titles -> verse 1
    heb_ch, heb_vs = ch, vs
    pm = re.search(r"\((\d+)\.(\d+)\)", brackets)
    if pm:
        heb_ch, heb_vs = int(pm.group(1)), int(pm.group(2))
    word = cols[1] if len(cols) > 1 else ""
    translit = cols[2] if len(cols) > 2 else ""
    gloss = cols[3] if len(cols) > 3 else ""
    morph = cols[5] if len(cols) > 5 else ""
    strongs = clean_strongs(cols[8]) if len(cols) > 8 else ""
    expanded = cols[11] if len(cols) > 11 else ""
    lm = LEMMA_BRACE.search(expanded)
    lemma = lm.group(1) if lm else ""
    return {
        "book": BOOK_MAP[code], "chapter": ch, "verse": kjv_vs,
        "src_ch": ch, "src_verse": vs, "heb_ch": heb_ch, "heb_verse": heb_vs,
        "position": pos, "word": word,
        "transliteration": translit, "gloss": gloss, "gloss_alt": "",
        "strongs": strongs, "morphology": morph, "lemma": lemma,
        "word_type": wtype, "is_main": 1 if wtype[0] in ("L", "Q") else 0,
        "src_ref": ref,
    }


def main():
    if OUT.exists():
        OUT.unlink()
    con = sqlite3.connect(OUT)
    con.execute(
        """CREATE TABLE words (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            book TEXT NOT NULL, chapter INTEGER NOT NULL, verse INTEGER NOT NULL,
            src_ch INTEGER NOT NULL, src_verse INTEGER NOT NULL,
            heb_ch INTEGER NOT NULL, heb_verse INTEGER NOT NULL,
            position INTEGER NOT NULL,
            word TEXT NOT NULL, transliteration TEXT, gloss TEXT, gloss_alt TEXT,
            strongs TEXT, morphology TEXT, lemma TEXT,
            word_type TEXT NOT NULL, is_main INTEGER NOT NULL, src_ref TEXT
        )"""
    )
    stats = Counter()
    skipped = []
    files = sorted(SRC.glob("TAGNT*.txt")) + sorted(SRC.glob("TAHOT*.txt"))
    assert len(files) == 6, f"expected 6 files, got {len(files)}"
    for f in files:
        is_greek = f.name.startswith("TAGNT")
        source_id = "step_tagnt" if is_greek else "step_tahot"
        with open(f, encoding="utf-8-sig") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.rstrip("\n")
                if not line or "\t" not in line:
                    continue
                cols = line.split("\t")
                if not REF.match(cols[0]):
                    continue  # header / verse-text rows
                try:
                    row = (parse_tagnt_row(cols) if is_greek
                           else parse_tahot_row(cols))
                except Exception as exc:  # noqa: BLE001
                    skipped.append((f.name, lineno, cols[0][:60], str(exc)))
                    continue
                row["source_id"] = source_id
                con.execute(
                    """INSERT INTO words (source_id, book, chapter, verse,
                        src_ch, src_verse, heb_ch, heb_verse,
                        position, word, transliteration, gloss,
                        gloss_alt, strongs, morphology, lemma, word_type,
                        is_main, src_ref)
                       VALUES (:source_id, :book, :chapter, :verse,
                        :src_ch, :src_verse, :heb_ch, :heb_verse,
                        :position, :word, :transliteration, :gloss, :gloss_alt,
                        :strongs, :morphology, :lemma, :word_type, :is_main,
                        :src_ref)""",
                    row,
                )
                stats[source_id] += 1
                # batched commits: one giant transaction does not survive
                # process exit on this box; commit every 5k rows.
                if (stats[source_id] % 5000) == 0:
                    con.commit()
                stats[source_id + "_main" if row["is_main"] else
                      source_id + "_var"] += 1
                if not row["gloss"]:
                    stats[source_id + "_nongloss"] += 1
                if not row["strongs"]:
                    stats[source_id + "_nostrongs"] += 1
                if not row["lemma"]:
                    stats[source_id + "_nolemma"] += 1
        con.commit()  # per-file commit: never leave a file's tail uncommitted
    con.commit()  # final commit for any partial trailing batch
    print("rows:", dict(stats))
    print("skipped:", len(skipped))
    for s in skipped[:10]:
        print("  SKIP", s)

    # split-verse analysis: KJV verses fed by more than one src VERSE
    # (e.g. 1Ki.18.33 + 1Ki.18.33(18.34): Hebrew versification splits the
    # English verse). These get sequential positions ordered by
    # (src_ch, src_verse, heb_ch, heb_verse, position) at merge time.
    # NOTE: src_ref includes the word number, so strip it for verse grouping.
    splits = con.execute(
        """SELECT book, chapter, verse,
                  COUNT(DISTINCT substr(src_ref, 1, instr(src_ref, '#') - 1)) AS nsrc,
                  COUNT(*) AS nwords
           FROM words WHERE is_main = 1
           GROUP BY book, chapter, verse HAVING nsrc > 1"""
    ).fetchall()
    print("KJV verses with split src verses:", len(splits))
    for s in splits[:12]:
        print("  SPLIT", s)
    # true duplicates: same src_ref + position twice
    dups = con.execute(
        """SELECT src_ref, position, COUNT(*)
           FROM words
           GROUP BY src_ref, position HAVING COUNT(*) > 1"""
    ).fetchall()
    print("true (src_ref, position) duplicates:", len(dups))
    for d in dups[:10]:
        print("  DUP", d)
    # verses covered
    n_verses = con.execute(
        "SELECT COUNT(DISTINCT book || chapter || verse) FROM words "
        "WHERE is_main = 1").fetchone()[0]
    print("distinct KJV verses (main reading):", n_verses)
    con.close()


if __name__ == "__main__":
    main()
