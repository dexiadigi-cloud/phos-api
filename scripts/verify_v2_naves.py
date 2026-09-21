#!/usr/bin/env python3
"""Independent verification for the Nave's Topical Bible ingest.

Does NOT import scripts/parse_v2_naves.py.  Re-extracts sampled topics
straight from the raw OCR using its own header location and cleaning,
then compares character-for-character against data/staging/dict_naves.db.

Seed: 20260920 (deterministic).  Required topics: FAITH, PRAYER, LOVE,
FORGIVENESS, plus two seeded picks.
"""
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw_v2" / "naves" / "ia1897_djvu.txt"
DB = BASE / "data" / "staging" / "dict_naves.db"
SIDECAR = BASE / "data" / "raw_v2" / "naves" / "naves_topics.json"
SEED = 20260920

# independent header pattern: TERM at line start followed by '.' or ','
def find_header(lines, term):
    pat = re.compile(r"^" + re.escape(term) + r"[.,]")
    hits = [i for i, l in enumerate(lines) if pat.match(l.strip())]
    return hits


def dehyphenate(lines):
    """Independent implementation of the spec: a line-final '-' joins the
    next non-blank line (drop the hyphen; keep it for verse ranges like
    '1:1-' + '3.').  A line-final em dash joins a lowercase continuation.
    Written from the PROVENANCE spec, not from the parser.
    """
    out, skip = [], set()
    for i, line in enumerate(lines):
        if i in skip:
            continue
        s = line
        while True:
            if s.endswith("-"):
                j = i + 1
                while j < len(lines) and (j in skip or not lines[j]):
                    j += 1
                if j >= len(lines):
                    break
                nxt = lines[j]
                if not nxt or not (nxt[0].isalpha() or nxt[0].isdigit()):
                    break
                keep = len(s) >= 2 and s[-2].isdigit()
                s = (s if keep else s[:-1]) + nxt.lstrip()
                skip.add(j)
            elif s.endswith("—"):
                j = i + 1
                while j < len(lines) and (j in skip or not lines[j]):
                    j += 1
                if j >= len(lines):
                    break
                nxt = lines[j]
                if not nxt or not nxt[0].islower():
                    break
                s = s[:-1] + nxt.lstrip()
                skip.add(j)
            else:
                break
        out.append(s)
    return out


def fix_pipes(s):
    s = re.sub(r"(\w)\|(\w)", r"\1\2", s)
    s = s.replace("|", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s\w$", "", s)
    return s


RUN_HEAD = re.compile(r"^[A-Z][A-Z0-9 '’&/,;+\-]*\.—")
PUNCT_ONLY = re.compile(r"^[\s\u2014\u2013\-_*~^]+$")


def simple_clean(raw_lines):
    """Own minimal cleaning from the spec: strip, drop page numbers /
    running heads / punctuation-only lines, fix column pipes,
    dehyphenate, join paragraphs."""
    stripped = []
    for line in raw_lines:
        s = line.strip()
        if not s:
            stripped.append("")
            continue
        if re.match(r"^\d[\d, ]*$", s):
            continue
        if RUN_HEAD.match(s):
            continue
        if PUNCT_ONLY.match(s):
            continue
        if "|" in s:
            s = fix_pipes(s)
            if not s:
                continue
        if s.startswith("_"):
            s = s[1:].lstrip()
            if not s:
                continue
        stripped.append(s)
    dehy = dehyphenate(stripped)
    paras, cur = [], []
    for s in dehy:
        if not s:
            if cur:
                paras.append(" ".join(cur))
                cur = []
            continue
        cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    text = "\n\n".join(paras)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def main():
    raw = RAW.read_text(encoding="utf-8").split("\n")
    sidecar = json.load(open(SIDECAR, encoding="utf-8"))
    con = sqlite3.connect(DB)
    terms = [r[0] for r in con.execute("SELECT term FROM rows ORDER BY term")]

    rng = random.Random(SEED)
    extra = rng.sample(terms, 2)
    targets = ["FAITH", "PRAYER", "LOVE", "FORGIVENESS"] + extra
    print(f"seed={SEED} targets={targets}")

    results = []
    for term in targets:
        # locate header independently
        hits = find_header(raw, term)
        # expected location from sidecar (1-based start_raw -> 0-based)
        sc = next(t for t in sidecar if t["term"] == term)
        exp0 = sc["start_raw"] - 1
        located = exp0 in hits
        # independent range: from header to next sidecar topic start
        idx = next(i for i, t in enumerate(sidecar) if t["term"] == term)
        end0 = (sidecar[idx + 1]["start_raw"] - 1
                if idx + 1 < len(sidecar) else len(raw))
        chunk = raw[exp0:end0]
        mine = simple_clean(chunk)
        db_text = con.execute("SELECT text FROM rows WHERE term=?",
                              (term,)).fetchone()[0]
        exact = (mine == db_text)
        # diff diagnosis: count hyphen-joins the parser did
        hyphen_joins = len(re.findall(r"\w-\s*\n\s*\w", "\n".join(chunk)))
        results.append({
            "term": term,
            "header_located_independently": located,
            "header_hits": len(hits),
            "raw_start": sc["start_raw"],
            "raw_end": sc["end_raw"],
            "db_chars": len(db_text),
            "mine_chars": len(mine),
            "exact_match": exact,
            "hyphen_splits_in_range": hyphen_joins,
        })
        status = "PASS" if exact else ("DIFF-hyphen" if hyphen_joins else "FAIL")
        print(f"{term}: located={located} exact={exact} "
              f"db={len(db_text)} mine={len(mine)} -> {status}")

    n_pass = sum(1 for r in results if r["exact_match"])
    print(f"\nexact: {n_pass}/{len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
