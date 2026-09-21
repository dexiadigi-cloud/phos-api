#!/usr/bin/env python3
"""Ingest Strong's 1890 Greek/Hebrew dictionaries (IA djvu.txt OCR) into study.db.

Source: IA item 'StrongsGreekAndHebrewDictionaries1890' (CC0 1.0 item license;
underlying 1890 dictionaries public domain regardless).
  data/raw_v2/strongs/StrongGreekDictionary_djvu.txt  (G1-G5624)
  data/raw_v2/strongs/StrongHebrewDictionary_djvu.txt (H1-H8674)

Re-runnable: drops and recreates the `strongs` table and replaces the
'strongs' row in `sources`. Never touches scripture.db.

Parsing method: entries are sequential numbered headings "<n>. <headword>
<transliteration>, <pronunciation>; <etymology> ... -- <KJV glosses>."
OCR corrupts some numbers ("S." for 3, "IS." for 12, "'2." for 5622,
"5624-" for 5624) and most Greek/Hebrew headwords. An expected-counter
walks the headings: clean digits equal to expected are accepted, digit
jumps within bounds are logged as genuine gaps (the source itself dropped
G2717 and G3203-G3302 per its closing NOTE), non-digit tokens whose
remainder looks like an entry ("<...> <translit>, <pron>;") are accepted
as the expected number with a logged normalization. Anything else is a
continuation line of the current entry.

Headword policy: `headword_original` is stored ONLY when it is genuine
Greek/Hebrew script; OCR mojibake ("Aapuv", "Ka$>>") is stored as NULL.
"""
import re, json, sqlite3, hashlib, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, 'data', 'raw_v2', 'strongs')
DB = os.path.join(BASE, 'data', 'study.db')
LOG_PATH = os.path.join(RAW, 'parse_log.json')

FILES = {
    'greek': ('StrongGreekDictionary_djvu.txt', 5624, 'G'),
    'hebrew': ('StrongHebrewDictionary_djvu.txt', 8674, 'H'),
}

HEAD_RE = re.compile(r'^([^\s.]{1,8})[.\-–]\s+(.*)$')
CORRUPT_DOT_RE = re.compile(r'^(\d{1,4})\.(\d{1,4})\.\s+(.*)$')  # "1.6."->16, "55.25."->5525


def digit_diffs(a, b):
    """Number of differing digit positions, or None if different lengths."""
    if len(a) != len(b):
        return None
    return sum(1 for x, y in zip(a, b) if x != y)


def dropped_digit(tok, expected):
    """True if tok looks like expected with one digit dropped ('0.' for 90)."""
    es = str(expected)
    return len(tok) == len(es) - 1 and (tok == es[1:] or tok == es[:-1])
FIELD_RE = re.compile(r'^(\S+)\s+([^,;—]+?),\s*([^;]*?);(.*)$', re.S)
GREEK_SCRIPT = re.compile(r'^[\u0370-\u03FF\u1F00-\u1FFF]+$')
HEBREW_SCRIPT = re.compile(r'^[\u0590-\u05FF]+$')

GREEK_SHA = '5c472d15d1d9aab91b7f105d14b66784b3b317d52e5e01c095a5ff0138c4e7b6'
HEBREW_SHA = '2d2ad555cba63aa7e8a15d6a05c2dd31709bc8456312d429def69757527b4bba'


def norm_ws(s):
    return re.sub(r'\s+', ' ', s).strip()


def entry_like(rest):
    # Corrupted heading remainder looks like "<headword> <translit>, <pron>'; ..."
    # (OCR sometimes drops the comma: "<headword> <translit> <pron>'; ...").
    head = rest[:100]
    return (("';" in head) or (',' in head)) and (';' in rest[:200])


def split_heading(line):
    """Return (token, rest, is_digits). Handles the '1.6.'-for-16 OCR pattern."""
    m2 = CORRUPT_DOT_RE.match(line)
    if m2:
        return m2.group(1) + m2.group(2), m2.group(3), True
    m = HEAD_RE.match(line)
    if m:
        return m.group(1), m.group(2), m.group(1).isdigit()
    return None, None, False


def strict_run(heads, start_pos, max_n):
    """Longest-run scoring for block-start detection over the heading list.
    A run ends (not continues) on out-of-order or non-entry-like headings."""
    expected = 1
    for pos in range(start_pos, len(heads)):
        h = heads[pos]
        tok, rest, is_digits = h['tok'], h['rest'], h['is_digits']
        if is_digits:
            num = int(tok)
            if num == expected:
                expected += 1
            elif digit_diffs(tok, str(expected)) == 1:
                expected += 1  # OCR digit confusion
            elif expected < num <= max_n and (num - expected) <= 500:
                expected = num + 1  # genuine gap
            else:
                break
        else:
            if entry_like(rest):
                expected += 1
            else:
                break
    return expected - 1


def find_block_start(heads, lines, max_n):
    cands = [p for p, h in enumerate(heads)
             if h['tok'] == '1' and h['is_digits']]
    scored = [(strict_run(heads, p, max_n), heads[p]['line_no']) for p in cands]
    scored.sort(reverse=True)
    best_run, best_line = scored[0]
    print(f'  block-start candidates (run, line): {scored} -> line {best_line}')
    return best_line


def build_headings(lines):
    """Every candidate heading in file order: dicts with line_no, tok, rest,
    is_digits, and the original line. Stops at the closing NOTE."""
    heads = []
    for i, line in enumerate(lines):
        if line.strip() == 'NOTE.':
            break
        tok, rest, is_digits = split_heading(line)
        if tok is not None:
            heads.append({'line_no': i, 'tok': tok, 'rest': rest,
                          'is_digits': is_digits, 'line': line})
    return heads


def next_clean_value(heads, idx):
    """int value of the next clean-digit heading after heads[idx], or None."""
    for h in heads[idx + 1:]:
        if h['is_digits']:
            return int(h['tok'])
    return None


def parse_file(fname, max_n, prefix, lang):
    path = os.path.join(RAW, fname)
    with open(path, encoding='utf-8', errors='replace') as f:
        lines = f.read().splitlines()
    note_idx = next((i for i, l in enumerate(lines) if l.strip() == 'NOTE.'),
                    len(lines))
    heads = build_headings(lines)
    print(f'  {len(heads)} candidate headings in file order')
    start_line = find_block_start(heads, lines, max_n)
    heads = [h for h in heads if h['line_no'] >= start_line]

    entries = {}       # num -> rec dict
    events = {'normalizations': [], 'gaps': [], 'offbyone': [],
              'backward': [], 'duplicates': [], 'uncertain': [],
              'no_emdash': [], 'field_parse_fail': []}
    expected = 1
    cur_num, cur_lines, cur_lineno = None, [], None

    def finalize():
        if cur_num is None:
            return
        raw_text = norm_ws(' '.join(cur_lines))
        rec = {'num': cur_num, 'line_no': cur_lineno, 'entry_text': raw_text,
               'headword_original': None, 'transliteration': None,
               'pronunciation': None, 'etymology': None, 'kjv_glosses': None}
        m = FIELD_RE.match(raw_text)
        if m:
            hw = m.group(1).lstrip('"\'*')
            script_re = GREEK_SCRIPT if lang == 'greek' else HEBREW_SCRIPT
            rec['headword_original'] = hw if script_re.match(hw) else None
            rec['transliteration'] = norm_ws(m.group(2))
            rec['pronunciation'] = norm_ws(m.group(3))
            rest = norm_ws(m.group(4))
            if '—' in rest:
                ety, gl = rest.split('—', 1)
                rec['etymology'] = norm_ws(ety)
                rec['kjv_glosses'] = norm_ws(gl)
            else:
                rec['etymology'] = rest
                events['no_emdash'].append(cur_num)
        else:
            rec['etymology'] = raw_text
            events['field_parse_fail'].append(cur_num)
        entries[cur_num] = rec

    def begin(num, h, note=None):
        """Start a new entry; returns False if num already present (keeps first)."""
        nonlocal expected, cur_num, cur_lines, cur_lineno
        finalize()
        if num in entries:
            events['duplicates'].append(
                {'num': num, 'token': h['tok'], 'line_no': h['line_no']})
            cur_num, cur_lines, cur_lineno = None, [], None
            return False
        cur_num, cur_lines, cur_lineno = num, [h['rest']], h['line_no']
        if note:
            events['normalizations'].append(
                {'num': num, 'token': note, 'line_no': h['line_no']})
        expected = num + 1
        return True

    def attach_continuation(h, tail):
        if cur_num is not None:
            cur_lines.append(h['line'])
            cur_lines.extend(tail)

    for idx, h in enumerate(heads):
        upto = heads[idx + 1]['line_no'] if idx + 1 < len(heads) else note_idx
        tail = [l for l in lines[h['line_no'] + 1:upto] if l.strip()]
        tok, rest, is_digits = h['tok'], h['rest'], h['is_digits']
        if is_digits:
            num = int(tok)
            if num == expected:
                if begin(num, h):
                    cur_lines.extend(tail)
            elif (digit_diffs(tok, str(expected)) == 1
                    or dropped_digit(tok, expected)):
                # provisional OCR digit confusion; confirm with lookahead
                t2 = next_clean_value(heads, idx)
                t2s = str(t2) if t2 is not None else None
                if t2 is not None and t2 == num + 1 and t2 != expected + 1:
                    # next heading continues the face-value number: a heading
                    # was entirely lost (off by one), token is not misread
                    events['offbyone'].append(
                        {'token': tok, 'face_value': num,
                         'expected_was': expected, 'line_no': h['line_no']})
                    events['gaps'].append({'from': expected, 'to': num - 1})
                    if begin(num, h, note=f'{tok}~{num}(off-by-one)'):
                        cur_lines.extend(tail)
                else:
                    confident = (t2 == expected + 1 or
                                 (t2s is not None and
                                  (digit_diffs(t2s, str(expected + 1)) == 1 or
                                   dropped_digit(t2s, expected + 1))))
                    if begin(expected, h, note=f'{tok}~{expected}'):
                        cur_lines.extend(tail)
                    if not confident:
                        events['uncertain'].append(
                            {'token': tok, 'assigned': expected,
                             'line_no': h['line_no']})
            elif num < 1 or num > max_n:
                events['backward'].append(
                    {'token': tok, 'line_no': h['line_no'],
                     'reason': 'out-of-range'})
                attach_continuation(h, tail)
            elif num > expected:
                dd = digit_diffs(tok, str(expected))
                if (num - expected) <= 2 or (dd is not None and dd <= 2):
                    # near-miss of expected: misread, not a real jump
                    if begin(expected, h, note=f'{tok}~{expected}(near-miss)'):
                        cur_lines.extend(tail)
                    if dd == 2:
                        events['uncertain'].append(
                            {'token': tok, 'assigned': expected,
                             'line_no': h['line_no']})
                else:
                    events['gaps'].append({'from': expected, 'to': num - 1})
                    if begin(num, h, note=f'{tok}(gap-jump)'):
                        cur_lines.extend(tail)
            else:  # num < expected: re-scan or stray; merge as continuation
                events['backward'].append(
                    {'token': tok, 'line_no': h['line_no'],
                     'reason': 'lt-expected'})
                attach_continuation(h, tail)
        else:
            if entry_like(rest):
                if begin(expected, h, note=f'{tok}~{expected}(corrupted)'):
                    cur_lines.extend(tail)
            else:
                attach_continuation(h, tail)
    finalize()
    return entries, events


def main():
    # verify raw file hashes
    for lang, (fname, max_n, prefix) in FILES.items():
        h = hashlib.sha256(open(os.path.join(RAW, fname), 'rb').read()).hexdigest()
        want = GREEK_SHA if lang == 'greek' else HEBREW_SHA
        assert h == want, f'hash mismatch for {fname}: {h}'
        print(f'{lang}: sha256 ok')

    all_entries, all_events = {}, {}
    for lang, (fname, max_n, prefix) in FILES.items():
        print(f'parsing {lang} ...')
        entries, events = parse_file(fname, max_n, prefix, lang)
        all_entries[lang] = entries
        all_events[lang] = events
        missing = sorted(set(range(1, max_n + 1)) - set(entries))
        print(f'  recovered {len(entries)}/{max_n} ({100*len(entries)/max_n:.1f}%), '
              f'norm={len(events["normalizations"])}, gaps={len(events["gaps"])}, '
              f'offbyone={len(events["offbyone"])}, backward={len(events["backward"])}, '
              f'dup={len(events["duplicates"])}, uncertain={len(events["uncertain"])}, '
              f'no_emdash={len(events["no_emdash"])}, field_fail={len(events["field_parse_fail"])}')
        if missing:
            print(f'  missing numbers (first 30): {missing[:30]}{" ..." if len(missing) > 30 else ""}')
        if events['uncertain'][:10]:
            print(f'  uncertain (first 10): {events["uncertain"][:10]}')

    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump({lang: {'normalizations': ev['normalizations'], 'gaps': ev['gaps'],
                          'offbyone': ev['offbyone'], 'backward': ev['backward'],
                          'duplicates': ev['duplicates'], 'uncertain': ev['uncertain'],
                          'no_emdash': ev['no_emdash'],
                          'field_parse_fail': ev['field_parse_fail'],
                          'recovered': sorted(all_entries[lang].keys())}
                   for lang, ev in all_events.items()}, f, ensure_ascii=False, indent=1)
    print(f'parse log: {LOG_PATH}')

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('DROP TABLE IF EXISTS strongs')
    cur.execute('''CREATE TABLE strongs (
        strongs_number TEXT PRIMARY KEY,
        language TEXT NOT NULL,
        num INTEGER NOT NULL,
        headword_original TEXT,
        transliteration TEXT,
        pronunciation TEXT,
        etymology TEXT,
        kjv_glosses TEXT,
        entry_text TEXT NOT NULL)''')
    cur.execute('CREATE INDEX idx_strongs_lang_num ON strongs(language, num)')
    total = 0
    for lang, (fname, max_n, prefix) in FILES.items():
        for num in sorted(all_entries[lang]):
            e = all_entries[lang][num]
            cur.execute('INSERT INTO strongs VALUES (?,?,?,?,?,?,?,?,?)',
                        (f'{prefix}{num}', lang, num, e['headword_original'],
                         e['transliteration'], e['pronunciation'], e['etymology'],
                         e['kjv_glosses'], e['entry_text']))
            total += 1
    rights_basis = (
        'James Strong, A Concise Dictionary of the Words in the Greek Testament '
        '(1890) and of the Words in the Hebrew Bible (1890). First published 1890; '
        'public domain by age. Transcription: Internet Archive item '
        "'StrongsGreekAndHebrewDictionaries1890' declares CC0 1.0 (licenseurl, "
        'creator James Strong); IA djvu.txt OCR is a mechanical reproduction of '
        'PD works and creates no new copyright. Commercial use OK, no attribution '
        'required. Retrieved 2026-09-20.')
    cur.execute("DELETE FROM sources WHERE source_id='strongs'")
    cur.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',
                ('strongs', 'lexicon',
                 "Strong's Hebrew and Greek Dictionaries (1890)",
                 'Public Domain', rights_basis, '1890 / IA djvu.txt',
                 f'greek:{GREEK_SHA}; hebrew:{HEBREW_SHA}'))
    con.commit()
    n = cur.execute('SELECT COUNT(*) FROM strongs').fetchone()[0]
    assert n == total
    cur.execute('PRAGMA integrity_check')
    assert cur.fetchone()[0] == 'ok'
    con.close()
    print(f'study.db: strongs table = {n} rows, integrity ok')


if __name__ == '__main__':
    main()
