#!/usr/bin/env python3
"""Fetch raw Albert Barnes "Notes on the Bible" HTML via the Wayback Machine.

sacred-texts.com (Internet Sacred Text Archive) hosts the complete Barnes
Notes on the Bible [1834] (all 66 books), but its Cloudflare edge drops
non-browser clients, so bulk retrieval goes through web.archive.org
snapshots of the same public-domain transcription.

Raw layout: data/raw_v2/barnes/<bookcode>.json =
  {"book": {"code","name","book_href","introduction_html"},
   "chapters": {"1": {"url","snapshot","html"}, ...}}
Only stdlib. Polite: single-threaded, ~1s between requests, retries.
Re-running resumes (skips chapters already saved). Use --refetch to redo.
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import db  # noqa: E402

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw_v2" / "barnes"
RETRIEVAL_DATE = "2026-09-20"
ORIGIN = "https://sacred-texts.com/bib/cmt/barnes"

# sacred-texts book code -> canonical book name (from their index page)
BOOKS = [
    ("gen", "Genesis"), ("exo", "Exodus"), ("lev", "Leviticus"),
    ("num", "Numbers"), ("deu", "Deuteronomy"), ("jos", "Joshua"),
    ("jdg", "Judges"), ("rut", "Ruth"), ("sa1", "1 Samuel"),
    ("sa2", "2 Samuel"), ("kg1", "1 Kings"), ("kg2", "2 Kings"),
    ("ch1", "1 Chronicles"), ("ch2", "2 Chronicles"), ("ezr", "Ezra"),
    ("neh", "Nehemiah"), ("est", "Esther"), ("job", "Job"),
    ("psa", "Psalms"), ("pro", "Proverbs"), ("ecc", "Ecclesiastes"),
    ("sol", "Song of Songs"), ("isa", "Isaiah"), ("jer", "Jeremiah"),
    ("lam", "Lamentations"), ("eze", "Ezekiel"), ("dan", "Daniel"),
    ("hos", "Hosea"), ("joe", "Joel"), ("amo", "Amos"),
    ("oba", "Obadiah"), ("jon", "Jonah"), ("mic", "Micah"),
    ("nah", "Nahum"), ("hab", "Habakkuk"), ("zep", "Zephaniah"),
    ("hag", "Haggai"), ("zac", "Zechariah"), ("mal", "Malachi"),
    ("mat", "Matthew"), ("mar", "Mark"), ("luk", "Luke"),
    ("joh", "John"), ("act", "Acts"), ("rom", "Romans"),
    ("co1", "1 Corinthians"), ("co2", "2 Corinthians"),
    ("gal", "Galatians"), ("eph", "Ephesians"), ("phi", "Philippians"),
    ("col", "Colossians"), ("th1", "1 Thessalonians"),
    ("th2", "2 Thessalonians"), ("ti1", "1 Timothy"),
    ("ti2", "2 Timothy"), ("tit", "Titus"), ("plm", "Philemon"),
    ("heb", "Hebrews"), ("jam", "James"), ("pe1", "1 Peter"),
    ("pe2", "2 Peter"), ("jo1", "1 John"), ("jo2", "2 John"),
    ("jo3", "3 John"), ("jde", "Jude"), ("rev", "Revelation"),
]

UA = {"User-Agent": "PhosDexiaBot/1.0 (research staging; contact via project)"}
SLEEP = 1.0


def http_get(url, tries=8, timeout=60):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.status == 200 and body and b"Temporarily Offline" not in body[:4000]:
                    return body
                last = f"HTTP {r.status} (offline-page?)"
        except Exception as e:  # noqa: BLE001
            last = repr(e)[:120]
        time.sleep(SLEEP * (k + 1) + 2)
    raise RuntimeError(f"GET failed after {tries} tries: {url} ({last})")


def cdx_snapshots(original_url, limit=8):
    """List (timestamp, original) of 200-status snapshots, newest last."""
    q = urllib.parse.urlencode({
        "url": original_url,
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
        "limit": str(limit),
    })
    try:
        body = http_get(f"http://web.archive.org/cdx/search/cdx?{q}", tries=4)
    except RuntimeError:
        return []
    rows = [l.split(" ") for l in body.decode("utf-8", "replace").strip().splitlines()
            if l.strip()]
    return [(r[0], r[1]) for r in rows if len(r) >= 3]


def wayback_get(original_url, must_contain):
    """Fetch best snapshot; validate content; fall back across snapshots."""
    cands = [(None, original_url)]  # (timestamp, url) - None => nearest redirect
    cands += [(ts, f"http://web.archive.org/web/{ts}id_/{orig}")
              for ts, orig in cdx_snapshots(original_url)]
    tried = []
    for ts, url in cands:
        if ts is None:
            url = f"http://web.archive.org/web/2015id_/{original_url}"
        try:
            body = http_get(url, tries=3)
        except RuntimeError as e:
            tried.append(f"{ts or 'nearest'}: {e}")
            continue
        text = body.decode("utf-8", "replace")
        if all(s in text for s in must_contain):
            return text, ts or "nearest-2015"
        tried.append(f"{ts or 'nearest'}: validation failed")
        time.sleep(SLEEP)
    return None, " | ".join(tried)[:200]


def book_intro(html_text):
    """Extract the book-page introduction HTML (between the H1 block and chapter list)."""
    m = re.search(r"</CENTER>\s*<HR>(.*?)<HR>", html_text, re.S | re.I)
    if not m:
        return ""
    return m.group(1).strip()[:20000]


def fetch_book(code, name, nchapters, refetch=False):
    dest = RAW_DIR / f"{code}.json"
    data = {"book": {"code": code, "name": name}, "chapters": {}}
    if dest.exists() and not refetch:
        data = json.loads(dest.read_text(encoding="utf-8"))
    have = set(data["chapters"].keys())

    if "introduction_html" not in data["book"]:
        bhtml, bts = wayback_get(f"{ORIGIN}/{code}.htm", must_contain=[f"{code}001.htm"])
        data["book"]["book_href"] = f"{code}.htm"
        data["book"]["book_snapshot"] = bts
        data["book"]["introduction_html"] = book_intro(bhtml) if bhtml else ""
        print(f"[{code}] book page snapshot {bts}", flush=True)
        time.sleep(SLEEP)

    for ch in range(1, nchapters + 1):
        if str(ch) in have and not refetch:
            continue
        url = f"{ORIGIN}/{code}{ch:03d}.htm"
        html_text, ts = wayback_get(url, must_contain=['NAME="an_000"', f"{code} {ch}:0"])
        if html_text is None:
            print(f"[{code}] ch{ch}: FAILED ({ts})", flush=True)
            data["chapters"][str(ch)] = {"url": url, "snapshot": None,
                                         "html": None, "error": ts}
        else:
            data["chapters"][str(ch)] = {"url": url, "snapshot": ts, "html": html_text}
        time.sleep(SLEEP)
        if ch % 10 == 0 or ch == nchapters:
            dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    n = sum(1 for v in data["chapters"].values() if v.get("html"))
    print(f"[{code}] done: {n}/{nchapters} chapters", flush=True)
    return dest


def main(argv):
    refetch = "--refetch" in argv
    only = [a.split("=", 1)[1] for a in argv if a.startswith("--only=")]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    bounds = db.get_bounds("KJV")
    manifest = {
        "source_id": "barnes",
        "title": "Albert Barnes' Notes on the Bible [1834]",
        "origin": ORIGIN,
        "origin_note": ("Complete 66-book transcription hosted by the Internet "
                        "Sacred Text Archive; retrieved via web.archive.org "
                        "snapshots because sacred-texts.com edge blocks "
                        "non-browser clients."),
        "retrieved": RETRIEVAL_DATE,
        "rights": "Public domain (author d. 1870; work dated [1834])",
        "files": [],
    }
    for code, name in BOOKS:
        if only and code not in only:
            continue
        nch = bounds[name]["chapters"]
        dest = fetch_book(code, name, nch, refetch=refetch)
        manifest["files"].append({
            "file": dest.name,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "bytes": dest.stat().st_size,
        })
        (RAW_DIR / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
    print("MANIFEST written", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
