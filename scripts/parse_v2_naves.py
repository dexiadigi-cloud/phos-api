#!/usr/bin/env python3
"""Parse Nave's Topical Bible (Orville J. Nave, copyright 1896; this scan: 1897
printing) from Internet Archive OCR into the Phos staging table.

Source edition: IA item navestopicalbibl0000orvi_h3u8
  (https://archive.org/details/navestopicalbibl0000orvi_h3u8),
  file navestopicalbibl0000orvi_h3u8_djvu.txt (OCR of the 1897 printing).

Pipeline
  1. Slice the raw OCR to the topical body (AARON .. ZUZIMS).
  2. Line-level cleaning: drop page-number lines, running heads, column
     markers; fix '|' column breaks; strip leading '_' artifacts;
     drop punctuation-only lines; dehyphenate words split across lines.
  3. Candidate headers: line starting with an ALL-CAPS term (>=2 chars)
     followed by '.' or ','.  Colon-terminated headers are subtopics in this
     edition and stay inside the enclosing topic's text.  Guards:
       * cross-reference continuations ("See <TERM>.", "Called also <TERM>,",
         "See <frag>-" hyphenated wraps) rejected via XREF_TRIGGERS on the
         previous non-blank line;
       * wrapped cross-ref lists rejected when the previous non-blank line
         ends with ';'.
  4. Greedy alpha acceptance + iterative poison demotion: a header is
     accepted only if its key (letters only, uppercased) sorts >= the
     previously accepted topic.  False accepts ("poisons": ghost duplicate
     headers, subtopic headers that happen to sort in order, OCR-mangled
     keys) swallow all following topics into one giant row.  They are found
     by gap analysis: a >2500-raw-line gap after an accepted topic is
     re-parsed locally from scratch; if >=8 topics are accepted inside the
     gap, the gap's first topic was a poison and is demoted (its text merges
     back into the preceding topic).  Repeats to fixpoint.  Every demotion
     is logged in the report for human review.
  5. Slice topics between accepted headers; assemble text with paragraph
     breaks preserved.
  6. Dedupe identical topic keys, keeping the fullest text.
  7. Write data/staging/dict_naves.db rows(source_id, term, text).

Writes a sidecar JSON (naves_topics.json) with raw line ranges per topic so
the independent verifier can re-extract entries straight from the raw OCR.
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw_v2" / "naves" / "ia1897_djvu.txt"
SIDECAR = BASE / "data" / "raw_v2" / "naves" / "naves_topics.json"
STAGING = BASE / "data" / "staging" / "dict_naves.db"
REPORT = BASE / "data" / "raw_v2" / "naves" / "parse_report.json"

BODY_START = 419      # 1-based raw line: 'AARON. Lineage of, ...'
BODY_END = 255246     # 1-based raw line: 'ZUZIMS. See ZaAMzuMMIMS.' (inclusive)

GAP_LINES = 2500      # gap size that triggers poison investigation
GAP_MIN_TOPICS = 8    # local accepts inside a gap needed to demote
MAX_ITERS = 300

PAGE_NUM = re.compile(r"^\d[\d, ]*$")
RUN_HEAD = re.compile(r"^[A-Z][A-Z0-9 '’&/,;+\-]*\.—")
COL_MARK = re.compile(r"^[A-Z] [0-9]+$")
HEADER = re.compile(r"^([A-Z][A-Z0-9 '’&/\-]+?)\s*([.,])")
PSALMS_SUB = re.compile(r"^PSALMS\s*\.?—")
NOT_TOPIC = re.compile(r"^(PSALM \d+|TO THE CHIEF MUSICIAN)\b")
XREF_TRIGGERS = [
    re.compile(r"\b(See|see|Called also|called also|Compare|compare|"
               r"see also|See also|refer to|referred to|Called|called)\s*$"),
    re.compile(r"\bSee\s+[A-Za-z][A-Za-z’'\-]*$"),  # hyphenated "See As-"
]

# Manually curated rejections (term, raw_lineno).  Documented in VERIFY.md.
BLACKLIST = set()


def clean_line(line: str):
    """Return cleaned line, '' for blank, or None if page furniture."""
    s = line.strip()
    if not s:
        return ""
    if PAGE_NUM.match(s):
        return None
    if RUN_HEAD.match(s):
        return None
    if COL_MARK.match(s):
        return None
    if "|" in s:  # two-column break artifact
        s = re.sub(r"(\w)\|(\w)", r"\1\2", s)
        s = s.replace("|", " ")
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r"\s\w$", "", s)  # trailing single-char column artifact
        if not s:
            return None
    if s.startswith("_"):  # OCR paragraph-mark artifact
        s = s[1:].lstrip()
        if not s:
            return None
    if re.match(r"^[\s\u2014\u2013\-_*~^]+$", s):
        return None
    return s


def dehyphenate(items):
    """Join words split across lines. items: list of (raw_lineno, text).

    A line-final '-' is near-always a split word in this OCR: join with the
    next non-blank line (page breaks in the OCR insert blank lines between
    the parts, e.g. 'WIs-' / '' / 'DOM OF.') whether it starts upper- or
    lowercase.  The hyphen is kept only for verse-range splits (digit
    before '-', e.g. '1:1-' + '3.').  A line-final '—' (em dash) joins only
    onto an adjacent lowercase continuation.
    """
    consumed = set()
    out = []
    for i, (lineno, text) in enumerate(items):
        if i in consumed:
            continue
        while text.endswith("-") or text.endswith("—"):
            # find next non-blank, non-consumed line
            j = i + 1
            while j < len(items) and (j in consumed or not items[j][1]):
                j += 1
            if j >= len(items):
                break
            cont = items[j][1]
            if text.endswith("—") and not cont[0].islower():
                break
            if text.endswith("-") and not (cont[0].isalpha()
                                           or cont[0].isdigit()):
                break
            keep = (text.endswith("-") and len(text) >= 2
                    and text[-2].isdigit())
            text = (text if keep else text[:-1]) + cont.lstrip()
            consumed.add(j)
        out.append((lineno, text))
    return out


def alpha_key(term: str) -> str:
    return re.sub(r"[^A-Z]", "", term.upper())


REF_START = re.compile(r"\b(See|see|Called|called|Compare|compare)\b")


def is_ref_continuation(cleaned, ci):
    """Is the candidate at cleaned[ci] a continuation of a cross-reference
    list ('See PETER; JOHN; ...') rather than a topic header?

    Walks backward (max 8 lines, skipping blanks which are often page
    breaks): if the first meaningful line starting/continuing a ref list
    is found -> continuation.  A 'See'-line that itself ends with '.'
    already terminated its list -> not a continuation.  Any other
    '.'-final line or header-like line also terminates the walk.
    """
    j, steps = ci - 1, 0
    while j >= 0 and steps < 8:
        _, pl = cleaned[j]
        if pl == "":
            j -= 1
            steps += 1
            continue
        if REF_START.search(pl):
            return not pl.rstrip().endswith(".")
        if pl.rstrip().endswith(".") or HEADER.match(pl):
            return False
        j -= 1
        steps += 1
    return False


def is_suffix_fragment(term, prev_line):
    """OCR often duplicates a word's tail onto the next line
    ('ACCOUNTABILITY.' / 'BILITY.', 'CRIMINATION.' / 'TION.').
    If the candidate term is a strict suffix of the previous line's last
    word and at most half its length, it's such a fragment, not a topic.
    """
    words = re.findall(r"[A-Za-z']+", prev_line)
    if not words:
        return False
    last = words[-1].upper()
    t = re.sub(r"[^A-Z]", "", term.upper())
    return (len(t) >= 2 and len(t) * 2 <= len(last)
            and last.endswith(t) and t != last)


def find_candidates(cleaned):
    """All header candidates with non-alpha guards applied."""
    cands, prev_nonblank = [], ""
    for ci, (lineno, text) in enumerate(cleaned):
        if not text:
            continue
        m = HEADER.match(text)
        term = None
        if m and "—" not in text:
            term = m.group(1).strip()
        elif PSALMS_SUB.match(text):
            # 'PSALMS.—<subtopic>.' : the PSALMS entry's subsection headers;
            # the first one opens the PSALMS topic (its bare 'PSALMS.' header
            # only appears later in the OCR at line 190704).
            term = "PSALMS"
        if term and not NOT_TOPIC.match(term):
            blocked = (
                (lineno, term) in BLACKLIST
                or is_ref_continuation(cleaned, ci)
                or is_suffix_fragment(term, prev_nonblank)
                or any(t.search(prev_nonblank) for t in XREF_TRIGGERS)
                or prev_nonblank.rstrip().endswith(";")
            )
            if not blocked:
                cands.append({"lineno": lineno, "term": term,
                              "key": alpha_key(term), "ci": ci})
        prev_nonblank = text
    return cands


def lnds(cands):
    """Longest non-decreasing subsequence of candidates (in text order,
    ordered by alpha key).  True main topics appear in the text in
    alphabetical order, so they form a very long non-decreasing chain;
    OCR fragments (cross-ref continuations, word tails, small-caps
    mid-sentence phrases) have effectively random keys and are skipped.
    O(n log n) via patience sorting with predecessor tracking.
    Returns the subsequence (list of candidate dicts)."""
    import bisect
    n = len(cands)
    if n == 0:
        return []
    # tails[i] = index of the candidate ending the best chain of length i+1
    # (with the smallest possible tail key)
    tails, prev = [], [-1] * n
    keys = [c["key"] for c in cands]
    for i in range(n):
        k = keys[i]
        # rightmost tails[j] with keys[tails[j]] <= k (non-decreasing)
        lo, hi = 0, len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if keys[tails[mid]] <= k:
                lo = mid + 1
            else:
                hi = mid
        pos = lo
        prev[i] = tails[pos - 1] if pos > 0 else -1
        if pos == len(tails):
            tails.append(i)
        else:
            tails[pos] = i
    # reconstruct
    seq, j = [], tails[-1]
    while j != -1:
        seq.append(cands[j])
        j = prev[j]
    seq.reverse()
    return seq


def greedy_accept(cands, prev_key=""):
    """Greedy alpha-monotonic acceptance. Returns accepted list."""
    accepted, pk = [], prev_key
    for c in cands:
        if c["key"] >= pk:
            accepted.append(c)
            pk = c["key"]
    return accepted


def main():
    raw_lines = RAW.read_text(encoding="utf-8").split("\n")
    body = raw_lines[BODY_START - 1 : BODY_END]

    cleaned = []
    for idx, line in enumerate(body):
        c = clean_line(line)
        if c is not None:
            cleaned.append((BODY_START + idx, c))
    cleaned = dehyphenate(cleaned)

    cands = find_candidates(cleaned)

    # Main topic chain: longest alpha-non-decreasing subsequence.
    # (Replaces the old greedy+demotion loop; LNDS skips fragments that
    # merely happen to sort in order at one point but break the chain.)
    accepted = lnds(cands)

    # slice + assemble
    entries = []
    for ti, a in enumerate(accepted):
        end_ci = accepted[ti + 1]["ci"] if ti + 1 < len(accepted) else len(cleaned)
        chunk = [t for _, t in cleaned[a["ci"]:end_ci]]
        paras, cur = [], []
        for t in chunk:
            if t == "":
                if cur:
                    paras.append(" ".join(cur)); cur = []
            else:
                cur.append(t)
        if cur:
            paras.append(" ".join(cur))
        text = "\n\n".join(p for p in paras if p)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        start_raw = cleaned[a["ci"]][0]
        end_raw = (cleaned[end_ci][0] if end_ci < len(cleaned) else BODY_END + 1)
        entries.append({"term": a["term"], "key": a["key"], "text": text,
                        "start_raw": start_raw, "end_raw": end_raw})

    # dedupe: same key in a CONTIGUOUS run = subsections of one entry
    # (e.g. 'HEAVEN.', 'HEAVEN. GOD'S DWELLING PLACE', ...) -> concatenate
    # their texts in order so no content is lost.  Same key in SEPARATE
    # runs = true duplicate -> keep the fullest run, record the merge.
    deduped, merges = {}, []
    # group indices by key, preserving chain order
    by_key = {}
    for idx, e in enumerate(entries):
        by_key.setdefault(e["key"], []).append(idx)
    for key, idxs in by_key.items():
        # split into contiguous blocks
        blocks, cur = [], [idxs[0]]
        for j in idxs[1:]:
            if j == cur[-1] + 1:
                cur.append(j)
            else:
                blocks.append(cur)
                cur = [j]
        blocks.append(cur)
        if len(blocks) == 1:
            # one logical entry: concatenate subsection slices
            es = [entries[j] for j in blocks[0]]
            text = "\n\n".join(e["text"] for e in es if e["text"])
            merged = {"term": es[0]["term"], "key": key, "text": text,
                      "start_raw": es[0]["start_raw"],
                      "end_raw": es[-1]["end_raw"]}
            if len(blocks[0]) > 1:
                merges.append(f"{es[0]['term']} x{len(blocks[0])} subsections")
            deduped[key] = merged
        else:
            # true duplicates: keep the fullest block
            best = None
            for b in blocks:
                es = [entries[j] for j in b]
                text = "\n\n".join(e["text"] for e in es if e["text"])
                if best is None or len(text) > len(best["text"]):
                    best = {"term": es[0]["term"], "key": key, "text": text,
                            "start_raw": es[0]["start_raw"],
                            "end_raw": es[-1]["end_raw"]}
            merges.append(f"{best['term']} x{len(blocks)} duplicate blocks")
            deduped[key] = best
    # preserve alpha/text order
    order = []
    seen = set()
    for e in entries:
        if e["key"] not in seen:
            seen.add(e["key"])
            order.append(e["key"])
    final = [deduped[k] for k in order if deduped[k]["text"]]

    STAGING.parent.mkdir(parents=True, exist_ok=True)
    if STAGING.exists():
        STAGING.unlink()
    con = sqlite3.connect(STAGING)
    con.execute("CREATE TABLE rows(source_id TEXT NOT NULL, term TEXT NOT NULL, "
                "text TEXT NOT NULL)")
    con.executemany(
        "INSERT INTO rows(source_id, term, text) VALUES ('naves', ?, ?)",
        [(e["term"], e["text"]) for e in final])
    con.commit()
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    n_rows = con.execute("SELECT COUNT(*) FROM rows").fetchone()[0]
    n_distinct = con.execute("SELECT COUNT(DISTINCT term) FROM rows").fetchone()[0]
    con.close()

    with open(SIDECAR, "w", encoding="utf-8") as f:
        json.dump([{"term": e["term"], "start_raw": e["start_raw"],
                    "end_raw": e["end_raw"]} for e in final], f)

    # longest topics for human review (catches residual giant-row poisons)
    longest = sorted(((len(e["text"]), e["term"]) for e in final), reverse=True)[:15]

    report = {
        "raw_file": str(RAW),
        "body_lines": f"{BODY_START}..{BODY_END}",
        "candidates": len(cands),
        "topics_accepted": len(accepted),
        "topics_after_dedupe": len(final),
        "duplicate_merges": len(merges),
        "merged_terms": sorted(set(merges)),
        "staging_rows": n_rows,
        "distinct_terms": n_distinct,
        "integrity_check": integrity,
        "first_topic": final[0]["term"] if final else None,
        "last_topic": final[-1]["term"] if final else None,
        "longest_topics": [{"term": t, "chars": n} for n, t in longest],
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
