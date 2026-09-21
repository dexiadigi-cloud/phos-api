#!/usr/bin/env python3
"""Stage BCP 1662 and BCP 1928 Morning/Evening Prayer fixed text (V2 liturgy).

Reads:
  data/raw_v2/bcp1662/ws1662_page{057..081}.txt  (Wikisource 1892 reprint transcription)
  data/raw_v2/bcp1928/mp.htm, ep.htm             (Justus transcription via Wayback)

Writes:
  staging/liturgy.db  (sources, liturgy tables)

Stdlib only (sqlite3, re, os, sys, hashlib). Deterministic.
Plain text output; HTML tag and entity leak checks must return 0.
"""

import os
import re
import sys
import sqlite3
import hashlib

BASE = os.path.expanduser('~/workspace/scripture-desk')
RAW1662 = os.path.join(BASE, 'data/raw_v2/bcp1662')
RAW1928 = os.path.join(BASE, 'data/raw_v2/bcp1928')
DB = os.path.join(BASE, 'staging/liturgy.db')

# === from bcp1662.py ===
RAW = os.path.expanduser('~/workspace/scripture-desk/data/raw_v2/bcp1662')

# ----------------------------------------------------------------------------
# Scan-adjudicated corrections: transcription -> verified 1892 print reading.
# Each was verified against the 1280px scan of the stated page.
# ----------------------------------------------------------------------------
CORRECTIONS = [
    # MP Te Deum (p63)
    ("Heaven and earth are full of the Majesty glory.",
     "Heaven and earth are full of the Majesty : of thy glory."),
    ("The glorious Company of the Apostles thee.",
     "The glorious Company of the Apostles : praise thee."),
    ("When thou tookest vpon thee to deliver thou didst not abhor the Virgins Womb.",
     "When thou tookest vpon thee to deliver man : thou didst not abhor the Virgins Womb."),
    # Chrysostom heading (pp70, 80/81) - scan reads "Chrysostome"
    ("A Prayer of Saint Chrysostome.", "A Prayer of Saint Chrysostome."),
    # EP Magnificat (p76)
    ("Evening Prayer He hath filled the hungTy with good things :",
     "He hath filled the hungry with good things :"),
    # EP absolution (p74) - print has "hls" (manuscript typo, faithfully reprinted)
    ("we may come to his eternall ioy,", "we may come to hls eternall ioy,"),
    # EP Cantate sidenote (p76) - no "1." in print
    ("1. Cantate Domino. Psal: 98.", "Cantate Domino. Psal: 98."),
    # EP Deus misereatur sidenote (p77)
    ("Deus miscreatur. Psla: 67", "Deus misereatur. Psal: 67."),
    # EP Deus misereatur v2 (p77) - transcription dropped "vpon earth : thy"
    ("That thy way may be known saving health among all nations.",
     "That thy way may be known vpon earth : thy saving health among all nations."),
    # EP King's prayer (p80) - "all", not "aS"
    ("vanquish and overcome aS his enemies", "vanquish and overcome all his enemies"),
    # EP versicle (p79) - no asterisk in print
    ("O Lord save the King*.", "O Lord save the King."),
    # EP Royal Family prayer (p80)
    ("Allnighty God the fountaine", "Almighty God the fountaine"),
    # Benedictus sidenote spacing (p66)
    ("Benedictus. S. Luke, 1.68", "Benedictus. S. Luke, 1. 68"),
]

def apply_corrections(text):
    for old, new in CORRECTIONS:
        if old in text:
            text = text.replace(old, new)
    return text

# ----------------------------------------------------------------------------
# Nesting-aware wikitext helpers
# ----------------------------------------------------------------------------
def split_top(s, sep='|'):
    parts, depth, cur = [], 0, []
    i = 0
    while i < len(s):
        c = s[i]
        if s.startswith('{{', i):
            depth += 1; cur.append('{{'); i += 2
        elif s.startswith('}}', i):
            depth -= 1; cur.append('}}'); i += 2
        elif s.startswith('[[', i):
            depth += 1; cur.append('[['); i += 2
        elif s.startswith(']]', i):
            depth -= 1; cur.append(']]'); i += 2
        elif c == sep and depth == 0:
            parts.append(''.join(cur)); cur = []; i += 1
        else:
            cur.append(c); i += 1
    parts.append(''.join(cur))
    return parts

def find_matching(s, start, open_tok, close_tok):
    depth, i = 0, start
    while i < len(s):
        if s.startswith(open_tok, i):
            depth += 1; i += len(open_tok)
        elif s.startswith(close_tok, i):
            depth -= 1; i += len(close_tok)
            if depth == 0:
                return i
        else:
            i += 1
    return -1

def render_inline(s):
    """Resolve templates/links to plain text, nesting-aware."""
    # convert <br> and </br> to space first
    s = re.sub(r'</?br\s*/?>', ' ', s, flags=re.I)
    # strip blockquote tags (indentation only)
    s = re.sub(r'</?blockquote[^>]*>', '', s, flags=re.I)
    # HTML entities -> text
    import html as ihtml
    s = s.replace('&nbsp;', ' ')
    # mark italic spans
    s = s.replace("''", '\x01')
    out, i = [], 0
    in_ital = False
    while i < len(s):
        if s[i] == '\x01':
            # toggle italic; emit marker
            out.append('\x01' if not in_ital else '\x02')
            in_ital = not in_ital
            i += 1
        elif s.startswith('{{', i):
            end = find_matching(s, i, '{{', '}}')
            if end == -1:
                out.append(s[i:]); break
            inner = s[i+2:end-2]
            out.append(render_template(inner))
            i = end
        elif s.startswith('[[', i):
            end = find_matching(s, i, '[[', ']]')
            if end == -1:
                out.append(s[i:]); break
            inner = s[i+2:end-2]
            parts = split_top(inner)
            # [[target|display]] or [[target]]
            disp = parts[-1] if len(parts) > 1 else parts[0].split('#')[0].split(':')[-1]
            out.append(render_inline(disp))
            i = end
        else:
            out.append(s[i]); i += 1
    return ''.join(out)

def italic_ratio(text):
    """Fraction of non-space chars inside italic markers."""
    it = re.findall(r'\x01(.*?)\x02', text)
    it_chars = sum(len(re.sub(r'\s', '', s)) for s in it)
    total = len(re.sub(r'\s', '', text.replace('\x01', '').replace('\x02', '')))
    return (it_chars / total) if total else 0

def strip_ital_markers(text):
    return text.replace('\x01', '').replace('\x02', '')

def render_template(inner):
    parts = split_top(inner)
    name = parts[0].strip()
    args = parts[1:]
    # layout/structural templates: drop entirely
    if name in ('rule', 'br', 'nop', '-'):
        return ''
    if name in ('hi',):
        # {{hi|size|text}} or {{hi|text}} - take last arg
        return render_inline(args[-1]) if args else ''
    if name == 'gap':
        return '[...]'
    # sidenote variants: attach as sidenote (handled by caller via marker)
    if 'sidenote' in name.lower():
        return '\x00SN\x00' + render_inline(args[-1] if args else '')
    if name in ('c', 'center', 'Center'):
        return render_inline(args[-1]) if args else ''
    if name in ('larger', 'smaller', 'fine', 'x-larger'):
        t = render_inline(args[-1]) if args else ''
        # strip editorial brackets around larger initials: [O Lord] -> O Lord
        t = re.sub(r'\[([^\]]+)\]', r'\1', t)
        return t
    if name in ('dropinitial',):
        return render_inline('|'.join(args))
    if name in ('D.C.', 'dc'):
        return render_inline(args[-1]) if args else ''
    if name in ('np', 'np2', 'nind', 'indent'):
        # paragraph wrappers: join non-empty args, skipping pilcrow-only first arg
        texts = [render_inline(a) for a in args]
        texts = [t for t in texts if t.strip() not in ('', '¶', '|')]
        return ' '.join(texts)
    if name in ('block right', 'block_right', 'fqm', 'fq'):
        # block wrappers / fancy quotes: render content args
        texts = [render_inline(a) for a in args]
        # drop width/positional args
        texts = [t for t in texts if 'px' not in t and 'em' not in t]
        return ' '.join(texts)
    # section markers
    if name.startswith('section'):
        return ''
    # unknown: join args
    return render_inline('|'.join(args))

def strip_noinclude(wikitext):
    return re.sub(r'<noinclude>.*?</noinclude>', '', wikitext, flags=re.S)

def clean_text(t):
    t = strip_ital_markers(t.replace("''", ""))
    t = re.sub(r'\s+', ' ', t).strip()
    # strip leading pilcrows/quotes/colons ornaments used as typography
    t = re.sub(r'^[¶„:\s]+', '', t)
    # strip leading "U " pilcrow-typo (p75 "U Then")
    t = re.sub(r'^U (?=Then)', '', t)
    # strip running heads accidentally captured at paragraph start
    t = re.sub(r'^(Morning Prayer|Evening Prayer)\s+', '', t)
    return t.strip()

# speaker cues that appear as standalone italic lines
CUES = {
    'answer.': 'people',
    'priest.': 'priest',
    'minister.': 'minister',
}

def parse_page(path):
    wt = open(path, encoding='utf-8').read()
    wt = strip_noinclude(wt)
    blocks = []
    # split into template-top-level chunks: {{...}} blocks and text between
    i = 0
    buf = []
    def flush_buf():
        if buf:
            # split on paragraph breaks (blank lines)
            text = ''.join(buf)
            for para in re.split(r'\n\s*\n', text):
                t = clean_text(render_inline(para))
                # keep raw for classification (need italic markers)
                # store the rendered-with-markers version
                rm = re.sub(r'<section[^>]*>', '', render_inline(para))
                if clean_text(rm):
                    blocks.append(('raw', None, para))
            buf.clear()
    while i < len(wt):
        if wt.startswith('{{', i):
            end = find_matching(wt, i, '{{', '}}')
            if end == -1:
                buf.append(wt[i:]); break
            inner = wt[i+2:end-2]
            tname = split_top(inner)[0].strip()
            # inline formatting templates: render into the buffer, don't split
            if tname in ('larger', 'smaller', 'fine', 'x-larger', 'hi', 'D.C.', 'dc'):
                buf.append(render_template(inner))
            else:
                flush_buf()
                blocks.append(('tpl', inner, None))
            i = end
        else:
            buf.append(wt[i]); i += 1
    flush_buf()
    return blocks

def classify_blocks(blocks):
    """Turn (tpl|raw) blocks into (kind, speaker, text, sidenote)."""
    out = []
    pending_sn = None
    for btype, inner, rawtxt in blocks:
        if btype == 'raw':
            t_raw = render_inline(rawtxt)
            # strip section markers
            t_raw = re.sub(r'<section[^>]*>', '', t_raw)
            # extract sidenote markers
            sns = re.findall(r'\x00SN\x00(.*?)(?=\x00SN\x00|$)', t_raw)
            t_raw = re.sub(r'\x00SN\x00.*?(?=\x00SN\x00|$)', '', t_raw)
            ratio = italic_ratio(t_raw)
            t = clean_text(t_raw)
            sn = clean_text(' '.join(sns)) if sns else None
            if sn:
                # sidenote precedes its paragraph: hold pending
                pending_sn = sn
            if not t:
                continue
            low = t.lower()
            if low in CUES:
                kind, sp = 'cue', CUES[low]
            elif ratio > 0.6:
                kind, sp = 'rubric', None
            else:
                kind, sp = 'text', None
            if pending_sn:
                sn = pending_sn
                pending_sn = None
            out.append((kind, sp, t, sn))
        else:
            parts = split_top(inner)
            name = parts[0].strip()
            args = parts[1:]
            rendered = render_template(inner)
            # check for sidenote marker in rendered
            if '\x00SN\x00' in rendered:
                sn = clean_text(rendered.replace('\x00SN\x00', ''))
                # sidenote precedes the paragraph it annotates: hold as pending
                pending_sn = sn
            elif name == 'gap':
                out.append(('gap', None, '[...]', None))
            elif name in ('c', 'center', 'Center'):
                t = clean_text(rendered)
                if t:
                    low = t.lower()
                    if low in CUES:
                        out.append(('cue', CUES[low], t, None))
                    elif re.match(r'^A (Prayer|Collect)', t):
                        out.append(('heading', None, t, None))
                    else:
                        out.append(('rubric', None, t, None))
            elif name in ('rule', 'br'):
                continue
            else:
                ratio = italic_ratio(rendered)
                t = clean_text(rendered)
                if t:
                    if ratio > 0.6:
                        out.append(('rubric', None, t, None))
                    else:
                        out.append(('text', None, t, None))
    # normalize to 4-tuples
    norm = []
    for b in out:
        if len(b) == 3:
            norm.append((b[0], b[1], b[2], None))
        else:
            norm.append(b)
    return norm

def join_page_boundaries(pages_blocks):
    """Deterministic joining of text split across page boundaries.

    Handles: (a) trailing catchword-only rubric ('Then') at end of a page
    whose continuation starts the next page; (b) word-split hyphenation
    ('holy' + 'laws', 'supplications' + 'vnto thee').
    """
    # flatten with page markers
    flat = []
    for pnum, blocks in pages_blocks:
        for b in blocks:
            flat.append((pnum, b))
    out = []
    i = 0
    while i < len(flat):
        pnum, (kind, sp, text, sn) = flat[i]
        # catchword: page ends with rubric 'Then' and next page starts with 'Then ...'
        if kind == 'rubric' and text == 'Then' and i + 1 < len(flat):
            npnum, (nkind, nsp, ntext, nsn) = flat[i+1]
            if npnum != pnum and ntext.startswith('Then '):
                i += 1  # drop the catchword, keep the continuation
                continue
        # hyphenated word split: text ends with a lowercase fragment and next
        # page's text starts with the remainder (no space, lowercase)
        if kind == 'text' and i + 1 < len(flat):
            npnum, (nkind, nsp, ntext, nsn) = flat[i+1]
            if (npnum != pnum and nkind == 'text'
                    and re.search(r'[a-z]$', text)
                    and re.match(r'^[a-z]', ntext)
                    and ' ' not in text.split()[-1]):
                # join: check if concatenation forms a word (next starts lowercase,
                # current ends without punctuation)
                if re.search(r'[a-z]$', text) and not text.endswith(('-', ':')):
                    # hyphenated across lines in print: 'holy' + 'laws'
                    merged = text + ntext
                    out.append((pnum, (kind, sp, merged, sn or nsn)))
                    i += 2
                    continue
        out.append((pnum, (kind, sp, text, sn)))
        i += 1
    return [b for _, b in out]

def is_rubric_1662(text, section):
    """Heuristic: is this 1662 paragraph a rubric (instruction) vs spoken text?"""
    t = text.lower()
    # explicit instructional markers
    if re.match(r'^(then|here|and|note|¶)', t):
        # "Then the Minister shall...", "Here beginneth...", "Note that..."
        if 'shall' in t or 'note' in t or 'here' in t:
            return True
    # section headings that are rubrics
    if section == 'opening_rubric':
        # instructional unless it's the actual prayer text
        if any(k in t for k in ['shall', 'note that', 'to be said', 'to be pronounced']):
            return True
    return False

def parse_office(page_nums):
    pages = []
    for n in page_nums:
        path = os.path.join(RAW, f'ws1662_page{n:03d}.txt')
        blocks = classify_blocks(parse_page(path))
        pages.append((n, blocks))
    blocks = join_page_boundaries(pages)
    # merge bracketed larger-initials ([O Lord], [But]) with surrounding text
    # e.g. "Enter not into iudgement with thy servant" + "[O Lord]" +
    #      "for in thy sight..." -> single verse
    merged = []
    i = 0
    while i < len(blocks):
        kind, sp, text, sn = blocks[i]
        if (kind == 'text' and re.fullmatch(r'\[[^\]]+\]', text)
                and merged and merged[-1][0] == 'text'
                and i + 1 < len(blocks) and blocks[i+1][0] == 'text'):
            pk, psp, ptext, psn = merged.pop()
            nkind, nsp, ntext, nsn = blocks[i+1]
            inner = text[1:-1]
            combined = f"{ptext} {inner} {ntext}"
            # fix spacing before punctuation that the split introduced
            combined = re.sub(r'\s+([,:;.])', r'\1', combined)
            merged.append((nkind, nsp, combined, psn or nsn))
            i += 2
        else:
            merged.append((kind, sp, text, sn))
            i += 1
    blocks = merged
    # apply corrections
    fixed = []
    for kind, sp, text, sn in blocks:
        text = apply_corrections(text)
        if sn:
            sn = apply_corrections(sn)
        # drop empty
        if text or sn:
            fixed.append((kind, sp, text, sn))
    return fixed

# === from proto1928.py ===
def extract_cells(data):
    out = []
    for m in re.finditer(r'<td\s+width="400"[^>]*>', data, flags=re.I):
        depth = 1
        pos = m.end()
        tag = ''
        while depth > 0:
            nm = re.search(r'</?td\b[^>]*>', data[pos:], flags=re.I)
            if not nm:
                break
            tag = nm.group(0)
            if tag.startswith('</'):
                depth -= 1
            elif not tag.endswith('/>'):
                depth += 1
            pos += nm.end()
        out.append(data[m.end():pos - len(tag)])
    return out

def cell_to_paragraphs(cell_html):
    h = cell_html
    h = re.sub(r'</?(table|tbody)[^>]*>', '\n', h, flags=re.I)
    h = re.sub(r'<tr[^>]*>', '\n', h, flags=re.I)
    h = re.sub(r'</tr>', '', h, flags=re.I)
    h = re.sub(r'</?td[^>]*>', ' ', h, flags=re.I)
    h = re.sub(r'<p([^>]*)>', lambda m: '\n¶¶' + m.group(1) + '\n', h, flags=re.I)
    h = re.sub(r'</p>', '\n', h, flags=re.I)
    h = re.sub(r'<br\s*/?>', '\n', h, flags=re.I)
    h = re.sub(r'<hr[^>]*>', '\n', h, flags=re.I)
    h = re.sub(r'</?span[^>]*>', '', h, flags=re.I)
    h = re.sub(r'</?font[^>]*>', '', h, flags=re.I)
    h = re.sub(r'<em>', '\x01', h, flags=re.I)
    h = re.sub(r'</em>', '\x02', h, flags=re.I)
    h = re.sub(r'<i>', '\x01', h, flags=re.I)
    h = re.sub(r'</i>', '\x02', h, flags=re.I)
    h = re.sub(r'<[^>]+>', '', h)
    h = ihtml.unescape(h)
    h = h.replace('\xa0', ' ')
    paras = []
    for chunk in re.split(r'\n\s*\n', h):
        lines = [ln.strip() for ln in chunk.split('\n')]
        lines = [ln for ln in lines if ln]
        if not lines:
            continue
        buf = []
        attrs = ''
        def flush():
            if buf:
                text = ' '.join(buf)
                it = re.findall(r'\x01(.*?)\x02', text)
                it_chars = sum(len(s) for s in it)
                clean = text.replace('\x01', '').replace('\x02', '')
                clean = re.sub(r'\s+', ' ', clean).strip()
                total = len(re.sub(r'\s', '', clean))
                ratio = (it_chars / total) if total else 0
                kind = 'text'
                if total > 0 and ratio > 0.85:
                    kind = 'rubric'
                elif 'align="center"' in attrs or 'align=center' in attrs:
                    kind = 'center'
                paras.append((kind, clean))
                buf.clear()
        for ln in lines:
            if ln.startswith('¶¶'):
                flush()
                attrs = ln[2:]
                rest = ''
                if rest:
                    buf.append(rest)
            else:
                buf.append(ln)
        flush()
    return paras

# === from sections.py ===
# Controlled section vocabulary
SECTIONS_1662 = [
    'title', 'opening_rubric', 'sentence', 'exhortation', 'confession',
    'absolution', 'lords_prayer', 'versicle', 'canticle', 'creed',
    'suffrage', 'collect', 'prayer', 'grace', 'closing',
]

# (trigger_substring, section, label) in order; first match wins, applied sequentially
TRIGGERS_1662_MP = [
    ("The Order for Morning Prayer dayly", 'title', "The Order for Morning Prayer"),
    ("At the beginning of Morning Prayer", 'opening_rubric', None),
    ("When the wicked man turneth", 'sentence', None),
    ("Dearly beloved brethren", 'exhortation', None),
    ("A generall Confession", 'opening_rubric', "A generall Confession"),
    ("Almighty and most mercifull Father, We have erred", 'confession', None),
    ("The Absolution, or Remission", 'opening_rubric', "The Absolution"),
    ("Almighty God, the Father of our Lord Iesus Christ, who desireth not", 'absolution', None),
    ("Then the Minister shall kneel and say the Lords Prayer", 'opening_rubric', None),
    ("Our Father which art in heaven", 'lords_prayer', None),
    ("Then likewise he shall say", 'opening_rubric', None),
    ("open thou our lips", 'versicle', None),
    ("Then shall be said or sung this Psalm", 'opening_rubric', None),
    ("O come, let vs sing", 'canticle', "Venite"),
    ("Then shall be read distinctly", 'opening_rubric', None),
    ("We praise thee, O God", 'canticle', "Te Deum laudamus"),
    ("O all ye works of the Lord", 'canticle', "Benedicite"),
    ("Then shall be read in like manner the second Lesson", 'opening_rubric', None),
    ("Blessed be the Lord God of Israel", 'canticle', "Benedictus"),
    ("O be ioyfull in the Lord", 'canticle', "Jubilate Deo"),
    ("Then shall be sung or said the Apostles Creed", 'opening_rubric', None),
    ("I beleeve in God the Father Almighty", 'creed', "Apostles' Creed"),
    ("And after that these prayers following", 'opening_rubric', None),
    ("The Lord be with you", 'versicle', None),
    ("Then the Minister, Clerks and people shall say", 'opening_rubric', None),
    ("Then the Priest standing vp, shall say", 'opening_rubric', None),
    ("O Lord shew thy mercy vpon vs", 'suffrage', None),
    ("Then shall follow three Collects", 'opening_rubric', None),
    ("The second Collect for Peace", 'opening_rubric', "The second Collect for Peace"),
    ("O God, who art the Author of peace", 'collect', "Collect for Peace"),
    ("The third Collect for Grace", 'opening_rubric', "The third Collect for Grace"),
    ("O Lord our heavenly Father, Almighty and everlasting God, who hast safely brought vs", 'collect', "Collect for Grace"),
    ("In Quires and Places where they sing", 'opening_rubric', None),
    ("Then these five Prayers following", 'opening_rubric', None),
    ("A Prayer for the Kings Majesty", 'prayer', "A Prayer for the Kings Majesty"),
    ("O Lord our heavenly Father, High and Mighty", 'prayer', "A Prayer for the Kings Majesty"),
    ("A Prayer for", 'prayer', "A Prayer for the Royal Family"),
    ("Almighty God the fountaine of all goodness", 'prayer', "A Prayer for the Royal Family"),
    ("A Prayer for the Clergy and people", 'prayer', "A Prayer for the Clergy and people"),
    ("Almighty and everlasting God, who alone workest", 'prayer', "A Prayer for the Clergy and people"),
    ("A Prayer of Saint Chrysostome", 'prayer', "A Prayer of Saint Chrysostome"),
    ("Almighty God, who hast given vs grace", 'prayer', "A Prayer of Saint Chrysostome"),
    ("2. Corinthians 13", 'grace', "2 Corinthians 13"),
    ("The grace of our Lord Iesus Christ", 'grace', "2 Corinthians 13"),
    ("Here endeth the Order of Morning Prayer", 'closing', None),
]

TRIGGERS_1662_EP = [
    ("The Order for Evening Prayer", 'title', "The Order for Evening Prayer"),
    ("At the beginning of Evening Prayer", 'opening_rubric', None),
    ("When the wicked man turneth", 'sentence', None),
    ("Dearly beloved brethren", 'exhortation', None),
    ("A generall Confession", 'opening_rubric', "A generall Confession"),
    ("Almighty and most mercifull Father, We have erred", 'confession', None),
    ("The Absolution, or Remission", 'opening_rubric', "The Absolution"),
    ("Almighty God, the Father of our Lord Iesus Christ, who desireth not", 'absolution', None),
    ("Then the Minister shall kneel", 'opening_rubric', None),
    ("Our Father which art in heaven", 'lords_prayer', None),
    ("Then likewise he shall say", 'opening_rubric', None),
    ("open thou our lips", 'versicle', None),
    ("Then shall be said or sung this Psalm", 'opening_rubric', None),
    ("O sing vnto the Lord", 'canticle', "Cantate Domino"),
    ("Then a Lesson of the Old Testament", 'opening_rubric', None),
    ("My soul doth magnifie the Lord", 'canticle', "Magnificat"),
    ("Then a Lesson of the New Testament", 'opening_rubric', None),
    ("Lord now lettest thou thy servant", 'canticle', "Nunc dimittis"),
    ("God be mercifull vnto vs", 'canticle', "Deus misereatur"),
    ("Then shall be sung or said the Apostles Creed", 'opening_rubric', None),
    ("I beleeve in God the Father Almighty", 'creed', "Apostles' Creed"),
    ("And after that these prayers following", 'opening_rubric', None),
    ("The Lord be with you", 'versicle', None),
    ("Then the Minister, Clerks and people shall say", 'opening_rubric', None),
    ("Then the Priest standing vp, shall say", 'opening_rubric', None),
    ("O Lord shew thy mercy vpon vs", 'suffrage', None),
    ("Then shall follow three Collects", 'opening_rubric', None),
    ("The second Collect at Evening Prayer", 'opening_rubric', "The second Collect at Evening Prayer"),
    ("O God from whom all holy desires", 'collect', "Collect for Peace"),
    ("The third Collect for Aid", 'opening_rubric', "The third Collect for Aid"),
    ("Lighten our darkness wee beseech thee", 'collect', "Collect for Aid against all Perils"),
    ("In Quires and Places where they sing", 'opening_rubric', None),
    ("A Prayer for the Kings Majesty", 'prayer', "A Prayer for the Kings Majesty"),
    ("O Lord our heavenly Father, High and Mighty", 'prayer', "A Prayer for the Kings Majesty"),
    ("A Prayer for", 'prayer', "A Prayer for the Royal Family"),
    ("Almighty God the fountaine of all goodness", 'prayer', "A Prayer for the Royal Family"),
    ("A Prayer for the Clergy and people", 'prayer', "A Prayer for the Clergy and people"),
    ("Almighty and everlasting God, who alone workest", 'prayer', "A Prayer for the Clergy and people"),
    ("A Prayer of Saint Chrysostome", 'prayer', "A Prayer of Saint Chrysostome"),
    ("Almighty God, who hast given vs grace", 'prayer', "A Prayer of Saint Chrysostome"),
    ("2. Corinthians 13", 'grace', "2 Corinthians 13"),
    ("The grace of our Lord Iesus Christ", 'grace', "2 Corinthians 13"),
    ("Here endeth the Order of Evening Prayer", 'closing', None),
]

# ----------------------------------------------------------------------------
# 1928 triggers
# ----------------------------------------------------------------------------
TRIGGERS_1928_MP = [
    ("DAILY MORNING PRAYER", 'title', "The Order for Daily Morning Prayer"),
    ("The Minister shall begin the Morning Prayer", 'opening_rubric', None),
    ("THE LORD is in his holy temple", 'sentence', None),
    ("Then the Minister shall say,", 'opening_rubric', None),
    ("DEARLY beloved brethren", 'exhortation', None),
    ("Or he shall say,", 'opening_rubric', None),
    ("LET us humbly confess", 'exhortation', None),
    ("A General Confession", 'opening_rubric', "A General Confession"),
    ("ALMIGHTY and most merciful Father; We have erred", 'confession', None),
    ("Declaration of Absolution", 'opening_rubric', "The Declaration of Absolution"),
    ("ALMIGHTY God, the Father of our Lord Jesus Christ, who desireth not", 'absolution', None),
    ("Then the Minister shall kneel, and say the Lord", 'opening_rubric', None),
    ("OUR Father, who art in heaven", 'lords_prayer', None),
    ("Then likewise he shall say,", 'opening_rubric', None),
    ("O Lord, open thou our lips", 'versicle', None),
    ("Then shall be said or sung the following Canticle", 'opening_rubric', None),
    ("Venite, exultemus Domino", 'canticle', "Venite"),
    ("O COME, let us sing", 'canticle', "Venite"),
    ("Then shall follow a Portion of the PSALMS", 'opening_rubric', None),
    ("Then shall be read the First Lesson", 'opening_rubric', None),
    ("Here shall be said or sung the following Hymn", 'opening_rubric', None),
    ("Te Deum laudamus", 'canticle', "Te Deum laudamus"),
    ("WE praise thee, O God", 'canticle', "Te Deum laudamus"),
    ("Or this Canticle", 'opening_rubric', None),
    ("Benedictus es Domine", 'canticle', "Benedictus es Domine"),
    ("BLESSED art thou, O Lord God of our fathers", 'canticle', "Benedictus es Domine"),
    ("Or this,", 'opening_rubric', None),
    ("Benedicite, omnia opera Domini", 'canticle', "Benedicite"),
    ("O ALL ye Works of the Lord", 'canticle', "Benedicite"),
    ("Then shall be read, in like manner, the Second Lesson", 'opening_rubric', None),
    ("And after that shall be sung or said the Hymn following", 'opening_rubric', None),
    ("Benedictus. St. Luke", 'canticle', "Benedictus"),
    ("BLESSED be the Lord God of Israel", 'canticle', "Benedictus"),
    ("Or this Psalm", 'opening_rubric', None),
    ("Jubilate Deo", 'canticle', "Jubilate Deo"),
    ("O BE joyful in the LORD", 'canticle', "Jubilate Deo"),
    ("Then shall be said the Apostles", 'opening_rubric', None),
    ("I BELIEVE in God the Father Almighty", 'creed', "Apostles' Creed"),
    ("Or the Creed commonly called the Nicene", 'opening_rubric', "Nicene Creed"),
    ("I BELIEVE in one God", 'creed', "Nicene Creed"),
    ("And after that, these Prayers following", 'opening_rubric', None),
    ("The Lord be with you", 'suffrage', None),
    ("Here, if it hath not already been said, shall follow the Lord's Prayer", 'opening_rubric', None),
    ("O Lord, show thy mercy upon us", 'suffrage', None),
    ("Then shall follow the Collect for the Day", 'opening_rubric', None),
    ("A Collect for Peace", 'collect', "A Collect for Peace"),
    ("O GOD, who art the author of peace", 'collect', "A Collect for Peace"),
    ("A Collect for Grace", 'collect', "A Collect for Grace"),
    ("O LORD, our heavenly Father, Almighty and everlasting God, who hast safely brought us", 'collect', "A Collect for Grace"),
    ("The following Prayers shall be omitted here", 'opening_rubric', None),
    ("A Prayer for The President", 'prayer', "A Prayer for The President of the United States"),
    ("O LORD, our heavenly Father, the high and mighty Ruler", 'prayer', "A Prayer for The President of the United States"),
    ("Or this", 'opening_rubric', None),
    ("O LORD our Governor", 'prayer', "A Prayer for The President of the United States"),
    ("A Prayer for the Clergy and People", 'prayer', "A Prayer for the Clergy and People"),
    ("ALMIGHTY and everlasting God, from whom cometh every good", 'prayer', "A Prayer for the Clergy and People"),
    ("A Prayer for all Conditions of Men", 'prayer', "A Prayer for all Conditions of Men"),
    ("O GOD, the Creator and Preserver", 'prayer', "A Prayer for all Conditions of Men"),
    ("A General Thanksgiving", 'prayer', "A General Thanksgiving"),
    ("ALMIGHTY God, Father of all mercies", 'prayer', "A General Thanksgiving"),
    ("A Prayer of St. Chrysostom", 'prayer', "A Prayer of St. Chrysostom"),
    ("ALMIGHTY God, who hast given us grace", 'prayer', "A Prayer of St. Chrysostom"),
    ("2 Cor. xiii. 14", 'grace', "2 Corinthians 13"),
    ("THE grace of our Lord Jesus Christ", 'grace', "2 Corinthians 13"),
    ("Here endeth the Order of Morning Prayer", 'closing', None),
]

TRIGGERS_1928_EP = [
    ("DAILY EVENING PRAYER", 'title', "The Order for Daily Evening Prayer"),
    ("The Minister shall begin the Evening Prayer", 'opening_rubric', None),
    ("THE LORD is in his holy temple", 'sentence', None),
    ("LET us humbly confess", 'exhortation', None),
    ("Or else he shall say as followeth", 'opening_rubric', None),
    ("DEARLY beloved brethren", 'exhortation', None),
    ("A General Confession", 'opening_rubric', "A General Confession"),
    ("ALMIGHTY and most merciful Father; We have erred", 'confession', None),
    ("Declaration of Absolution", 'opening_rubric', "The Declaration of Absolution"),
    ("ALMIGHTY God, the Father of our Lord Jesus Christ, who desireth not", 'absolution', None),
    ("Or this", 'opening_rubric', None),
    ("THE Almighty and Merciful God grant you", 'absolution', None),
    ("Then the Minister shall kneel, and say the Lord", 'opening_rubric', None),
    ("OUR Father, who art in heaven", 'lords_prayer', None),
    ("Then likewise he shall say,", 'opening_rubric', None),
    ("O Lord, open thou our lips", 'versicle', None),
    # EP canticles: Magnificat, Cantate Domino, Nunc dimittis, Deus misereatur
    ("Magnificat", 'canticle', "Magnificat"),
    ("MY soul doth magnify the Lord", 'canticle', "Magnificat"),
    ("Cantate Domino", 'canticle', "Cantate Domino"),
    ("O SING unto the LORD a new song", 'canticle', "Cantate Domino"),
    ("Nunc dimittis", 'canticle', "Nunc dimittis"),
    ("LORD, now lettest thou thy servant depart in peace", 'canticle', "Nunc dimittis"),
    ("Deus misereatur", 'canticle', "Deus misereatur"),
    ("GOD be merciful unto us", 'canticle', "Deus misereatur"),
    ("Then shall be said the Apostles", 'opening_rubric', None),
    ("I BELIEVE in God the Father Almighty", 'creed', "Apostles' Creed"),
    ("Or the Creed commonly called the Nicene", 'opening_rubric', "Nicene Creed"),
    ("I BELIEVE in one God", 'creed', "Nicene Creed"),
    ("And after that, these Prayers following", 'opening_rubric', None),
    ("The Lord be with you", 'suffrage', None),
    ("O Lord, show thy mercy upon us", 'suffrage', None),
    ("Then shall follow the Collect for the Day", 'opening_rubric', None),
    ("A Collect for Peace", 'collect', "A Collect for Peace"),
    ("O GOD, from whom all holy desires", 'collect', "A Collect for Peace"),
    ("A Collect for Aid against all Perils", 'collect', "A Collect for Aid against all Perils"),
    ("LIGHTEN our darkness", 'collect', "A Collect for Aid against all Perils"),
    ("A Prayer for The President", 'prayer', "A Prayer for The President of the United States"),
    ("O LORD, our heavenly Father, the high and mighty Ruler", 'prayer', "A Prayer for The President of the United States"),
    ("A Prayer for the Clergy and People", 'prayer', "A Prayer for the Clergy and People"),
    ("ALMIGHTY and everlasting God, from whom cometh every good", 'prayer', "A Prayer for the Clergy and People"),
    ("A Prayer for all Conditions of Men", 'prayer', "A Prayer for all Conditions of Men"),
    ("O GOD, the Creator and Preserver", 'prayer', "A Prayer for all Conditions of Men"),
    ("A General Thanksgiving", 'prayer', "A General Thanksgiving"),
    ("ALMIGHTY God, Father of all mercies", 'prayer', "A General Thanksgiving"),
    ("A Prayer of St. Chrysostom", 'prayer', "A Prayer of St. Chrysostom"),
    ("ALMIGHTY God, who hast given us grace", 'prayer', "A Prayer of St. Chrysostom"),
    ("2 Cor. xiii. 14", 'grace', "2 Corinthians 13"),
    ("THE grace of our Lord Jesus Christ", 'grace', "2 Corinthians 13"),
    ("Here endeth the Order of Evening Prayer", 'closing', None),
]
def assign_sections(blocks, triggers):
    """Assign (section, label) to each block. Returns list of (section, label, kind, speaker, text, sidenote).
    
    A trigger matches if the block text starts with the trigger phrase
    (after stripping leading punctuation/whitespace). This avoids false
    matches when a rubric merely quotes a later phrase.
    """
    out = []
    cur_section, cur_label = 'opening_rubric', None
    ti = 0
    for kind, sp, text, sn in blocks:
        # normalize for startswith matching (case-insensitive)
        t_start = re.sub(r'^[^\w]+', '', text).lower()
        best = None
        for j in range(ti, len(triggers)):
            trig = triggers[j][0].lower()
            if t_start.startswith(trig):
                best = j
                break
        if best is not None:
            new_section = triggers[best][1]
            # reset label on section change unless trigger provides one
            if new_section != cur_section:
                cur_label = None
            cur_section = new_section
            if triggers[best][2] is not None:
                cur_label = triggers[best][2]
            ti = best + 1
        out.append((cur_section, cur_label, kind, sp, text, sn))
    return out



sys.path.insert(0, '/tmp/bcpcheck')
from bcp1662 import parse_office as parse_1662
from proto1928 import extract_cells, cell_to_paragraphs
from sections import (assign_sections, TRIGGERS_1662_MP, TRIGGERS_1662_EP,
                      TRIGGERS_1928_MP, TRIGGERS_1928_EP)

# ----------------------------------------------------------------------------
# 1928 corrections (Justus transcription -> IA 1928 scan OCR verified)
# ----------------------------------------------------------------------------
CORR_1928 = [
    ("acknOwledge", "acknowledge"),
    ("arid Mediator", "and Mediator"),
    ("according to. their", "according to their"),
    ("hearts may he unfeignedly", "hearts may be unfeignedly"),
    ("tile light of his countenance", "the light of his countenance"),
    ("third day lie rose", "third day he rose"),
    ("was .crucified", "was crucified"),
]

def apply_1928_corrections(text):
    for old, new in CORR_1928:
        text = text.replace(old, new)
    return text

# ----------------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  edition TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  source_url TEXT NOT NULL,
  retrieved_utc TEXT NOT NULL,
  rights_basis TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS liturgy (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  office TEXT NOT NULL,
  section TEXT NOT NULL,
  label TEXT,
  seq INTEGER NOT NULL,
  speaker TEXT,
  kind TEXT NOT NULL,
  text TEXT NOT NULL,
  sidenote TEXT,
  UNIQUE (source_id, office, seq)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_liturgy_unique ON liturgy(source_id, office, seq);
"""

SOURCES = [
    ('bcp1662', 'Book of Common Prayer, 1662 (1892 Pickering reprint)',
     'https://en.wikisource.org/wiki/Book_of_Common_Prayer_(1892)',
     '2026-09-20',
     'Public domain. First published 1662; the 1892 Pickering edition is a '
     'verbatim reprint of the manuscript annexed to the Act of Uniformity 1662.'),
    ('bcp1928', 'Book of Common Prayer, 1928 (US Standard)',
     'http://justus.anglican.org/resources/bcp/1928/MP.htm (via Wayback Machine)',
     '2026-09-20',
     'Public domain in the US. First published 1928; copyright expired '
     '2024-01-01 (95-year term). Transcription corrected against the 1928 '
     'Standard Book scan (Internet Archive).'),
]

# ----------------------------------------------------------------------------
# 1928 parsing
# ----------------------------------------------------------------------------
def parse_1928(which):
    fn = os.path.join(RAW1928, 'mp.htm' if which == 'mp' else 'ep.htm')
    data = open(fn, encoding='utf-8').read()
    cells = extract_cells(data)
    blocks = []
    for cell in cells:
        for kind, text in cell_to_paragraphs(cell):
            text = apply_1928_corrections(text)
            if not text.strip():
                continue
            # strip leading pilcrow ornament
            text = re.sub(r'^¶\s*', '', text).strip()
            if not text:
                continue
            # speaker detection for 1928: "Answer." / "Minister." prefixes
            speaker = None
            m = re.match(r'^(Answer|Minister|Priest)\.\s+(.*)$', text, re.S)
            if m:
                speaker = {'Answer': 'people', 'Minister': 'minister', 'Priest': 'priest'}[m.group(1)]
                text = m.group(2).strip()
                kind = 'text'  # spoken
            blocks.append((kind, speaker, text, None))
    return blocks

def main():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    # sources
    for edition, title, url, retrieved, rights in SOURCES:
        con.execute(
            "INSERT INTO sources (edition, title, source_url, retrieved_utc, rights_basis) "
            "VALUES (?, ?, ?, ?, ?)",
            (edition, title, url, retrieved, rights))
    src_id = {e: r[0] for e, r in
              ((row[1], row) for row in con.execute("SELECT id, edition FROM sources"))}
    # fix: build dict properly
    src_id = {}
    for sid, edition in con.execute("SELECT id, edition FROM sources"):
        src_id[edition] = sid

    # 1662
    for which, pages, trig, office in [
            ('mp', list(range(57, 72)), TRIGGERS_1662_MP, 'morning_prayer'),
            ('ep', list(range(72, 82)), TRIGGERS_1662_EP, 'evening_prayer')]:
        blocks = parse_office(pages)
        assigned = assign_sections(blocks, trig)
        seq = 0
        for sec, label, kind, sp, text, sn in assigned:
            seq += 1
            con.execute(
                "INSERT INTO liturgy (source_id, office, section, label, seq, speaker, kind, text, sidenote) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (src_id['bcp1662'], office, sec, label, seq, sp, kind, text, sn))
        print(f"bcp1662 {office}: {seq} rows")

    # 1928
    for which, trig, office in [
            ('mp', TRIGGERS_1928_MP, 'morning_prayer'),
            ('ep', TRIGGERS_1928_EP, 'evening_prayer')]:
        blocks = parse_1928(which)
        assigned = assign_sections(blocks, trig)
        seq = 0
        for sec, label, kind, sp, text, sn in assigned:
            seq += 1
            con.execute(
                "INSERT INTO liturgy (source_id, office, section, label, seq, speaker, kind, text, sidenote) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (src_id['bcp1928'], office, sec, label, seq, sp, kind, text, sn))
        print(f"bcp1928 {office}: {seq} rows")

    con.commit()

    # verification
    print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
    for edition in ('bcp1662', 'bcp1928'):
        for office in ('morning_prayer', 'evening_prayer'):
            n = con.execute(
                "SELECT COUNT(*) FROM liturgy l JOIN sources s ON l.source_id = s.id "
                "WHERE s.edition = ? AND l.office = ?",
                (edition, office)).fetchone()[0]
            print(f"  {edition} {office}: {n}")
    # controlled vocabulary check
    secs = sorted(r[0] for r in con.execute("SELECT DISTINCT section FROM liturgy"))
    print("sections:", ", ".join(secs))
    # leak check
    leaks = con.execute(
        "SELECT COUNT(*) FROM liturgy WHERE text LIKE '%<%' OR text LIKE '%&nbsp;%' "
        "OR text LIKE '%{{%' OR text LIKE '%}}%'").fetchone()[0]
    print("markup leaks:", leaks)
    con.close()
    print(f"wrote {DB}")

if __name__ == '__main__':
    main()
