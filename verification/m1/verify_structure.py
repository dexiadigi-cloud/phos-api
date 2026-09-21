#!/usr/bin/env python3
"""M1 structural verification for Phos scripture.db. Writes raw output files."""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path.home() / "workspace" / "scripture-desk"
DB = ROOT / "data" / "scripture.db"
OUT = ROOT / "verification" / "m1" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

CANON = ["Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
"1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah",
"Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Songs","Isaiah","Jeremiah",
"Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum",
"Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew","Mark","Luke","John",
"Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians",
"Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus",
"Philemon","Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"]

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
report = []

# 1. integrity_check
ic = con.execute("PRAGMA integrity_check").fetchall()
(OUT/"integrity_check.txt").write_text("\n".join(r[0] for r in ic) + "\n")
report.append(f"integrity_check: {ic}")

# 2. books per translation in canonical order
for tr in ("BSB","KJV","WEB","ASV"):
    rows = con.execute("SELECT DISTINCT book, book_order FROM verses WHERE translation=? ORDER BY book_order", (tr,)).fetchall()
    (OUT/f"books_{tr.lower()}.txt").write_text(
        "\n".join(f"{o:02d} {b}" for b,o in rows) + "\n")
    canon_ok = [b for b,o in rows] == CANON and len(rows) == 66
    report.append(f"{tr} books: {len(rows)} rows, canonical-order match={canon_ok}")
    if not canon_ok:
        report.append(f"  MISSING: {set(CANON)-{b for b,o in rows}} EXTRA: {{b for b,o in rows}}-set(CANON)")

# 3. counts per translation
counts = con.execute("SELECT translation, COUNT(*) FROM verses GROUP BY translation").fetchall()
(OUT/"counts.txt").write_text("\n".join(f"{t} {n}" for t,n in counts)+"\n")
report.append(f"counts: {dict(counts)}")

# 4. duplicate verse keys
dups = con.execute("""SELECT translation, book, chapter, verse, COUNT(*) c FROM verses
GROUP BY translation, book, chapter, verse HAVING c>1 LIMIT 50""").fetchall()
(OUT/"duplicates.txt").write_text(str(dups)+"\n")
report.append(f"duplicate verse keys: {len(dups)} ({'NONE' if not dups else 'FOUND'})")

# 5. empty/null/whitespace-only texts
bad = con.execute("""SELECT translation, book, chapter, verse FROM verses
WHERE text IS NULL OR TRIM(text)='' LIMIT 50""").fetchall()
(OUT/"empty_texts.txt").write_text(str(bad)+"\n")
report.append(f"empty/null/whitespace-only texts: {len(bad)}")

# 6. markup leakage
leak_patterns = [
    (r"\\[a-zA-Z]", "USFM backslash-marker"),
    (r"<[^>]+>", "HTML/XML tag"),
    (r"\{[^}]*\}", "curly-brace markup"),
]
leak_rows = []
con.create_function("regexp", 2, lambda p, s: 1 if re.search(p, s or "") else 0)
for pat, name in leak_patterns:
    rows = con.execute("""SELECT translation, book, chapter, verse, substr(text,1,100)
    FROM verses WHERE regexp(?, text)""", (pat,)).fetchall()
    leak_rows.append((name, len(rows), rows[:10]))
with open(OUT/"markup_leakage.txt","w") as f:
    for name, n, samples in leak_rows:
        f.write(f"== {name}: {n} rows ==\n")
        for s in samples:
            f.write(str(s)+"\n")
report.append("markup leakage: " + ", ".join(f"{n}={cnt}" for n,cnt,s in leak_rows))

# 7. chapter counts per book per translation
with open(OUT/"chapter_counts.txt","w") as f:
    for tr in ("BSB","KJV","WEB","ASV"):
        rows = con.execute("""SELECT book, MAX(chapter) FROM verses WHERE translation=?
        GROUP BY book_order ORDER BY book_order""", (tr,)).fetchall()
        f.write(f"== {tr} ==\n")
        for b,c in rows:
            f.write(f"{b}: {c}\n")
report.append("chapter_counts written")

# 8. FTS5 sample queries
fts_tests = [
    ("in the beginning", "BSB"),
    ("love neighbour", "BSB"),
    ("psalm shepherd", "BSB"),
    ("faith", "KJV"),
    ("grace", "WEB"),
]
fts_rows = []
for q, tr in fts_tests:
    try:
        rows = con.execute("""SELECT translation, book, chapter, verse, substr(text,1,60)
        FROM verses_fts JOIN verses ON verses.rowid=verses_fts.rowid
        WHERE verses_fts MATCH ? AND translation=? LIMIT 3""", (q, tr)).fetchall()
    except Exception as e:
        rows = [("ERR", str(e))]
    fts_rows.append((q, tr, rows))
with open(OUT/"fts_checks.txt","w") as f:
    for q, tr, rows in fts_rows:
        f.write(f"== query={q!r} tr={tr} ==\n")
        for r in rows:
            f.write(str(r)+"\n")
report.append("FTS5 checks written")

# 9. ranged verse keys (BSB) - count and list
rng = con.execute("SELECT book, chapter, verse, substr(text,1,60) FROM verses WHERE translation='BSB' AND verse LIKE '%-%'").fetchall()
(OUT/"bsb_ranges.txt").write_text("\n".join(f"{b} {c}:{v} {t}" for b,c,v,t in rng)+"\n")
report.append(f"BSB ranged verse keys: {len(rng)}")

con.close()
(OUT/"structural_summary.txt").write_text("\n".join(report)+"\n")
print("\n".join(report))
