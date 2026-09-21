#!/usr/bin/env python3
"""Verse-key diffs: WEB/ASV vs KJV. Raw output to verification/m1/raw."""
import sqlite3
from pathlib import Path

ROOT = Path.home() / "workspace" / "scripture-desk"
OUT = ROOT / "verification" / "m1" / "raw"
con = sqlite3.connect(f"file:{ROOT/'data'/'scripture.db'}?mode=ro", uri=True)

def keys(tr):
    return {(b, c, v) for (b, c, v) in
            con.execute("SELECT book, chapter, verse FROM verses WHERE translation=?", (tr,))}

kjv, web, asv = keys("KJV"), keys("WEB"), keys("ASV")
web_missing = sorted(kjv - web)     # in KJV but not WEB
web_extra   = sorted(web - kjv)     # in WEB but not KJV
asv_missing = sorted(kjv - asv)
asv_extra   = sorted(asv - kjv)

with open(OUT/"verse_diffs_web.txt","w") as f:
    f.write(f"WEB rows={len(web)} KJV rows={len(kjv)}\n")
    f.write(f"KJV keys missing in WEB: {len(web_missing)}\n")
    for b,c,v in web_missing: f.write(f"  MISSING {b} {c}:{v}\n")
    f.write(f"WEB keys not in KJV: {len(web_extra)}\n")
    for b,c,v in web_extra: f.write(f"  EXTRA {b} {c}:{v}\n")

with open(OUT/"verse_diffs_asv.txt","w") as f:
    f.write(f"ASV rows={len(asv)} KJV rows={len(kjv)}\n")
    f.write(f"KJV keys missing in ASV: {len(asv_missing)}\n")
    for b,c,v in asv_missing: f.write(f"  MISSING {b} {c}:{v}\n")
    f.write(f"ASV keys not in KJV: {len(asv_extra)}\n")
    for b,c,v in asv_extra: f.write(f"  EXTRA {b} {c}:{v}\n")

# For each missing key, show neighboring verses to judge versification vs data loss
def neighbors(tr, book, ch):
    return {v: t for (v, t) in con.execute(
        "SELECT verse, text FROM verses WHERE translation=? AND book=? AND chapter=? ORDER BY verse",
        (tr, book, ch))}

with open(OUT/"verse_diffs_context.txt","w") as f:
    for tr, miss, name in (("WEB", web_missing, "web"), ("ASV", asv_missing, "asv")):
        f.write(f"===== {tr} missing keys in context =====\n")
        for b, c, v in miss:
            f.write(f"-- {b} {c}:{v} missing in {tr}; same chapter in KJV and {tr}:\n")
            f.write("   KJV: " + "\n   KJV: ".join(
                f"{vv}: {tt[:80]}" for vv, tt in neighbors("KJV", b, c).items()) + "\n")
            f.write("   "+tr+": " + "\n   "+tr+": ".join(
                f"{vv}: {tt[:80]}" for vv, tt in neighbors(tr, b, c).items()) + "\n")
print(f"WEB: missing={len(web_missing)} extra={len(web_extra)}")
print(f"ASV: missing={len(asv_missing)} extra={len(asv_extra)}")
