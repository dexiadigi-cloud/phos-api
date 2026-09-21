#!/usr/bin/env python3
"""Fetch the 23 Matthew Henry chapters missing from HelloAO, from CCEL.

HelloAO's matthew-henry dataset lacks: Song of Songs (all 8 ch),
Jonah 2-4, Matthew 19-28, 2 Samuel 23-24. CCEL's "Commentary on the Whole
Bible" (6 vols, mhc1-mhc6) is a faithful transcription of the same
public-domain original (verified: unmodernized 18th-c. English).

Raw output: data/raw_v2/matthew_henry/CCEL_GAPS.json =
  {"chapters": [{"usfm","chapter","url","content_html"}, ...]}
Only stdlib. Polite sequential fetch.
"""
import json
import re
import time
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw_v2" / "matthew_henry"
RETRIEVAL_DATE = "2026-09-20"
UA = {"User-Agent": "PhosDexiaBot/1.0 (research staging)"}

ROMAN = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v", 6: "vi", 7: "vii",
         8: "viii", 9: "ix", 10: "x", 11: "xi", 12: "xii", 13: "xiii",
         14: "xiv", 15: "xv", 16: "xvi", 17: "xvii", 18: "xviii",
         19: "xix", 20: "xx", 21: "xxi", 22: "xxii", 23: "xxiii",
         24: "xxiv", 25: "xxv", 26: "xxvi", 27: "xxvii", 28: "xxviii",
         29: "xxix", 30: "xxx"}

# (volume, ccel book slug, usfm, chapters); content page N = roman(N+1)
# because page i is always the book preface.
GAPS = [
    ("mhc3", "Song", "SNG", list(range(1, 9))),
    ("mhc4", "Jonah", "JON", [2, 3, 4]),
    ("mhc5", "Matt", "MAT", list(range(19, 29))),
    ("mhc2", "2Sam", "2SA", [23, 24]),
]


def get(url, tries=5):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status == 200:
                    return r.read().decode("utf-8", "replace")
                last = f"HTTP {r.status}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)[:120]
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"GET failed: {url} ({last})")


def extract_content(html_text):
    m = re.search(r'<div[^>]*class="book-content"[^>]*>(.*?)<div[^>]*class="content-foot"',
                  html_text, re.S)
    if not m:
        raise RuntimeError("book-content div not found")
    return m.group(1).strip()


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / "CCEL_GAPS.json"
    out = {"provenance": {
        "source": "Christian Classics Ethereal Library (ccel.org)",
        "work": "Matthew Henry, Commentary on the Whole Bible (6 vols)",
        "rights": "Public domain (author d. 1714)",
        "retrieved": RETRIEVAL_DATE,
        "note": ("Gap-fill for the 23 chapters absent from HelloAO's "
                 "matthew-henry dataset. Verified unmodernized; same work."),
    }, "chapters": []}
    for vol, slug, usfm, chapters in GAPS:
        for ch in chapters:
            roman = ROMAN[ch + 1]
            url = f"https://ccel.org/ccel/henry/{vol}/{vol}.{slug}.{roman}.html"
            html_text = get(url)
            content = extract_content(html_text)
            # sanity: page should name the right chapter
            head = re.sub(r"<[^>]+>", " ", content[:3000])
            out["chapters"].append({
                "usfm": usfm, "chapter": ch, "url": url,
                "content_html": content,
                "heading_hint": re.sub(r"\s+", " ", head).strip()[:160],
            })
            print(f"[{usfm} {ch}] {url} ({len(content)} chars)", flush=True)
            time.sleep(0.6)
    dest.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {dest} ({len(out['chapters'])} chapters)", flush=True)


if __name__ == "__main__":
    main()
