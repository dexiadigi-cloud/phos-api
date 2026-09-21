#!/usr/bin/env python3
"""Repair Strong's lexicon ingest (2026-09-20).

Sequence-aware re-parse of the OCR'd Strong's dictionaries.
Entry numbers suffer OCR digit confusion (3<->8, S<->5/8, $/#<->2, ...);
entries run in strict numeric sequence, so a corrupted heading number is
correctable when a single OCR-confusion substitution yields the expected number.

Usage: python3 repair_strongs.py [--dry-run]
Writes: data/study.db (strongs table replaced in one transaction),
        verification/v2/strongs-repair-manifest.json,
        verification/v2/strongs-repair-log.md
"""
import re, sqlite3, json, sys
from pathlib import Path

BASE = Path.home() / "workspace" / "scripture-desk"
RAW = BASE / "data" / "raw_v2" / "strongs"
DB = BASE / "data" / "study.db"
MANIFEST = BASE / "verification" / "v2" / "strongs-repair-manifest.json"
LOG = BASE / "verification" / "v2" / "strongs-repair-log.md"

# OCR confusion pairs observed in these files. Acceptance always requires the
# corrected token to equal the expected sequence number, so the map can be
# generous: ambiguity is resolved by position.
CONF = {
    '0': ('O', 'o', '9'), 'O': ('0',), 'o': ('0',), '9': ('0', '8'),
    '1': ('l', 'I', 'i', '7'), 'l': ('1',), 'I': ('1',), 'i': ('1',),
    '2': ('3', '5', 'S', 's', '$', '#', '?'),
    '7': ('1',), 'Z': ('1',),
    '3': ('2', '5', '8', 'S', 's', 'B'),
    '5': ('2', '3', '6', '8', 'S', 's'),
    '6': ('b', '5'), 'b': ('6',),
    '8': ('3', '5', '9', 'S', 's', 'B'), 'B': ('8', '3'),
    'S': ('2', '3', '5', '8'), 's': ('2', '3', '5', '8'),
    '$': ('2', '5'), '#': ('2',),
    '4': ('^',), '^': ('4', '2'), '?': ('2',),
}
NUMCHARS = set("0123456789") | set("$#SsOoLlIibB^?")
# candidate heading: any short line-initial token ending in . or -
HEAD_RE = re.compile(r"^(\S{1,12}?)[.\-_][ \t]")
# merge split headings like "15 Jf." -> "15Jf." (digit-run, space, short frag)
MERGE_RE = re.compile(r"^(\d[\d$#SsOoLlIibB^?]*)\s+([^\d\s]\S{0,3})[.\-]")

FILES = [
    # (filename, language, prefix, max_number, known publisher gaps (start, end))
    ("StrongGreekDictionary_djvu.txt", "greek", "G", 5624, [(2717, 2717), (3203, 3302)]),
    ("StrongHebrewDictionary_djvu.txt", "hebrew", "H", 8674, []),
]


def correct_to(token, expected, max_subs=2):
    """Return (expected, n_subs) if token matches expected directly or via
    <= max_subs OCR-confusion substitutions; else None."""
    if not token or any(c not in NUMCHARS for c in token):
        return None
    if len(token) != len(expected):
        return None
    subs = 0
    for i, ch in enumerate(token):
        if ch == expected[i]:
            continue
        if expected[i] in CONF.get(ch, ()):
            subs += 1
        else:
            return None
    if subs <= max_subs:
        return (expected, subs)
    return None


def norm_tok(t):
    t = t.lstrip("._").rstrip("\"'")
    # internal dots/dashes are OCR artifacts: "11.54" -> "1154", "44-6" -> "446"
    t = t.replace(".", "").replace("-", "").replace("_", "")
    return t

def merge_split_headings(lines):
    # "15 Jf." -> "15Jf." : digit-run, space, short non-digit fragment ending in ./-
    out = []
    for ln in lines:
        m = MERGE_RE.match(ln)
        if m and re.search(r"[^\d]", m.group(2)):
            out.append(m.group(1) + m.group(2) + "." + ln[m.end():])
        else:
            out.append(ln)
    return out

def looks_like_entry_head(lines, li):
    # word-shape plausibility: short token, then headword, then transliteration
    # ending in , or . ; entry gloss ";" on the SAME line (not 2 lines down,
    # which would belong to the next entry); transliteration not a bracket note
    words = lines[li].split()
    if len(words) < 3 or len(words[0]) > 10:
        return False
    if words[2][0] in "[(":
        return False
    if not (words[2].endswith(",") or words[2].endswith(".")):
        return False
    return ";" in lines[li]


def gap_search(tok, expected, max_num, accepted, K=12):
    # (number, subs): tok's best reading as expected+d, d in 1..K, via the
    # confusion map. Excludes already-accepted numbers. Fewest subs wins;
    # ties go to the smallest d. Used when the token doesn't read as
    # expected: a clean "1151." at expected=1146 is 1151 with 1147-1150
    # missing, not a jump. (A far-away face value is only reached here, and
    # only within K, so "924." at expected=2 still jumps.)
    # Clean tokens get a wider K: a clean "2873." at expected=2851 is
    # unambiguously 2873 with a genuine 22-number gap.
    if tok.isdigit():
        K = max(K, 50)
    best = None
    for d in range(1, K + 1):
        num = expected + d
        if num > max_num or num in accepted:
            continue
        r = correct_to(tok, str(num))
        if r is not None:
            key = (r[1], d)
            if best is None or key < best[0]:
                best = (key, num)
    return (best[1], best[0][0]) if best else None


def headwords2(lines, li):
    w = lines[li].split()
    return (w[1] if len(w) > 1 else "", w[2] if len(w) > 2 else "")


def run_machine(cands, lines, start_ci, max_num, gaps, stall_limit=1000):
    entries = []   # [num, start_line, end_line, raw_token, corrected]
    events = []
    accepted = {}  # num -> entry index
    expected = 1
    ci = start_ci
    n = len(cands)
    consec_reject = 0
    logged_spurious = 0
    while ci < n:
        li, raw_tok = cands[ci]
        # normalize OCR artifacts: leading dots (".47" -> "47"), internal
        # dashes ("44-6" -> "446"), trailing quotes
        tok = norm_tok(raw_tok)
        clean = tok.isdigit()
        H = int(tok) if clean else None
        # documented publisher gaps: jump deterministically, never "correct"
        # a far-away clean heading into the gap (e.g. 3303 -> 3203)
        gap_hit = False
        for gs, ge in gaps:
            if gs <= expected <= ge + 1:
                target = ge + 1
                if target not in accepted and (correct_to(tok, str(target)) is not None
                                               or (clean and H == target)):
                    if entries:
                        entries[-1][2] = li
                    entries.append([target, li, None, raw_tok, False])
                    accepted[target] = len(entries) - 1
                    events.append(f"KNOWN-GAP {expected}..{ge} absent per source; accepted {target} raw='{tok}' line={li+1}")
                    expected = target + 1
                    consec_reject = 0; ci += 1; gap_hit = True
                    break
        if gap_hit:
            continue
        res = correct_to(tok, str(expected))
        # Prefer the expected number whenever the token reads as it (even
        # with subs): a clean "86." at expected=85 is a corrupted 85 heading,
        # not 86 with 85 missing.
        if res is not None:
            use_num, use_subs = expected, res[1]
            if use_num in accepted:
                # true dup of an accepted entry: verify by headword, else skip
                ai = accepted[use_num]
                if headwords2(lines, li) == headwords2(lines, entries[ai][1]):
                    events.append(f"DUP '{tok}' line={li+1} already have {use_num} -- skipped")
                    consec_reject += 1; ci += 1; continue
                # same number, different headword: fall through to positional logic
            else:
                if entries:
                    entries[-1][2] = li
                entries.append([use_num, li, None, raw_tok, use_subs > 0])
                accepted[use_num] = len(entries) - 1
                if use_subs:
                    events.append(f"CORRECT '{tok}' -> {use_num} ({use_subs} subs, line {li+1})")
                expected = use_num + 1
                consec_reject = 0; ci += 1; continue
        # spurious: immediate next candidate reads as E with 0-1 subs (and we
        # have no anchor for E+1). A 2-sub reading like "S6."->25 is too weak
        # to declare the current token junk.
        spurious = False
        anchor = False
        if ci + 1 < n:
            r2 = correct_to(norm_tok(cands[ci + 1][1]), str(expected))
            if r2 is not None and r2[1] <= 1:
                # but not if we have an E+1 anchor: then this is positional
                has_anchor = False
                for j in range(1, 5):
                    if ci + j >= n:
                        break
                    rj = correct_to(norm_tok(cands[ci + j][1]), str(expected + 1))
                    if rj is not None:
                        has_anchor = True
                        break
                if not has_anchor:
                    spurious = True
        if not spurious:
            # anchor: first of next 4 that reads as E+1
            for j in range(1, 5):
                if ci + j >= n:
                    break
                rj = correct_to(norm_tok(cands[ci + j][1]), str(expected + 1))
                if rj is not None:
                    anchor = True
                    break
        if spurious:
            events.append(f"SPURIOUS '{tok}' line={li+1} expected={expected} (later heading fits) -- skipped")
            consec_reject += 1; ci += 1; continue
        dup_headword = False
        if clean and H in accepted:
            ai = accepted[H]
            dup_headword = (headwords2(lines, li) == headwords2(lines, entries[ai][1]))
        if anchor and correct_to(tok, str(expected + 1)) is None \
                and not dup_headword \
                and looks_like_entry_head(lines, li):
            # positional: mangled heading with an E+1 anchor ahead. Guards:
            # - it must not read as E+1 (that would steal E+1's heading)
            # - a clean token already accepted is a dup, not a positional
            # - it must look like a real dictionary entry heading
            # The old length guard is gone: correct_to(tok,E+1) is None already
            # blocks a clean true-E+1 heading, and the dup check blocks dups.
            if clean and H in accepted:
                events.append(f"DUP '{tok}' line={li+1} already have {H} -- skipped")
                consec_reject += 1; ci += 1; continue
            if entries:
                entries[-1][2] = li
            entries.append([expected, li, None, raw_tok, True])
            accepted[expected] = len(entries) - 1
            events.append(f"POSITIONAL '{tok}' -> {expected} (line {li+1})")
            expected = expected + 1
            consec_reject = 0; ci += 1; continue
        # gap-fit: no anchor, but the token reads as expected+d (d<=12).
        # A clean "1151." at expected=1146 is 1151 with 1147-1150 missing.
        gs = gap_search(tok, expected, max_num, accepted)
        if gs is not None:
            use_num, use_subs = gs
            if entries:
                entries[-1][2] = li
            entries.append([use_num, li, None, raw_tok, True])
            accepted[use_num] = len(entries) - 1
            events.append(f"GAPFIT expected {expected}..{use_num-1} missing; '{tok}' -> {use_num} ({use_subs} subs, line {li+1})")
            expected = use_num + 1
            consec_reject = 0; ci += 1; continue
        if H is not None and (H < expected or dup_headword or H in accepted):
            events.append(f"DUP/ANOMALY '{tok}' line={li+1} expected={expected} -- skipped")
        elif H is not None and expected < H <= max_num:
            # genuine gap: accept H (a clean H here didn't read as expected or
            # expected+1..50 above, so it's a real jump). But it must look
            # like a real entry: a bare "3861." with no body is spurious.
            if not looks_like_entry_head(lines, li):
                events.append(f"SPURIOUS '{tok}' line={li+1} no entry body -- skipped")
                consec_reject += 1
            else:
                if entries:
                    entries[-1][2] = li
                entries.append([H, li, None, raw_tok, False])
                accepted[H] = len(entries) - 1
                events.append(f"JUMP expected={expected} accepted={H} raw='{tok}' line={li+1}")
                expected = H + 1
                consec_reject = 0
        else:
            if logged_spurious < 8:
                events.append(f"SPURIOUS '{tok}' line={li+1} -- skipped")
                logged_spurious += 1
            consec_reject += 1
        ci += 1
        if consec_reject > stall_limit:
            events.append(f"STALL after {stall_limit} consecutive rejects at line {li+1}")
            break
    if entries and entries[-1][2] is None:
        entries[-1][2] = len(lines)
    return entries, events


def parse_fields(raw_text):
    text = " ".join(raw_text.split())
    m = re.match(r"^\S+?[.\-]\s+", text)
    rest = text[m.end():] if m else text
    headword = translit = pron = etym = glosses = None
    parts = rest.split(None, 2)
    if len(parts) >= 1:
        headword = parts[0][:80]
    if len(parts) >= 2:
        translit = parts[1].rstrip(",")[:80] or None
    rem = parts[2] if len(parts) > 2 else ""
    rem = rem.lstrip(", ")
    if ";" in rem:
        pron, tail = rem.split(";", 1)
        pron = pron.strip()[:80] or None
    else:
        tail = rem
    if "—" in tail:
        etym, glosses = tail.split("—", 1)
    elif " -- " in tail:
        etym, glosses = tail.split(" -- ", 1)
    else:
        etym = tail
    etym = (etym or "").strip() or None
    glosses = (glosses or "").strip() or None
    if etym and len(etym) > 2000:
        etym = etym[:2000]
    if glosses and len(glosses) > 2000:
        glosses = glosses[:2000]
    return headword, translit, pron, etym, glosses, text


def parse_one(fname, lang, prefix, max_num, gaps):
    lines = (RAW / fname).read_text(encoding="utf-8", errors="replace").splitlines()
    lines = merge_split_headings(lines)   # "15 Jf." -> "15Jf."
    cands = []
    for i, ln in enumerate(lines):
        m = HEAD_RE.match(ln)
        if m:
            cands.append((i, m.group(1)))
    # candidate starts: token corrects to "1" and chunk looks like a dictionary entry
    starts = []
    for ci, (li, tok) in enumerate(cands):
        if correct_to(tok, "1") is None:
            continue
        if ";" in " ".join(lines[li:li + 3]):
            starts.append(ci)
    if not starts:
        raise RuntimeError(f"{fname}: no entry-1 start found")
    best = None
    for ci in starts:
        entries, _ = run_machine(cands, lines, ci, max_num, gaps)
        key = (len(entries), cands[ci][0])
        if best is None or key > best[0]:
            best = (key, ci)
    entries, events = run_machine(cands, lines, best[1], max_num, gaps)
    return lines, entries, events, cands[best[1]][0]


def main():
    dry = "--dry-run" in sys.argv
    all_rows = []
    manifest = {}
    log_sections = []
    for fname, lang, prefix, max_num, gaps in FILES:
        lines, entries, events, start_line = parse_one(fname, lang, prefix, max_num, gaps)
        corrections = sum(1 for e in entries if e[4])
        log_sections.append(f"## {lang} ({fname})\n")
        log_sections.append(f"- entries parsed: {len(entries)} / {max_num} "
                            f"({100.0 * len(entries) / max_num:.1f}%)\n")
        log_sections.append(f"- single-confusion corrections: {corrections}\n")
        log_sections.append(f"- parse start: line {start_line + 1}\n")
        log_sections.append(f"- entry-number range: {entries[0][0]}..{entries[-1][0]}\n\n")
        man = {}
        for num, sline, eline, raw_tok, corrected in entries:
            raw_text = "\n".join(lines[sline:eline])
            hw, tr, pr, et, gl, text = parse_fields(raw_text)
            all_rows.append((f"{prefix}{num}", lang, num, hw, tr, pr, et, gl, text))
            man[str(num)] = {"raw_token": raw_tok, "line": sline + 1,
                             "corrected": corrected}
        manifest[lang] = man
        log_sections.append("### events\n\n```\n" + "\n".join(events) + "\n```\n\n")

    if dry:
        print(f"DRY RUN: {len(all_rows)} rows parsed, DB untouched")
        return

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM strongs")
    cur.executemany(
        "INSERT INTO strongs (strongs_number, language, num, headword_original,"
        " transliteration, pronunciation, etymology, kjv_glosses, entry_text)"
        " VALUES (?,?,?,?,?,?,?,?,?)", all_rows)
    # refresh source row counts if present
    cur.execute("SELECT COUNT(*) FROM sources WHERE source_id='strongs'")
    if cur.fetchone()[0]:
        cur.execute("UPDATE sources SET notes = ? WHERE source_id='strongs'",
                    (f"Strong's Greek+Hebrew dictionaries (1890), CC0 IA item; "
                     f"{sum(1 for r in all_rows if r[1]=='greek')} Greek + "
                     f"{sum(1 for r in all_rows if r[1]=='hebrew')} Hebrew entries; "
                     f"repaired parse 2026-09-20",))
    con.commit()
    greek_n = sum(1 for r in all_rows if r[1] == "greek")
    heb_n = sum(1 for r in all_rows if r[1] == "hebrew")
    oor = cur.execute("SELECT COUNT(*) FROM strongs WHERE (language='greek' AND (num<1 OR num>5624))"
                      " OR (language='hebrew' AND (num<1 OR num>8674))").fetchone()[0]
    dups = cur.execute("SELECT COUNT(*) FROM (SELECT strongs_number FROM strongs"
                       " GROUP BY strongs_number HAVING COUNT(*)>1)").fetchone()[0]
    integ = cur.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()

    MANIFEST.write_text(json.dumps({"langs": manifest,
                                    "stats": {"greek": greek_n, "hebrew": heb_n}},
                                   ensure_ascii=False))
    LOG.write_text("# Strong's repair parse log (2026-09-20)\n\n"
                   "Sequence-aware re-parse: expected-number tracking with OCR-confusion\n"
                   "correction (up to 2 substitutions; 0<->O/o, 1<->l/I/i, 2<->5/S/s/$/#,\n"
                   "3<->8/S/s/B, 5<->2/S/s, 6<->b, 8<->3/S/s/B, S/s<->2/3/5/8, $/#->2/5),\n"
                   "plus positional assignment for mangled headings sandwiched between\n"
                   "good anchors. Greek Nos. 2717 and 3203-3302 have no entries in the\n"
                   "source (dropped by the publisher; see end-of-file note), so the\n"
                   "achievable Greek maximum is 5523.\n\n" + "".join(log_sections))
    print(f"greek={greek_n} hebrew={heb_n} out_of_range={oor} dups={dups} integrity={integ}")
    print(f"G3056 present: {any(r[0]=='G3056' for r in all_rows)}")


if __name__ == "__main__":
    main()
