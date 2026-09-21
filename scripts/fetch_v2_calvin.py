#!/usr/bin/env python3
"""Fetch the 45 CCEL Calvin commentary volumes (calcom01..calcom45) as cache
plain-text files into data/raw_v2/calvin/.

Each CCEL cache txt carries a Dublin Core header block including the volume's
own "Rights: Public Domain" statement. This script records each volume's DC
header (title/creator/print basis/rights) into MANIFEST.json with sha256.

Stdlib only. Polite: single-threaded, ~1s between requests, retries.
Re-running resumes (skips volumes already saved). Use --refetch to redo.
"""
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
RAW_DIR = PROJ / "data" / "raw_v2" / "calvin"
RETRIEVAL_DATE = "2026-09-20"
UA = {"User-Agent": "PhosDexiaBot/1.0 (research staging; contact via project)"}
SLEEP = 1.0

# vol -> (short name) for logging; translators confirmed from archive.org
# metadata of the same Calvin Translation Society 45-volume set.
VOLUMES = {
    "01": "Genesis vol 1", "02": "Genesis vol 2",
    "03": "Four last books of Moses vol 1", "04": "Four last books of Moses vol 2",
    "05": "Four last books of Moses vol 3", "06": "Four last books of Moses vol 4",
    "07": "Joshua",
    "08": "Psalms vol 1", "09": "Psalms vol 2", "10": "Psalms vol 3",
    "11": "Psalms vol 4", "12": "Psalms vol 5",
    "13": "Isaiah vol 1", "14": "Isaiah vol 2", "15": "Isaiah vol 3",
    "16": "Isaiah vol 4",
    "17": "Jeremiah & Lamentations vol 1", "18": "Jeremiah & Lamentations vol 2",
    "19": "Jeremiah & Lamentations vol 3", "20": "Jeremiah & Lamentations vol 4",
    "21": "Jeremiah & Lamentations vol 5",
    "22": "Ezekiel vol 1", "23": "Ezekiel vol 2",
    "24": "Daniel vol 1", "25": "Daniel vol 2",
    "26": "Minor Prophets vol 1", "27": "Minor Prophets vol 2",
    "28": "Minor Prophets vol 3", "29": "Minor Prophets vol 4",
    "30": "Minor Prophets vol 5",
    "31": "Harmony of the Gospels vol 1", "32": "Harmony of the Gospels vol 2",
    "33": "Harmony of the Gospels vol 3",
    "34": "John vol 1", "35": "John vol 2",
    "36": "Acts vol 1", "37": "Acts vol 2",
    "38": "Romans",
    "39": "1 Corinthians", "40": "2 Corinthians",
    "41": "Galatians & Ephesians",
    "42": "Philippians, Colossians, Thessalonians",
    "43": "Timothy, Titus, Philemon",
    "44": "Hebrews",
    "45": "Catholic Epistles",
}


def http_get(url, tries=6, timeout=120):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.status == 200 and body and len(body) > 10000:
                    return body
                last = f"HTTP {r.status} len={len(body)}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)[:150]
        time.sleep(SLEEP * (k + 1) + 2)
    raise RuntimeError(f"GET failed after {tries} tries: {url} ({last})")


def dc_header(text):
    """Extract the Dublin Core header block fields from cache txt."""
    fields = {}
    # Header block sits between the first two underscore rules.
    m = re.search(r"_{10,}\n(.*?)\n\s*_{10,}", text, re.S)
    block = m.group(1) if m else text[:2000]
    for key in ["Title", "Creator(s)", "Print Basis", "Rights",
                "LC Call no", "Language"]:
        mm = re.search(rf"^\s*{re.escape(key)}:\s*(.*?)\s*$", block,
                       re.M | re.S)
        if mm:
            fields[key] = re.sub(r"\s+", " ", mm.group(1)).strip()
    return fields


def fetch_volume(vol, refetch=False):
    dest = RAW_DIR / f"calcom{vol}.txt"
    url = f"https://ccel.org/ccel/calvin/calcom{vol}/cache/calcom{vol}.txt"
    if dest.exists() and not refetch:
        return dest, url, "cached"
    body = http_get(url)
    dest.write_bytes(body)
    time.sleep(SLEEP)
    return dest, url, "fetched"


def main(argv):
    refetch = "--refetch" in argv
    only = [a.split("=", 1)[1] for a in argv if a.startswith("--only=")]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_id": "calvin",
        "title": "John Calvin, Commentaries (Calvin Translation Society "
                 "translations, 1843-1855)",
        "origin": "Christian Classics Ethereal Library (CCEL)",
        "origin_note": ("45-volume English translation set hosted by CCEL; "
                        "plain-text cache files fetched directly from ccel.org."),
        "retrieved": RETRIEVAL_DATE,
        "rights": "Public domain (each volume's DC header states "
                  "'Rights: Public Domain')",
        "files": [],
    }
    vols = [v for v in sorted(VOLUMES) if not only or v in only]
    for vol in vols:
        dest, url, how = fetch_volume(vol, refetch=refetch)
        text = dest.read_text(encoding="utf-8", errors="replace")
        if "<" in text[:200000]:
            raise RuntimeError(f"{dest.name}: HTML tags present in cache txt")
        hdr = dc_header(text)
        manifest["files"].append({
            "file": dest.name,
            "volume": vol,
            "label": VOLUMES[vol],
            "url": url,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "bytes": dest.stat().st_size,
            "dc": hdr,
        })
        print(f"[calcom{vol}] {how}: {dest.stat().st_size:,} bytes | "
              f"rights={hdr.get('Rights', '?')}", flush=True)
    (RAW_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    n_pd = sum(1 for f in manifest["files"]
               if f["dc"].get("Rights") == "Public Domain")
    print(f"MANIFEST written: {len(manifest['files'])} files, "
          f"{n_pd} state Rights: Public Domain", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
