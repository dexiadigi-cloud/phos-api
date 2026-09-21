#!/usr/bin/env python3
"""Fetch raw HelloAO commentary JSON for the V2 staging pipeline.

Downloads every chapter of each configured HelloAO commentary and stores
ONE raw file per book at data/raw_v2/<source_id>/<USFM>.json, where each
file is {"book": <books.json entry>, "chapters": {num: <raw chapter JSON>}}.
Writes data/raw_v2/<source_id>/MANIFEST.json with URL template, retrieval
date, per-file sha256, and the commentary-level license metadata.

Only stdlib. Polite: sequential per commentary with small delay + retries.
Re-running skips books whose raw file already exists (use --refetch to redo).
"""
import hashlib
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

BASE = "https://bible.helloao.org"
RAW_ROOT = Path(__file__).resolve().parents[1] / "data" / "raw_v2"

SOURCES = {
    # source_id: (helloao commentary id, title)
    "matthew_henry": ("matthew-henry", "Matthew Henry's Complete Commentary on the Whole Bible"),
    "jfb": ("jamieson-fausset-brown", "Jamieson-Fausset-Brown Bible Commentary"),
    "gill": ("john-gill", "John Gill's Exposition of the Entire Bible"),
}

RETRIEVAL_DATE = "2026-09-20"


def http_get_json(url, tries=5):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PhosDexiaBot/1.0 (research staging)"})
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status == 200:
                    return json.loads(r.read().decode("utf-8"))
                if r.status == 404:
                    return None
                last = f"HTTP {r.status}"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # not found: do not retry
            last = repr(e)
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep(2 * (k + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url} ({last})")


def fetch_source(source_id, helloao_id, refetch=False):
    out_dir = RAW_ROOT / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    books_url = f"{BASE}/api/c/{helloao_id}/books.json"
    print(f"[{source_id}] books index: {books_url}", flush=True)
    index = http_get_json(books_url)
    comm = index["commentary"]
    lic = {
        "licenseUrl": comm.get("licenseUrl"),
        "licenseNotes": comm.get("licenseNotes"),
        "licenseNotice": comm.get("licenseNotice"),
        "sha256": comm.get("sha256"),
    }
    manifest = {
        "source_id": source_id,
        "title": SOURCES[source_id][1],
        "helloao_commentary_id": helloao_id,
        "source_url_template": f"{BASE}/api/c/{helloao_id}/{{BOOK}}/{{CHAPTER}}.json",
        "books_index_url": books_url,
        "retrieved": RETRIEVAL_DATE,
        "license": lic,
        "files": [],
    }
    books = index["books"]
    print(f"[{source_id}] {len(books)} books", flush=True)
    for b in books:
        usfm = b["id"]
        nch = b["numberOfChapters"]
        dest = out_dir / f"{usfm}.json"
        if dest.exists() and not refetch:
            print(f"[{source_id}] {usfm}: exists, skipping", flush=True)
        else:
            chapters = {}
            for ch in range(1, nch + 1):
                url = f"{BASE}/api/c/{helloao_id}/{usfm}/{ch}.json"
                data = http_get_json(url)
                if data is None:
                    print(f"[{source_id}] {usfm} ch{ch}: 404 MISSING", flush=True)
                    continue
                chapters[str(ch)] = data
                time.sleep(0.15)
            payload = {"book": b, "chapters": chapters}
            dest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"[{source_id}] {usfm}: {len(chapters)}/{nch} chapters saved", flush=True)
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest["files"].append({
            "file": dest.name, "sha256": sha,
            "bytes": dest.stat().st_size,
        })
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[{source_id}] MANIFEST written ({len(manifest['files'])} files)", flush=True)


def main(argv):
    refetch = "--refetch" in argv
    only = [a.split("=", 1)[1] for a in argv if a.startswith("--only=")]
    for source_id, (helloao_id, _title) in SOURCES.items():
        if only and source_id not in only:
            continue
        fetch_source(source_id, helloao_id, refetch=refetch)


if __name__ == "__main__":
    main(sys.argv[1:])
