"""Final Strong's ingest: parse with best parsers, manually recover H430, write to DB."""
import sys, sqlite3, json
sys.path.insert(0, 'scripts')
from pathlib import Path
import repair_strongs_simple as rss
import repair_strongs_greek as rg

RAW = Path("data/raw_v2/strongs")

def get_entry_text(lines, start_li, end_li):
    """Extract entry text from start line to end line (exclusive of next heading)."""
    text_lines = []
    for i in range(start_li, end_li):
        text_lines.append(lines[i].strip())
    return " ".join(t for t in text_lines if t)

# Parse Hebrew with simple (passing)
print("Parsing Hebrew...")
fname, lang, prefix, max_num, gaps = rss.FILES[1]
lines_h, entries_h, _ = rss.parse_one(fname, lang, prefix, max_num, gaps)
print(f"Hebrew: {len(entries_h)} entries")

# Parse Greek with positional (best effort)
print("Parsing Greek...")
fname, lang, prefix, max_num, gaps = rg.FILES[0]
lines_g, entries_g, _ = rg.parse_one(fname, lang, prefix, max_num, gaps)
print(f"Greek: {len(entries_g)} entries")

# Build database rows
rows = []
for entries, lines, prefix, lang in [
    (entries_g, lines_g, "G", "greek"),
    (entries_h, lines_h, "H", "hebrew"),
]:
    emap = {e[0]: e for e in entries}
    nums = sorted(emap.keys())
    for idx, num in enumerate(nums):
        e = emap[num]
        li = e[1]
        # end line is start of next entry, or li+20 if last
        if idx + 1 < len(nums):
            end_li = min(emap[nums[idx+1]][1], len(lines))
        else:
            end_li = li + 20
        entry_text = get_entry_text(lines, li, min(end_li, len(lines), li+20))
        strongs_num = f"{prefix}{num}"
        # Parse headword (simplified: first word after number)
        # For now, store full entry_text
        rows.append((strongs_num, lang, num, None, None, None, None, None, entry_text))

print(f"Total rows: {len(rows)}")

# Manual H430 recovery (OCR heading "r430i" was missed by parser)
# H430 definition is at line 3226: "<-PN 'eloabb, el-o'-ah; ..."
if not any(r[0] == "H430" for r in rows):
    print("Manually recovering H430...")
    # Find the definition
    for i, ln in enumerate(lines_h):
        if "'eloabb" in ln and "el-o'-ah" in ln:
            def_text = get_entry_text(lines_h, i, i+5)
            rows.append(("H430", "hebrew", 430, None, None, None, None, None, def_text))
            print(f"H430 recovered from line {i+1}")
            break

print(f"Final total rows: {len(rows)}")

# Write to database (in transaction)
db_path = Path("data/study.db")
bak_path = Path("data/study.db.bak-strongs-repair")
print(f"Backup exists: {bak_path.exists()}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()
# Clear existing strongs table
cur.execute("DELETE FROM strongs")
# Insert new rows
cur.executemany(
    "INSERT INTO strongs (strongs_number, language, num, headword_original, transliteration, pronunciation, etymology, kjv_glosses, entry_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    rows
)
conn.commit()

# Verify
cur.execute("SELECT COUNT(*) FROM strongs WHERE language='greek'")
g = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM strongs WHERE language='hebrew'")
h = cur.fetchone()[0]
print(f"DB: Greek={g}, Hebrew={h}, Total={g+h}")

# Check seeded
for sn in ["G1", "G3056", "G5624", "H1", "H430", "H8674"]:
    cur.execute("SELECT strongs_number FROM strongs WHERE strongs_number=?", (sn,))
    print(f"{sn}: {'FOUND' if cur.fetchone() else 'MISSING'}")

cur.execute("PRAGMA integrity_check")
print(f"Integrity: {cur.fetchone()[0]}")
conn.close()
