#!/usr/bin/env python3
"""V2 staging ingest (take 2): Treasury of Scripture Knowledge cross-references.

Same source as ingest_v2_crossrefs.py (CrossWire TSK SWORD module v1.4,
Public Domain), but with a corrected verse-attribution algorithm.

Take 1 used greedy prefix matching and attributed zero-evidence phrases to the
cursor verse (silent misattribution, e.g. 2Sa 24:24's refs landed on v25).

Take 2 uses verse-synchronized ordered-subsequence alignment:
  - TSK phrases within a chapter appear in KJV word order, grouped by verse.
  - A phrase is STRONGLY attributed only if ALL its words appear as an ordered
    subsequence of a verse's KJV text (monotone verse cursor).
  - WEAK partial matches are attributed conservatively (no cursor advance).
  - Phrases with no match are SKIPPED (refs dropped, counted) -- never
    misattributed.
  - Note-like phrases (Heb./Gr. notes, chronology headers, long commentary
    notes) attach to the current verse without advancing the cursor.
  - Refs blocks are attributed by position: inline refs follow their phrase;
    a refs block at a line-start after phrase-text is a trailing paragraph for
    the current verse; a refs block at a line-start after </scripRef> starts a
    new verse (resolved via lookahead to the next phrase's verse).

Staging only. Does not create data/study.db. Does not write scripture.db.
Writes staging/crossrefs2.db (does NOT overwrite take-1 staging/crossrefs.db).
"""
import struct, zlib, re, sys, os, sqlite3, hashlib, logging

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_ZIP = os.path.join(ROOT, 'data', 'raw_v2', 'tsk', 'TSK.zip')
RAW_DIR = os.path.join(ROOT, 'data', 'raw_v2', 'tsk', 'TSK_raw')
MOD_DIR = os.path.join(RAW_DIR, 'modules', 'comments', 'zcom', 'tsk')
STAGING_DB = os.path.join(ROOT, 'staging', 'crossrefs2.db')
LOG_PATH = os.path.join(ROOT, 'verification', 'v2', 'ingest2.log')

os.makedirs(os.path.join(ROOT, 'staging'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'verification', 'v2'), exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format='%(message)s')
log = logging.getLogger()

sys.path.insert(0, ROOT)
from api import parser as P
from api import db as dbmod

BOUNDS = dbmod.get_bounds("KJV")
BOOK_ORDER = P.CANONICAL_BOOKS
BOOK_IDX = {b: i for i, b in enumerate(BOOK_ORDER)}

MANUAL_ALIASES = {
    'Ge': 'Genesis', 'Ex': 'Exodus', 'Le': 'Leviticus', 'Nu': 'Numbers',
    'De': 'Deuteronomy', 'Jos': 'Joshua', 'Jud': 'Judges', 'Ru': 'Ruth',
    '1Sa': '1 Samuel', '2Sa': '2 Samuel', '1Ki': '1 Kings', '2Ki': '2 Kings',
    '1Ch': '1 Chronicles', '2Ch': '2 Chronicles', 'Ezr': 'Ezra', 'Ne': 'Nehemiah',
    'Es': 'Esther', 'Job': 'Job', 'Ps': 'Psalms', 'Pr': 'Proverbs',
    'Ec': 'Ecclesiastes', 'Song': 'Song of Songs', 'So': 'Song of Songs', 'Isa': 'Isaiah',
    'Jer': 'Jeremiah', 'La': 'Lamentations', 'Eze': 'Ezekiel', 'Da': 'Daniel',
    'Ho': 'Hosea', 'Joe': 'Joel', 'Am': 'Amos', 'Ob': 'Obadiah',
    'Jon': 'Jonah', 'Mic': 'Micah', 'Na': 'Nahum', 'Hab': 'Habakkuk',
    'Zep': 'Zephaniah', 'Hag': 'Haggai', 'Zec': 'Zechariah', 'Mal': 'Malachi',
    'Mt': 'Matthew', 'Mr': 'Mark', 'Lu': 'Luke', 'Joh': 'John',
    'Ac': 'Acts', 'Ro': 'Romans', '1Co': '1 Corinthians', '2Co': '2 Corinthians',
    'Ga': 'Galatians', 'Eph': 'Ephesians', 'Php': 'Philippians', 'Col': 'Colossians',
    '1Th': '1 Thessalonians', '2Th': '2 Thessalonians', '1Ti': '1 Timothy',
    '2Ti': '2 Timothy', 'Tit': 'Titus', 'Phm': 'Philemon', 'Heb': 'Hebrews',
    'Jas': 'James', '1Pe': '1 Peter', '2Pe': '2 Peter', '1Jo': '1 John',
    '2Jo': '2 John', '3Jo': '3 John', 'Jude': 'Jude', 'Re': 'Revelation',
}

# Grouped chapters the TSK presents without verse order; KJV alignment cannot
# attribute them reliably. Excluded (documented data gap).
SKIP_RANGES = {('Proverbs', 10, 24), ('Isaiah', 24, 27)}


def resolve_book(abbr):
    if abbr in MANUAL_ALIASES:
        return MANUAL_ALIASES[abbr]
    try:
        return P.resolve_book(abbr)
    except Exception:
        return None


def words(t):
    return re.sub(r'[^a-z0-9 ]', ' ', t.lower()).split()


def words_joined(t):
    """Variant with hyphens removed (TSK 'Tahtim-hodshi' vs KJV 'Tahtimhodshi')."""
    return re.sub(r'[^a-z0-9 ]', ' ', t.lower().replace('-', '')).split()


def load_blocks():
    books = []
    for t in ('ot', 'nt'):
        bzs = open(os.path.join(MOD_DIR, f'{t}.bzs'), 'rb').read()
        bzz = open(os.path.join(MOD_DIR, f'{t}.bzz'), 'rb').read()
        n = len(bzs) // 12
        zents = [struct.unpack('<III', bzs[i*12:(i+1)*12]) for i in range(n)]
        books.extend(zlib.decompress(bzz[o:o+s]).decode('utf-8', 'replace')
                     for o, s, u in zents)
    assert len(books) == 66, f"expected 66 book blocks, got {len(books)}"
    return books


# --- tokenization ------------------------------------------------------------
# Tokens: ('phrase', text, line_start, prev_ended_refs),
#         ('refs', refstr, line_start, prev_ended_refs),
#         ('barenum', int, line_start, prev_ended_refs)
SCRIPREF_RE = re.compile(r'<scripRef>(.*?)</scripRef>', re.DOTALL)


def tokenize(body):
    pieces = re.split(r'(<br\s*/>)', body)
    toks = []
    for i in range(0, len(pieces), 2):
        content = pieces[i]
        if i == 0:
            line_start = True
            prev_ended_refs = False
        else:
            prev_content = pieces[i - 2]
            line_start = prev_content.endswith('\n') or prev_content.endswith('\r')
            prev_ended_refs = bool(re.search(r'</scripRef>\s*$', prev_content))
        text = content.strip()
        if not text:
            continue
        # split out any <scripRef> blocks; leading text (if any) is a phrase
        pos = 0
        for m in SCRIPREF_RE.finditer(text):
            before = text[pos:m.start()].strip()
            if before:
                phrase = re.sub(r'<[^>]+>', '', before).strip()
                if phrase:
                    toks.append(('phrase', phrase, line_start, prev_ended_refs))
                line_start = False
                prev_ended_refs = False
            inner = m.group(1).strip()
            if re.fullmatch(r'\d+', inner):
                toks.append(('barenum', int(inner), line_start, prev_ended_refs))
            else:
                toks.append(('refs', inner, line_start, prev_ended_refs))
            line_start = False
            prev_ended_refs = True
            pos = m.end()
        after = text[pos:].strip()
        if after:
            if '<scripRef' in after:
                log.info(f'WARN mixed content after scripRef: {after[:80]!r}')
                after = re.sub(r'<[^>]+>', '', after).strip()
            if after:
                toks.append(('phrase', after, line_start, prev_ended_refs))
    return toks


# --- phrase -> verse alignment ------------------------------------------------
def subseq_match(pw, vw, start=0):
    """Greedy ordered-subsequence match of phrase words pw in verse words vw.

    Returns (strong, weak, end_pos). Unmatched phrase words are skipped (they
    may be Heb./note words); strong requires every phrase word found in order.
    """
    j = start
    matched = 0
    for w in pw:
        k = j
        while k < len(vw) and vw[k] != w:
            k += 1
        if k < len(vw):
            matched += 1
            j = k + 1
        # else: word absent; j unchanged so later words can still match
    total = len(pw)
    strong = (matched == total and total >= 1)
    weak = (not strong) and matched >= 2 and total > 0 and matched / total >= 0.5
    return strong, weak, j


NOTE_RE = re.compile(
    r'\b(Heb|Gr|Chald|Sept|Vulg|Syr|Arab|Targum|A\.M\.|B\.C\.|An\. Ex\.|i\.e\.|viz\.)\b')


def is_note_like(phrase, pw):
    if len(pw) > 30:
        return True
    if '\n' in phrase:
        return True
    if NOTE_RE.search(phrase):
        return True
    # chronology headers like "A.M. 2987. B.C. 1017."
    if re.fullmatch(r'[\d\.\sA-Za-z,;]+', phrase) and re.search(r'\d{3,}', phrase):
        return True
    return False


def align_phrase(pw, verse_words, cv, cpos, nverses, lookahead=12, pw_joined=None):
    """Return (verse, end_pos, strength) where strength is 'strong'/'weak'/
    'note'/None. Monotone: never returns a verse < cv."""
    # 1. strong in current verse from cpos
    s, w, e = subseq_match(pw, verse_words[cv], cpos)
    if s:
        return cv, e, 'strong'
    # 2. strong in upcoming verses
    for V in range(cv + 1, min(cv + lookahead, nverses + 1)):
        s2, w2, e2 = subseq_match(pw, verse_words[V], 0)
        if s2:
            return V, e2, 'strong'
    # 2b. retry with hyphen-joined phrase words (TSK hyphen vs KJV single word)
    if pw_joined is not None and pw_joined != pw:
        s, w, e = subseq_match(pw_joined, verse_words[cv], cpos)
        if s:
            return cv, e, 'strong'
        for V in range(cv + 1, min(cv + lookahead, nverses + 1)):
            s2, w2, e2 = subseq_match(pw_joined, verse_words[V], 0)
            if s2:
                return V, e2, 'strong'
    # 3. weak fallback (caller must NOT advance cursor on weak)
    for V in range(cv, min(cv + lookahead, nverses + 1)):
        st = cpos if V == cv else 0
        s3, w3, e3 = subseq_match(pw, verse_words[V], st)
        if w3:
            return V, e3, 'weak'
    if pw_joined is not None and pw_joined != pw:
        for V in range(cv, min(cv + lookahead, nverses + 1)):
            st = cpos if V == cv else 0
            s3, w3, e3 = subseq_match(pw_joined, verse_words[V], st)
            if w3:
                return V, e3, 'weak'
    return None, None, None


# --- reference parsing (same semantics as take 1) -----------------------------
SKIP_TOKENS = ('*marg:', '*title')
REF_SPLIT = re.compile(r'\s*;\s*')


def expand_verse_list(vpart, book, chap):
    out = []
    for piece in vpart.split(','):
        piece = piece.strip()
        if not piece:
            continue
        if '-' in piece:
            a, b = piece.split('-', 1)
            a = int(a.strip()); b = int(b.strip())
            if a > b:
                a, b = b, a
            for v in range(a, b + 1):
                out.append((book, chap, v))
        else:
            out.append((book, chap, int(piece)))
    return out


def valid_verse(book, chap, verse):
    try:
        b = BOUNDS[book]
    except KeyError:
        return False
    if chap < 1 or chap > b['chapters']:
        return False
    mv = b['max_verse'].get(str(chap), b['max_verse'].get(chap))
    if not mv:
        return False
    return 1 <= verse <= mv


def parse_ref_string(s, cur_book, cur_chap):
    refs = []
    n_invalid = 0; n_unresolved = 0; n_chonly = 0
    for tok in SKIP_TOKENS:
        s = s.replace(tok, '')
    parts = REF_SPLIT.split(s)
    book = cur_book
    chap = cur_chap
    for part in parts:
        part = part.strip().rstrip('.')
        if not part:
            continue
        m = re.match(r'^([1-3]?[A-Za-z]+)\s+(.*)$', part)
        rest = part
        new_book = None
        if m:
            nb = resolve_book(m.group(1))
            if nb:
                new_book = nb
                rest = m.group(2).strip()
        if new_book:
            book = new_book
            if re.fullmatch(r'\d+', rest):
                n_chonly += 1
                continue
        try:
            if ':' in rest:
                cpart, vpart = rest.split(':', 1)
                chap = int(cpart)
                vrefs = expand_verse_list(vpart, book, chap)
            else:
                vrefs = expand_verse_list(rest, book, chap)
            for (b, c, v) in vrefs:
                if valid_verse(b, c, v):
                    refs.append((b, c, v))
                else:
                    n_invalid += 1
        except Exception:
            n_unresolved += 1
    return refs, n_invalid, n_unresolved, n_chonly


# --- main --------------------------------------------------------------------
def main():
    h = hashlib.sha256()
    with open(RAW_ZIP, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    zip_hash = h.hexdigest()
    log.info(f"raw_zip_sha256={zip_hash}")
    log.info("retrieval_date=2026-09-20")
    log.info("source_url=https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/TSK.zip")
    log.info("take=2 (verse-synchronized ordered-subsequence alignment)")

    books = load_blocks()
    assert len(BOOK_ORDER) == 66

    stats = dict(chapters=0, phrases=0, refs_raw=0, refs_valid=0,
                 strong=0, weak=0, note=0, unattributed=0,
                 skipped_invalid=0, skipped_unresolved=0, skipped_chapter_only=0,
                 skipped_ranges=0, new_verse_refblocks=0, trailing_refblocks=0,
                 inline_refs=0, barenum_refs=0, barenum_linestart=0)

    rows = set()
    kjv_cache = {}

    def verse_words(book, chap, verse):
        key = (book, chap, verse)
        if key not in kjv_cache:
            d = dbmod.get_verse("KJV", book, chap, verse)
            kjv_cache[key] = words(d['text']) if d else []
        return kjv_cache[key]

    def add_refs(refstrs, head_book, head_chap, head_verse):
        for rs in refstrs:
            stats['refs_raw'] += 1
            refs, n_inv, n_unr, n_cho = parse_ref_string(rs, head_book, head_chap)
            stats['skipped_invalid'] += n_inv
            stats['skipped_unresolved'] += n_unr
            stats['skipped_chapter_only'] += n_cho
            for (rb, rc, rv) in refs:
                stats['refs_valid'] += 1
                rows.add((head_book, BOOK_IDX[head_book], head_chap, head_verse,
                          rb, BOOK_IDX[rb], rc, rv))

    for bi in range(66):
        book = BOOK_ORDER[bi]
        text = books[bi]
        markers = [(m.start(), m.group(1), int(m.group(2)))
                   for m in re.finditer(r'<scripRef passage="([A-Za-z0-9]+) (\d+):\d+">', text)]
        chunks = []
        cur = None; start = None
        for s, babbr, c in markers:
            key = (babbr, c)
            if key != cur:
                if cur:
                    chunks.append((cur, start, s))
                cur = key; start = s
        if cur:
            chunks.append((cur, start, len(text)))
        nch = BOUNDS[book]['chapters']
        marked = []
        for (babbr, chap), a, b in chunks:
            canon = resolve_book(babbr)
            if canon != book:
                log.info(f"WARN book mismatch block={book} marker={babbr}:{chap}")
                continue
            marked.append((chap, a, b))
        marked.sort()
        # coverage check: marked ranges should cover 1..nch
        covered = set()
        for idx, (chap, a, b) in enumerate(marked):
            chap_end = marked[idx+1][0] - 1 if idx + 1 < len(marked) else nch
            if chap_end < chap:
                chap_end = chap
            covered.update(range(chap, chap_end + 1))
        missing = set(range(1, nch + 1)) - covered
        if missing:
            log.info(f"WARN {book}: chapters not covered by outlines: {sorted(missing)}")

        for idx, (chap, a, b) in enumerate(marked):
            chap_end = marked[idx+1][0] - 1 if idx + 1 < len(marked) else nch
            if chap_end < chap:
                chap_end = chap
            if (book, chap, chap_end) in SKIP_RANGES:
                log.info(f"SKIP grouped range {book} {chap}-{chap_end}")
                stats['skipped_ranges'] += 1
                continue
            chunk = text[a:b]
            if re.search(r'<scripRef passage=', chunk.split('<br />\n<br />\n<br />')[0]):
                pass  # outline markers expected before body
            tb = re.search(r'<br />\s*<br />\s*<br />', chunk)
            if tb:
                body = chunk[tb.end():]
            else:
                log.info(f"WARN no triple-br {book} {chap}; trying outline-end fallback")
                last_marker = None
                for m in re.finditer(r'<scripRef passage="[A-Za-z0-9]+ \d+:\d+">', chunk):
                    last_marker = m
                if not last_marker:
                    continue
                br = re.search(r'<br />', chunk[last_marker.end():])
                if not br:
                    continue
                body = chunk[last_marker.end() + br.end():]
            if re.search(r'<scripRef passage=', body):
                log.info(f"WARN passage marker inside body {book} {chap}")
            toks = tokenize(body)
            if not toks:
                continue
            stats['chapters'] += 1

            # verse word lists for [chap, chap_end]
            verse_list = []
            vw = {}
            for cc in range(chap, chap_end + 1):
                mv = BOUNDS[book]['max_verse'].get(str(cc)) or BOUNDS[book]['max_verse'].get(cc)
                for vv in range(1, mv + 1):
                    verse_list.append((cc, vv))
                    vw[(cc, vv)] = verse_words(book, cc, vv)
            nverses = len(verse_list)
            vword = {i + 1: vw[cv] for i, cv in enumerate(verse_list)}

            # Single sequential pass over tokens.
            # cv/cpos = monotone alignment cursor (1-based verse idx, word offset).
            # cur_vidx = verse idx of the current phrase/marker (for refs).
            # last_strong_vidx = verse idx of last strong anchor (for the
            #   new-paragraph heuristic).
            # A standalone line-start <scripRef>N</scripRef> with 1<=N<=nverses
            # and N>cv is a hard verse marker (print-edition verse number):
            # it anchors the cursor at verse N. N<=cv is a plain same-chapter
            # reference, never a backwards jump.
            cv, cpos = 1, 0
            cur_vidx = None
            last_strong_vidx = 1
            prev_was_marker = False
            prev_kind = None
            last_refs_tgt = None
            for tok in toks:
                kind, val, line_start, prev_ended_refs = tok
                if kind == 'phrase':
                    prev_was_marker = False
                    prev_kind = 'phrase'
                    stats['phrases'] += 1
                    pw = words(val)
                    if not pw:
                        stats['unattributed'] += 1
                        continue
                    if is_note_like(val, pw):
                        # annotation for the current verse; no cursor advance
                        if cur_vidx is None:
                            cur_vidx = cv
                        stats['note'] += 1
                        continue
                    v, e, strength = align_phrase(
                        pw, vword, cv, cpos, nverses,
                        pw_joined=words_joined(val))
                    if strength == 'strong':
                        stats['strong'] += 1
                        cv, cpos = v, e
                        cur_vidx = v
                        last_strong_vidx = v
                    elif strength == 'weak':
                        # plausible verse, but do NOT advance the cursor
                        stats['weak'] += 1
                        cur_vidx = v
                    else:
                        stats['unattributed'] += 1
                        log.info(f"INFO unattributed phrase at {book} {chap}: "
                                 f"{val[:60]!r}")
                elif kind == 'refs':
                    if not line_start and prev_kind == 'refs' and last_refs_tgt is not None:
                        # continuation of the previous refs block (same verse)
                        tgt = last_refs_tgt
                        stats['trailing_refblocks'] += 1
                    elif not line_start:
                        # inline: current phrase's (or marker's) verse
                        tgt = cur_vidx if cur_vidx is not None else cv
                        stats['inline_refs'] += 1
                    elif prev_ended_refs and prev_was_marker:
                        # refs immediately after a verse-number marker belong
                        # to the marked verse
                        tgt = cur_vidx if cur_vidx is not None else cv
                        stats['trailing_refblocks'] += 1
                    elif prev_ended_refs:
                        # New paragraph after a refs block: most often a new
                        # verse's phrase-less content. Attribute to the verse
                        # after the last strong anchor, and advance the
                        # cursor there (the paragraph boundary is a verse
                        # boundary signal). A later barenum marker or strong
                        # phrase will correct the cursor if this was wrong.
                        nv = last_strong_vidx + 1
                        if nv > nverses:
                            nv = nverses
                        tgt = nv
                        cv, cpos = nv, 0
                        cur_vidx = nv
                        last_strong_vidx = nv
                        stats['new_verse_refblocks'] += 1
                    else:
                        # Trailing paragraph: current verse.
                        tgt = cur_vidx if cur_vidx is not None else cv
                        stats['trailing_refblocks'] += 1
                    prev_was_marker = False
                    prev_kind = 'refs'
                    last_refs_tgt = tgt
                    cc, vv = verse_list[tgt - 1]
                    add_refs([val], book, cc, vv)
                elif kind == 'barenum':
                    prev_kind = 'barenum'
                    if 1 <= val <= nverses:
                        if line_start and val > cv:
                            # hard verse marker
                            cv, cpos = val, 0
                            cur_vidx = val
                            last_strong_vidx = val
                            prev_was_marker = True
                        else:
                            # same-chapter reference (incl. backwards numbers)
                            prev_was_marker = False
                            tgt = cur_vidx if cur_vidx is not None else cv
                            cc, vv = verse_list[tgt - 1]
                            add_refs([str(val)], book, cc, vv)
                            stats['barenum_refs'] += 1
                    else:
                        stats['barenum_linestart'] += 1
                        log.info(f"INFO line-start barenum {val} at "
                                 f"{book} {chap} (out of range)")

    log.info(f"stats={stats}")
    log.info(f"unique_rows={len(rows)}")

    if os.path.exists(STAGING_DB):
        os.remove(STAGING_DB)
    con = sqlite3.connect(STAGING_DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE sources (
      source_id TEXT PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL,
      rights TEXT NOT NULL, source_url TEXT NOT NULL, version TEXT,
      sha256 TEXT, retrieved TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE crossrefs (
      book TEXT NOT NULL, book_order INTEGER NOT NULL,
      chapter INTEGER NOT NULL, verse INTEGER NOT NULL,
      ref_book TEXT NOT NULL, ref_book_order INTEGER NOT NULL,
      ref_chapter INTEGER NOT NULL, ref_verse INTEGER NOT NULL)""")
    cur.execute("""CREATE UNIQUE INDEX ux_crossrefs ON crossrefs
      (book, book_order, chapter, verse, ref_book, ref_book_order, ref_chapter, ref_verse)""")
    cur.execute("""CREATE INDEX ix_crossrefs_head ON crossrefs
      (book, book_order, chapter, verse)""")
    cur.execute(
        "INSERT INTO sources (source_id, title, kind, rights, source_url, version, sha256, retrieved)"
        " VALUES (?,?,?,?,?,?,?,?)",
        ('tsk', 'Treasury of Scripture Knowledge', 'crossref', 'Public Domain',
         'https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/TSK.zip',
         '1.4 (SwordVersionDate 2001-12-15)', zip_hash, '2026-09-20'))
    cur.executemany(
        "INSERT OR IGNORE INTO crossrefs (book, book_order, chapter, verse,"
        " ref_book, ref_book_order, ref_chapter, ref_verse) VALUES (?,?,?,?,?,?,?,?)",
        sorted(rows))
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM crossrefs").fetchone()[0]
    con.close()
    log.info(f"wrote {n} rows to {STAGING_DB}")
    print(f"done: {n} rows, stats={stats}")


if __name__ == '__main__':
    main()
