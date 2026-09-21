#!/usr/bin/env python3
"""Deterministic source-to-DB checks. SEED=20260920. 20+ random verse picks,
raw source text pulled independently of ingest parsers, compared to DB."""
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

SEED = 20260920
ROOT = Path.home() / "workspace" / "scripture-desk"
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "scripture.db"
OUT = ROOT / "verification" / "m1" / "raw"

# Book code map for BSB USFM filenames (independent list, canonical order)
CODE = {"Genesis":"GEN","Exodus":"EXO","Leviticus":"LEV","Numbers":"NUM","Deuteronomy":"DEU",
"Joshua":"JOS","Judges":"JDG","Ruth":"RUT","1 Samuel":"1SA","2 Samuel":"2SA","1 Kings":"1KI",
"2 Kings":"2KI","1 Chronicles":"1CH","2 Chronicles":"2CH","Ezra":"EZR","Nehemiah":"NEH",
"Esther":"EST","Job":"JOB","Psalms":"PSA","Proverbs":"PRO","Ecclesiastes":"ECC",
"Song of Songs":"SNG","Isaiah":"ISA","Jeremiah":"JER","Lamentations":"LAM","Ezekiel":"EZK",
"Daniel":"DAN","Hosea":"HOS","Joel":"JOL","Amos":"AMO","Obadiah":"OBA","Jonah":"JON",
"Micah":"MIC","Nahum":"NAM","Habakkuk":"HAB","Zephaniah":"ZEP","Haggai":"HAG",
"Zechariah":"ZEC","Malachi":"MAL","Matthew":"MAT","Mark":"MRK","Luke":"LUK","John":"JHN",
"Acts":"ACT","Romans":"ROM","1 Corinthians":"1CO","2 Corinthians":"2CO","Galatians":"GAL",
"Ephesians":"EPH","Philippians":"PHP","Colossians":"COL","1 Thessalonians":"1TH",
"2 Thessalonians":"2TH","1 Timothy":"1TI","2 Timothy":"2TI","Titus":"TIT","Philemon":"PHM",
"Hebrews":"HEB","James":"JAS","1 Peter":"1PE","2 Peter":"2PE","1 John":"1JN","2 John":"2JN",
"3 John":"3JN","Jude":"JUD","Revelation":"REV"}

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

def db_text(tr, book, ch, v):
    r = con.execute("SELECT text FROM verses WHERE translation=? AND book=? AND chapter=? AND verse=?",
                    (tr, book, ch, v)).fetchone()
    return r[0] if r else None

# --- independent raw readers (do NOT reuse ingest_m1 parsers) ---
def raw_kjv(book, ch, v):
    d = json.loads((RAW/"kjv_src"/f"{book}.json").read_text(encoding="utf-8"))
    return re.sub(r"\s+"," ",d[str(ch)][str(v)]).strip()

def raw_bsb(book, ch, v):
    raw = (RAW/"bsb_usfm"/f"{CODE[book]}.usfm").read_text(encoding="utf-8")
    # split chapters then verses independently
    ch_parts = re.split(r"\\c\s+(\d+)", raw)
    body = None
    for i in range(1, len(ch_parts), 2):
        if int(ch_parts[i]) == ch:
            body = ch_parts[i+1]; break
    v_parts = re.split(r"\\v\s+(\d+(?:-\d+)?)", body)
    text = None
    for i in range(1, len(v_parts), 2):
        if v_parts[i] == v:
            text = v_parts[i+1]; break
    text = re.sub(r"\\f\b.*?\\f\*", "", text, flags=re.DOTALL)   # footnotes
    text = re.sub(r"\\[a-zA-Z]+\d*\*?", "", text)               # markers
    text = text.replace("|","")
    return re.sub(r"\s+"," ",text).strip()

_getb = None
def raw_getbible(path, book, ch, v):
    global _getb
    if _getb is None: _getb = {}
    if str(path) not in _getb:
        _getb[str(path)] = json.loads(Path(path).read_text(encoding="utf-8"))
    d = _getb[str(path)]
    for bk in d["books"]:
        if bk["name"] == book:
            for c in bk["chapters"]:
                for vv in c["verses"]:
                    if int(vv["chapter"]) == ch and str(vv["verse"]) == v:
                        return re.sub(r"\s+"," ",vv["text"]).strip()
    return None

def raw_text(tr, book, ch, v):
    if tr == "KJV": return raw_kjv(book, ch, v)
    if tr == "BSB": return raw_bsb(book, ch, v)
    if tr == "WEB": return raw_getbible(RAW/"web.json", book, ch, v)
    if tr == "ASV": return raw_getbible(RAW/"asv.json", book, ch, v)

def norm(t):
    return re.sub(r"\s+"," ",t or "").strip()

def words(t):
    return re.sub(r"[^\w\s']","",t.lower()).split()

rng = random.Random(SEED)
# all DB keys per translation to sample from
keys = {}
for tr in ("BSB","KJV","WEB","ASV"):
    keys[tr] = con.execute("SELECT book, chapter, verse FROM verses WHERE translation=?",(tr,)).fetchall()

plan = [("BSB",6),("KJV",6),("WEB",4),("ASV",4)]
picks = []
for tr, n in plan:
    picks += [(tr,)+rng.choice(keys[tr]) for _ in range(n)]
# add 4 fixed notable verses (one per translation)
picks += [("BSB","Genesis",1,"1"),("KJV","John",3,"16"),("WEB","Psalms",23,"1"),("ASV","Romans",8,"28")]

results = []
npass = 0
with open(OUT/"random_checks.txt","w") as f:
    f.write(f"SEED={SEED}, picks={len(picks)} (20 random + 4 fixed)\n")
    for i,(tr,book,ch,v) in enumerate(picks):
        try:
            src = raw_text(tr,book,ch,v)
            db = db_text(tr,book,ch,v)
        except Exception as e:
            src, db = None, f"READ-ERROR: {e}"
        if tr == "BSB":
            # BSB raw has been marker-stripped; compare word sequences (lossy-clean acknowledged)
            ok = words(src) == words(db) if (src and db) else False
            how = "word-sequence"
        else:
            ok = norm(src) == norm(db)
            how = "exact-normalized"
        npass += ok
        status = "PASS" if ok else "FAIL"
        f.write(f"[{i:02d}] {status} {tr} {book} {ch}:{v} ({how})\n")
        f.write(f"  DB : {db[:110] if db else None}\n")
        f.write(f"  SRC: {src[:110] if src else None}\n")
        results.append((status,tr,book,ch,v))
    f.write(f"TOTAL: {npass}/{len(picks)} pass\n")

print(f"random checks: {npass}/{len(picks)} pass")
for r in results:
    if r[0]=="FAIL": print("FAIL:", r)
