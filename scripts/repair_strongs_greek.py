#!/usr/bin/env python3
"""Simple Strong's repair: sequential greedy with confusion map.
For each candidate heading in file order, accept the best reading in
[expected, expected+50] via the confusion map (<=2 subs). No positional,
no spurious, no anchor. Conservative and stable.
"""
import re, sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw_v2" / "strongs"

# Well-attested OCR confusions (conservative)
CONF = {
    '0': ('9', '6', '8'),
    '1': ('l', 'I', 'i', '7'),
    'l': ('1',), 'I': ('1',), 'i': ('1',),
    '2': ('3', '5', 'S', 's', '$', '#', '?', '8'),
    '3': ('5', '8', 'B', 's', '2', '$'),
    '4': ('^',),
    '5': ('3', 'S', 's', '6', '2'),
    '6': ('5', 'b', '8'),
    '7': ('1',),
    '8': ('3', '5', '9', 'S', 's', 'B', '2'),
    '9': ('0', '8', '6'),
    'S': ('2', '3', '5', '8', '1'),
    's': ('5', '8'),
    'B': ('8', '3', '5'),
    '$': ('5', 'S', 's'),
    'Z': ('1',),
    'O': ('0', '9'),
    'o': ('0',),
}

def correct_to(tok, target):
    if not tok or len(tok) != len(target):
        return None
    subs = 0
    for a, b in zip(tok, target):
        if a == b:
            continue
        if b in CONF.get(a, ()):
            subs += 1
            if subs > 2:
                return None
        else:
            return None
    return (target, subs)

def norm_tok(t):
    t = t.lstrip("._").rstrip("\"'")
    t = t.replace(".", "").replace("-", "").replace("_", "")
    return t

HEAD_RE = re.compile(r"^(\S{1,12}?)[.\-_][ \t]")

def merge_split_headings(lines):
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^(\S{1,6}?)\s+([A-Za-z][\S]{0,6})[.\-]\s*$", ln)
        if m and i + 1 < len(lines):
            tok, frag = m.group(1), m.group(2)
            if tok and frag and all(c in "0123456789S$#?IlisSBZzOo" for c in tok):
                out.append(f"{tok}{frag}.")
                i += 2
                continue
        out.append(ln)
        i += 1
    return out

FILES = [
    ("StrongGreekDictionary_djvu.txt", "greek", "G", 5624, [(2717, 2717), (3203, 3302)]),
    ("StrongHebrewDictionary_djvu.txt", "hebrew", "H", 8674, []),
]

def parse_one(fname, lang, prefix, max_num, gaps):
    lines = merge_split_headings((RAW / fname).read_text(encoding="utf-8", errors="replace").splitlines())
    cands = []
    for i, ln in enumerate(lines):
        m = HEAD_RE.match(ln)
        if m:
            cands.append((i, m.group(1)))
    # find start: token corrects to "1" and chunk looks like entry
    starts = []
    for ci, (li, tok) in enumerate(cands):
        if correct_to(norm_tok(tok), "1") is None:
            continue
        if ";" in " ".join(lines[li:li + 3]):
            starts.append(ci)
    if not starts:
        raise RuntimeError(f"{fname}: no start")
    # pick start with most entries (greedy)
    best = None
    for ci in starts:
        entries = run_simple(cands, lines, ci, max_num, gaps)
        key = len(entries)
        if best is None or key > best[0]:
            best = (key, ci)
    entries = run_simple(cands, lines, best[1], max_num, gaps)
    return lines, entries, cands[best[1]][0]

def run_simple(cands, lines, start_ci, max_num, gaps):
    entries = []  # [num, line_idx, end_line, raw_tok, corrected]
    accepted = {}
    expected = 1
    ci = start_ci
    n = len(cands)
    while ci < n and expected <= max_num:
        li, raw_tok = cands[ci]
        tok = norm_tok(raw_tok)
        # known publisher gaps
        gap_hit = False
        for gs, ge in gaps:
            if gs <= expected <= ge + 1:
                target = ge + 1
                if target not in accepted and correct_to(tok, str(target)) is not None:
                    if entries:
                        entries[-1][2] = li
                    entries.append([target, li, None, raw_tok, True])
                    accepted[target] = len(entries) - 1
                    expected = target + 1
                    ci += 1
                    gap_hit = True
                    break
        if gap_hit:
            continue
        # find best reading in [expected, expected+50]
        # Prefer CLOSEST number (smallest d); tie-break by fewest subs.
        # A clean "280." at expected=230 is 230 (1 sub), not 280 (0 subs).
        # Accept only if: d <= 5 (near, allow subs), OR d <= 15 with 0 subs
        # (exact far heading, e.g. "1151." at 1146). Otherwise skip: a far
        # non-exact fit like "533."->552 at expected=542 is likely a printer
        # error/out-of-order, not a valid heading.
        best = None
        for d in range(0, 51):
            num = expected + d
            if num > max_num or num in accepted:
                continue
            r = correct_to(tok, str(num))
            if r is not None:
                key = (d, r[1])
                if best is None or key < best[0]:
                    best = (key, num)
        if best is not None:
            d, subs = best[0]
            if d <= 5 or (d <= 15 and subs == 0):
                use_num = best[1]
                use_subs = subs
                if entries:
                    entries[-1][2] = li
                entries.append([use_num, li, None, raw_tok, use_subs > 0 or use_num != expected])
                accepted[use_num] = len(entries) - 1
                expected = use_num + 1
                ci += 1
                continue
        # Strict positional (Greek only): no fit, but next is exact E+1.
        # Tok must be 2-4 chars, not a common word. The exact anchor is the
        # strong signal; the tok is allowed to be heavily mangled.
        if ci + 1 < n:
            _, raw2 = cands[ci + 1]
            r2 = correct_to(norm_tok(raw2), str(expected + 1))
            if r2 is not None and r2[1] == 0:  # exact anchor
                if 2 <= len(tok) <= 4:
                    # skip common English words
                    if tok.lower() not in ('is', 'as', 'at', 'to', 'of', 'in', 'on', 'up', 'us', 'we', 'he', 'she', 'it', 'the', 'and', 'for'):
                        if entries:
                            entries[-1][2] = li
                        entries.append([expected, li, None, raw_tok, True])
                        accepted[expected] = len(entries) - 1
                        expected = expected + 1
                        ci += 1
                        continue
        # else: skip (no fit)
        ci += 1
    return entries

def main():
    for fname, lang, prefix, max_num, gaps in FILES:
        lines, entries, start_tok = parse_one(fname, lang, prefix, max_num, gaps)
        nums = set(e[0] for e in entries)
        missing = [n for n in range(1, max_num + 1) if n not in nums]
        corr = sum(1 for e in entries if e[4])
        print(f"{lang}: entries={len(entries)}/{max_num} ({100*len(entries)/max_num:.1f}%) corrections={corr} missing={len(missing)}")

if __name__ == "__main__":
    main()
