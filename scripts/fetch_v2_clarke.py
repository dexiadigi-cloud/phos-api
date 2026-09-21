#!/usr/bin/env python3
"""Fetch raw HelloAO Adam Clarke commentary JSON (source_id=clarke).

One raw file per book at data/raw_v2/clarke/<USFM>.json:
  {"book": <books.json entry>, "chapters": {<num>: <raw chapter JSON>}}
Writes data/raw_v2/clarke/MANIFEST.json (URL template, retrieval date,
per-file sha256, commentary-level license metadata).

Stdlib only. Polite: 0.15s between chapter requests, retries. Skips books
whose raw file already exists unless --refetch.
"""
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://bible.helloao.org"
RAW_ROOT = Path(__file__).resolve().parents[1] / "data" / "raw_v2"
SOURCE_ID = "clarke"
HELLOAO_ID = "adam-clarke"
TITLE = "Adam Clarke, Commentary on the Whole Bible"
RETRIEVAL_DATE = "2026-09-20"


def http_get_json(url, tries=5):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "PhosDexiaBot/1.0 (research staging)"})
            with urllib.request.urlopen(req, timeout=45) as r:
                if r.status == 200:
                    return json.loads(r.read().decode("utf-8"))
                if r.status == 404:
                    return None
                last = f"HTTP {r.status}"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = repr(e)
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep(2 * (k + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url} ({last})")


def main(argv):
    refetch = "--refetch" in argv
    out_dir = RAW_ROOT / SOURCE_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    books_url = f"{BASE}/api/c/{HELLOAO_ID}/books.json"
    print(f"[{SOURCE_ID}] books index: {books_url}", flush=True)
    index = http_get_json(books_url)
    comm = index["commentary"]
    manifest = {
        "source_id": SOURCE_ID,
        "title": TITLE,
        "helloao_commentary_id": HELLOAO_ID,
        "source_url_template": f"{BASE}/api/c/{HELLOAO_ID}/{{BOOK}}/{{CHAPTER}}.json",
        "books_index_url": books_url,
        "retrieved": RETRIEVAL_DATE,
        "license": {
            "licenseUrl": comm.get("licenseUrl"),
            "licenseNotes": comm.get("licenseNotes"),
            "licenseNotice": comm.get("licenseNotice"),
            "sha256": comm.get("sha256"),
        },
        "files": [],
    }
    books = index["books"]
    print(f"[{SOURCE_ID}] {len(books)} books", flush=True)
    for b in books:
        usfm = b["id"]
        nch = b["numberOfChapters"]
        dest = out_dir / f"{usfm}.json"
        if dest.exists() and not refetch:
            print(f"[{SOURCE_ID}] {usfm}: exists, skipping", flush=True)
        else:
            chapters = {}
            for ch in range(1, nch + 1):
                url = f"{BASE}/api/c/{HELLOAO_ID}/{usfm}/{ch}.json"
                data = http_get_json(url)
                if data is None:
                    print(f"[{SOURCE_ID}] {usfm} ch{ch}: 404 MISSING", flush=True)
                    continue
                chapters[str(ch)] = data
                time.sleep(0.15)
            payload = {"book": b, "chapters": chapters}
            dest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"[{SOURCE_ID}] {usfm}: {len(chapters)}/{nch} chapters saved", flush=True)
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest["files"].append(
            {"file": dest.name, "sha256": sha, "bytes": dest.stat().st_size})
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[{SOURCE_ID}] MANIFEST written ({len(manifest['files'])} files)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
