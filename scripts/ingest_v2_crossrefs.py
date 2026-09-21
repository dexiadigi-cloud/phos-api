#!/usr/bin/env python3
"""V2 staging ingest: Treasury of Scripture Knowledge cross-references.

Reads the CrossWire TSK SWORD module (raw_v2/tsk/TSK.zip, extracted to TSK_raw/),
parses per-chapter cross-reference sections, KJV-aligns phrases to verses
(monotone, with bare-number verse-end markers as anchors), parses/validates/
range-expands references against KJV bounds via api/parser.py and api/db.py,
and writes staging/crossrefs.db with the exact required schema.

Staging only. Does not create data/study.db. Does not write scripture.db.
"""
import struct, zlib, re, sys, os, sqlite3, hashlib, zipfile, logging

# --- paths ---
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_ZIP = os.path.join(ROOT, 'data', 'raw_v2', 'tsk', 'TSK.zip')
RAW_DIR = os.path.join(ROOT, 'data', 'raw_v2', 'tsk', 'TSK_raw')
MOD_DIR = os.path.join(RAW_DIR, 'modules', 'comments', 'zcom', 'tsk')
STAGING_DB = os.path.join(ROOT, 'staging', 'crossrefs.db')
LOG_PATH = os.path.join(ROOT, 'verification', 'v2', 'ingest.log')

os.makedirs(os.path.join(ROOT, 'staging'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'verification', 'v2'), exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format='%(message)s')
log = logging.getLogger()

sys.path.insert(0, ROOT)
from api import parser as P
from api import db as dbmod

BOUNDS = dbmod.get_bounds("KJV")
BOOK_ORDER = P.CANONICAL_BOOKS  # SWORD blocks are in canonical order
# map canonical book name -> index
BOOK_IDX = {b: i for i, b in enumerate(BOOK_ORDER)}

# TSK book abbreviations -> canonical names (parser.resolve_book covers most;
# these are explicit manual aliases for the TSK module's abbreviations)
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

def resolve_book(abbr):
    if abbr in MANUAL_ALIASES:
        return MANUAL_ALIASES[abbr]
    try:
        return P.resolve_book(abbr)
    except Exception:
        return None

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

def words(t):
    return re.sub(r'[^a-z0-9 ]', ' ', t.lower()).split()

def longest_prefix(pw, vw, kmax=8):
    for k in range(min(len(pw), kmax), 0, -1):
        pre = pw[:k]
        for s in range(len(vw) - k + 1):
            if vw[s:s+k] == pre:
                return k
    return 0

def parse_tokens(xref):
    toks = []
    for s in re.split(r'<br />', xref):
        s = s.strip()
        if not s:
            continue
        if s.startswith('<scripRef>'):
            mm = re.match(r'<scripRef>(.*?)</scripRef>', s, re.DOTALL)
            inner = mm.group(1).strip() if mm else ''
            toks.append(('marker', int(inner)) if re.fullmatch(r'\d+', inner) else ('refs', inner))
        else:
            phrase = re.sub(r'<[^>]+>', '', s).strip()
            if phrase:
                toks.append(('phrase', phrase))
    return toks

def build_groups(toks):
    groups = []
    cur_phrase = None; cur_refs = []; marker_before = None; pending_marker = None
    prev_was_phrase = False
    for k, v in toks:
        if k == 'marker':
            if prev_was_phrase and cur_phrase:
                # Bare number immediately after a phrase: it's a ref (bare verse
                # number), not a verse-end marker.
                cur_refs.append(str(v))
            else:
                if cur_phrase:
                    groups.append((cur_phrase, cur_refs, marker_before))
                    cur_phrase = None; cur_refs = []; marker_before = None
                pending_marker = v
            prev_was_phrase = False
        elif k == 'phrase':
            if cur_phrase:
                groups.append((cur_phrase, cur_refs, marker_before))
            cur_phrase = v; cur_refs = []
            marker_before = pending_marker; pending_marker = None
            prev_was_phrase = True
        elif k == 'refs':
            if cur_phrase:
                cur_refs.append(v)
            prev_was_phrase = False
    if cur_phrase:
        groups.append((cur_phrase, cur_refs, marker_before))
    return groups

# reference parsing -----------------------------------------------------------
SKIP_TOKENS = ('*marg:', '*title')
REF_SPLIT = re.compile(r'\s*;\s*')

def parse_ref_string(s, cur_book, cur_chap):
    """Parse a TSK ref-list string into (book, chapter, verse) tuples.
    Returns (refs, skipped_invalid, skipped_unresolved, skipped_chapter_only).
    Handles inheritance, ranges, comma lists. Chapter-only refs are skipped.
    """
    refs = []
    n_invalid = 0; n_unresolved = 0; n_chonly = 0
    # strip note tokens
    for tok in SKIP_TOKENS:
        s = s.replace(tok, '')
    parts = REF_SPLIT.split(s)
    book = cur_book
    chap = cur_chap
    for part in parts:
        part = part.strip().rstrip('.')
        if not part:
            continue
        # chapter-only? e.g. "Ge 1" or "1" alone after a book was just named
        # with no colon: treat Book+N (no colon) as chapter-only -> skip.
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
            # bare number after a book with no colon/comma/dash -> chapter only
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
    if mv is None:
        return False
    return 1 <= verse <= mv

def main():
    # provenance: hash the raw zip
    h = hashlib.sha256()
    with open(RAW_ZIP, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    zip_hash = h.hexdigest()
    log.info(f"raw_zip_sha256={zip_hash}")
    log.info("retrieval_date=2026-09-20")
    log.info("source_url=https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/TSK.zip")
    log.info("module_title=Treasury of Scripture Knowledge version=1.4 license=Public Domain")

    books = load_blocks()
    # map block index -> canonical book name (OT 0-38, NT 39-65 in canonical order)
    assert len(BOOK_ORDER) == 66

    # KJV text cache per chapter
    kjv_cache = {}

    def kjv_words(book, chap, verse):
        key = (book, chap, verse)
        if key not in kjv_cache:
            d = dbmod.get_verse("KJV", book, chap, verse)
            kjv_cache[key] = words(d['text']) if d else []
        return kjv_cache[key]

    stats = dict(chapters=0, phrases=0, refs_raw=0, refs_valid=0,
                 skipped_invalid=0, skipped_unresolved=0, skipped_chapter_only=0,
                 lp_zero=0, markers_used=0)

    # collect rows: (head_book, head_chap, head_verse, ref_book, ref_chap, ref_verse)
    rows = set()

    for bi in range(66):
        book = BOOK_ORDER[bi]
        text = books[bi]
        # chapter chunks via outline markers
        markers = [(m.start(), m.group(1), int(m.group(2)))
                   for m in re.finditer(r'<scripRef passage="([A-Za-z0-9]+) (\d+):\d+">', text)]
        # group by chapter
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
        # Determine chapter ranges: a marked chapter covers from itself to
        # (next marked chapter - 1), handling grouped chapters like Pr 10-24.
        marked_chaps = []
        for (babbr, chap), a, b in chunks:
            canon = resolve_book(babbr)
            if canon != book:
                log.info(f"WARN book mismatch block={book} marker={babbr}:{chap}")
                continue
            marked_chaps.append((chap, a, b))
        marked_chaps.sort()
        # Skip grouped chapters that cannot be reliably verse-attributed:
        # Proverbs 10-24 (grouped under Pr 10) and Isaiah 24-27 (grouped under Isa 24).
        # The TSK groups these without verse markers, and KJV phrase alignment
        # drifts unreliably across the range.
        SKIP_RANGES = {('Proverbs', 10, 24), ('Isaiah', 24, 27)}
        for idx, (chap, a, b) in enumerate(marked_chaps):
            chap_end = marked_chaps[idx+1][0] - 1 if idx+1 < len(marked_chaps) else nch
            if chap_end < chap:
                chap_end = chap
            if (book, chap, chap_end) in SKIP_RANGES:
                log.info(f"SKIP grouped range {book} {chap}-{chap_end} (unreliable verse attribution)")
                stats['skipped_unresolved'] += 1
                continue
            chunk = text[a:b]
            tb = re.search(r'<br />\s*<br />\s*<br />', chunk)
            if tb:
                xref = chunk[tb.end():]
            else:
                last_marker = None
                for m in re.finditer(r'<scripRef passage="[A-Za-z0-9]+ \d+:\d+">', chunk):
                    last_marker = m
                if not last_marker:
                    log.info(f"WARN no outline markers {book} {chap}")
                    stats['skipped_unresolved'] += 1
                    continue
                br = re.search(r'<br />', chunk[last_marker.end():])
                if not br:
                    log.info(f"WARN no br after outline {book} {chap}")
                    stats['skipped_unresolved'] += 1
                    continue
                xref = chunk[last_marker.end() + br.end():]
                log.info(f"INFO no triple-br, using outline-end {book} {chap}")
            groups = build_groups(parse_tokens(xref))
            if not groups:
                continue
            stats['chapters'] += 1
            # Build verse sequence spanning [chap, chap_end]
            verse_seq = []
            for cc in range(chap, chap_end + 1):
                mv = BOUNDS[book]['max_verse'].get(str(cc)) or BOUNDS[book]['max_verse'].get(cc)
                for vv in range(1, mv + 1):
                    verse_seq.append((cc, vv))
            # greedy monotone alignment with marker anchors over verse_seq
            # markers are verse-end within the CURRENT chapter; track chapter too.
            # For simplicity, markers reset to (chap_of_marker + 1). Since markers
            # are sparse and within-chapter, we map marker N to the position in
            # verse_seq where chapter==cur_chap and verse==N+1.
            # We'll track index into verse_seq.
            cur_idx = 0
            # map (chap, verse) -> idx for anchor lookup
            pos_of = {cv: i for i, cv in enumerate(verse_seq)}
            cur_chap_track = chap
            for phrase, refstrs, marker_before in groups:
                stats['phrases'] += 1
                if marker_before:
                    stats['markers_used'] += 1
                    # marker is verse-end in cur_chap_track; next verse is +1
                    # (may roll to next chapter if at end)
                    anchor = (cur_chap_track, marker_before + 1)
                    if anchor in pos_of:
                        cur_idx = pos_of[anchor]
                    else:
                        # try next chapter verse 1
                        anchor2 = (cur_chap_track + 1, 1)
                        if anchor2 in pos_of:
                            cur_idx = pos_of[anchor2]
                            cur_chap_track += 1
                pw = words(phrase)
                best_idx, best_lp = cur_idx, -1
                for i in range(cur_idx, len(verse_seq)):
                    cc, vv = verse_seq[i]
                    vw = kjv_words(book, cc, vv)
                    if not vw:
                        continue
                    lp = longest_prefix(pw, vw)
                    if lp > best_lp:
                        best_lp, best_idx = lp, i
                        if lp >= 4:
                            break
                if best_lp == 0:
                    stats['lp_zero'] += 1
                cur_idx = best_idx
                head_c, head_v = verse_seq[best_idx]
                cur_chap_track = head_c
                if not refstrs:
                    continue
                for rs in refstrs:
                    stats['refs_raw'] += 1
                    refs, n_inv, n_unr, n_cho = parse_ref_string(rs, book, head_c)
                    stats['skipped_invalid'] += n_inv
                    stats['skipped_unresolved'] += n_unr
                    stats['skipped_chapter_only'] += n_cho
                    for (rb, rc, rv) in refs:
                        stats['refs_valid'] += 1
                        rows.add((book, head_c, head_v, rb, rc, rv))
    log.info(f"stats={stats}")
    log.info(f"unique_rows={len(rows)}")

    # write staging db with exact required schema
    if os.path.exists(STAGING_DB):
        os.remove(STAGING_DB)
    con = sqlite3.connect(STAGING_DB)
    cur = con.cursor()
    cur.execute("CREATE TABLE sources (source_id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, retrieved TEXT NOT NULL, license TEXT NOT NULL, notes TEXT)")
    cur.execute("CREATE TABLE crossrefs (head_book TEXT NOT NULL, head_chapter INTEGER NOT NULL, head_verse INTEGER NOT NULL, ref_book TEXT NOT NULL, ref_chapter INTEGER NOT NULL, ref_verse INTEGER NOT NULL)")
    cur.execute("CREATE UNIQUE INDEX ux_crossrefs ON crossrefs (head_book, head_chapter, head_verse, ref_book, ref_chapter, ref_verse)")
    cur.execute("CREATE INDEX ix_crossrefs_head ON crossrefs (head_book, head_chapter, head_verse)")
    cur.execute(
        "INSERT INTO sources (source_id, kind, title, retrieved, license, notes) VALUES (?,?,?,?,?,?)",
        ('tsk', 'crossref', 'Treasury of Scripture Knowledge',
         '2026-09-20', 'Public Domain',
         'CrossWire SWORD module TSK v1.4 (SwordVersionDate 2001-12-15), '
         'DistributionLicense=Public Domain. Original/PD TSK tradition '
         '(Canne, Browne, Blayney, Scott, and others, about 1880 per module '
         'description); not R.A. Torrey 1982 New Treasury nor TSKe/derivatives. '
         f'Raw ZIP SHA-256={zip_hash}.'))
    cur.executemany(
        "INSERT OR IGNORE INTO crossrefs (head_book, head_chapter, head_verse, ref_book, ref_chapter, ref_verse) VALUES (?,?,?,?,?,?)",
        sorted(rows))
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM crossrefs").fetchone()[0]
    con.close()
    log.info(f"wrote {n} rows to {STAGING_DB}")
    print(f"done: {n} rows, stats={stats}")

if __name__ == '__main__':
    main()
