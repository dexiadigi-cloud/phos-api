#!/usr/bin/env python3
"""Parse Matthew Henry CCEL gap chapters (23 missing from HelloAO) into structured JSON.

Sources:
  - 21 chapters: CCEL HTML pages (mhc3 Song, mhc4 Jonah, mhc5 Matthew)
  - 2 chapters: CCEL mhc2.txt plain text (2 Samuel 23-24; mhc2 HTML is broken)

Output: data/raw_v2/matthew_henry/CCEL_GAPS.json
Format per chapter: {"book": "SNG", "chapter": 1, "intro": "...",
                     "sections": [{"verse_start":..,"verse_end":..,"title":..,"text":..}, ...]}
"""
import re, html as H, json, sys, urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw_v2" / "matthew_henry"
MHC2_TXT = Path(__file__).resolve().parent.parent / "data" / "raw_v2" / "matthew_henry" / "mhc2_ccel.txt"

ROMAN = {1:"i",2:"ii",3:"iii",4:"iv",5:"v",6:"vi",7:"vii",8:"viii",9:"ix",10:"x",
11:"xi",12:"xii",13:"xiii",14:"xiv",15:"xv",16:"xvi",17:"xvii",18:"xviii",19:"xix",
20:"xx",21:"xxi",22:"xxii",23:"xxiii",24:"xxiv",25:"xxv",26:"xxvi",27:"xxvii",
28:"xxviii",29:"xxix",30:"xxx"}

GAPS_HTML = [
    ("SNG", n, "mhc3", "Song") for n in range(1, 9)
] + [
    ("JON", n, "mhc4", "Jonah") for n in range(2, 5)
] + [
    ("MAT", n, "mhc5", "Matt") for n in range(19, 29)
]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == 2: raise
    raise RuntimeError("unreachable")

def clean_text(html_frag):
    t = re.sub(r"<br\s*/?>", "\n", html_frag, flags=re.I)
    t = re.sub(r"</p\s*>", "\n\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = H.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n[ \t]+", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def parse_ver_refs(summary):
    """Extract ordered verse ranges from summary.
    Handles: 'ver. 1', 'ver. 1-7', 'ver. 1, 2', 'ver. 16, 17', 'vv. 3-5'."""
    refs = []
    # Match "ver." or "vv." followed by numbers, ranges, comma lists
    for m in re.finditer(r"v{1,2}\.\s*(\d+(?:\s*[-–,]\s*\d+)*)", summary):
        part = m.group(1)
        nums = []
        for tok in re.split(r"[,\s]+", part):
            tok = tok.strip("–-")
            if not tok: continue
            if "–" in tok or "-" in tok:
                a, b = re.split(r"[–-]", tok)
                nums.append((int(a), int(b)))
            else:
                nums.append((int(tok), int(tok)))
        if nums:
            # merge into single range from first start to last end
            refs.append((nums[0][0], nums[-1][1]))
    return refs

def assign_ranges(sections, refs, max_verse):
    """Assign verse ranges to sections using summary refs in order.
    - If more refs than sections: extra refs merge into the last section.
    - If fewer refs than sections: remaining sections split the remainder.
    - Last section always extends to max_verse."""
    n = len(sections)
    out = []
    if not refs:
        # even split
        for i, sec in enumerate(sections):
            vs = (out[-1]["verse_end"] + 1) if out else 1
            ve = max_verse if i == n - 1 else min(max_verse, vs + max(0, (max_verse // n) - 1))
            out.append({"verse_start": vs, "verse_end": ve,
                        "title": sec["title"], "text": sec["text"]})
        return out
    # Assign refs to sections; if more refs than sections, merge extras into last
    # If fewer refs, distribute remainder
    assigned = []
    for i in range(n):
        if i < len(refs):
            vs, ve = refs[i]
        else:
            vs = assigned[-1][1] + 1 if assigned else 1
            ve = vs  # placeholder
        assigned.append([vs, ve])
    # Merge extra refs into last section
    if len(refs) > n:
        assigned[-1][1] = refs[-1][1]
    # Last section extends to max_verse
    assigned[-1][1] = max_verse
    # Fix overlaps/inversions: ensure strictly increasing
    for i in range(1, n):
        if assigned[i][0] <= assigned[i-1][1]:
            assigned[i][0] = assigned[i-1][1] + 1
        if assigned[i][1] < assigned[i][0]:
            assigned[i][1] = assigned[i][0]
    # First section starts at 1 (MH chapters always start at v1)
    if assigned[0][0] != 1:
        assigned[0][0] = 1
    for i, sec in enumerate(sections):
        vs, ve = assigned[i]
        out.append({"verse_start": vs, "verse_end": ve,
                    "title": sec["title"], "text": sec["text"]})
    return out

def parse_html_chapter(book, ch, vol, slug, max_verse):
    roman = ROMAN[ch + 1]
    url = f"https://ccel.org/ccel/henry/{vol}/{vol}.{slug}.{roman}.html"
    html_text = get(url)
    m = re.search(r'<div[^>]*class="book-content"[^>]*>(.*?)<div[^>]*class="content-foot"',
                  html_text, re.S)
    if not m:
        raise RuntimeError(f"book-content not found: {url}")
    c = m.group(1)
    # intro = first <p class="intro">
    intro = ""
    mi = re.search(r'<p class="intro"[^>]*>(.*?)</p>', c, re.S)
    if mi: intro = clean_text(mi.group(1))
    # sections split by <h4>
    parts = re.split(r"<h4[^>]*>(.*?)</h4>", c, flags=re.S)
    raw_sections = []
    for i in range(1, len(parts), 2):
        title = clean_text(parts[i])
        body = clean_text(parts[i + 1]) if i + 1 < len(parts) else ""
        if body:
            raw_sections.append({"title": title, "text": body})
    assigned = assign_by_leading_verse(raw_sections, max_verse)
    return {"book": book, "chapter": ch, "intro": intro,
            "sections": assigned, "source_url": url}

def leading_verse(text):
    """Extract the verse number at the start of a section's text."""
    m = re.match(r"\s*(\d+)\s+[A-Z\"“]", text)
    if m: return int(m.group(1))
    return None

def assign_by_leading_verse(raw_sections, max_verse):
    """Assign verse ranges from the leading verse number of each section's text.
    MH sections begin by quoting the verse(s) they expound."""
    starts = []
    for sec in raw_sections:
        v = leading_verse(sec["text"])
        if v is None:
            raise RuntimeError(f"no leading verse in section: {sec['title'][:50]}")
        starts.append(v)
    # validate strictly increasing
    for i in range(1, len(starts)):
        if starts[i] <= starts[i-1]:
            raise RuntimeError(f"verse starts not increasing: {starts}")
    out = []
    for i, sec in enumerate(raw_sections):
        vs = starts[i]
        ve = (starts[i+1] - 1) if i + 1 < len(starts) else max_verse
        out.append({"verse_start": vs, "verse_end": ve,
                    "title": sec["title"], "text": sec["text"]})
    return out

def parse_txt_chapter(book, ch, start_line, end_line, max_verse):
    """Parse 2SA from mhc2.txt. Sections are the '(b. c. XXXX.)' headers;
    verse ranges come from each section's leading verse number."""
    lines = MHC2_TXT.read_text(encoding="utf-8", errors="replace").splitlines()
    chunk = "\n".join(lines[start_line - 1:end_line])
    # Main section headers end with "(b. c. XXXX.)"
    header_re = re.compile(r"^([A-Z][A-Za-z ,;:'()0-9.\-–&]*\(b\. c\. \d+\.\))\s*$")
    intro_lines, raw_sections = [], []
    cur_title, cur_buf = None, []
    in_intro = True
    for ln in chunk.splitlines():
        s = ln.strip()
        mh = header_re.match(s)
        if mh and in_intro:
            in_intro = False
            cur_title = mh.group(1)
            cur_buf = []
            continue
        if mh and not in_intro:
            raw_sections.append({"title": cur_title,
                                 "text": re.sub(r"\n{3,}", "\n\n", "\n".join(cur_buf)).strip()})
            cur_title = mh.group(1)
            cur_buf = []
            continue
        if in_intro:
            intro_lines.append(ln)
        else:
            cur_buf.append(ln)
    if cur_title:
        raw_sections.append({"title": cur_title,
                             "text": re.sub(r"\n{3,}", "\n\n", "\n".join(cur_buf)).strip()})
    # Clean intro: drop CHAP heading and spaced book titles
    intro_text = "\n".join(intro_lines)
    intro_text = re.sub(r"(?m)^\s*CHAP\.\s+[IVX]+\.\s*$", "", intro_text)
    intro_text = re.sub(r"(?m)^\s*(?:[A-Z]\s+){2,}[A-Z]\.?\s*$", "", intro_text)
    intro_text = re.sub(r"\n{3,}", "\n\n", intro_text).strip()
    assigned = assign_by_leading_verse(raw_sections, max_verse)
    return {"book": book, "chapter": ch, "intro": intro_text,
            "sections": assigned, "source": "ccel mhc2.txt"}

def main():
    # KJV max verses for gap chapters
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
    import db as dbmod, parser as parsemod
    MANUAL_ALIASES = {"SNG": "Song of Songs"}
    def canon(abbrev):
        r = parsemod.resolve_book(abbrev)
        if r: return r
        return MANUAL_ALIASES[abbrev]
    bounds = dbmod.get_bounds("KJV")
    result = {"_meta": {
        "source": "Christian Classics Ethereal Library (ccel.org)",
        "work": "Matthew Henry, Commentary on the Whole Bible (6 vols)",
        "retrieval_date": "2026-09-20",
        "note": "Gap-fill for 23 chapters missing from HelloAO matthew-henry API",
    }}
    # 21 HTML chapters
    for book, ch, vol, slug in GAPS_HTML:
        cbook = canon(book)
        maxv = bounds[cbook]["max_verse"][ch]
        print(f"[{book} {ch}] fetching...", flush=True)
        result[f"{book}_{ch}"] = parse_html_chapter(book, ch, vol, slug, maxv)
    # 2 Samuel 23-24 from mhc2.txt (line boundaries verified 2026-09-20)
    for book, ch, s, e in [("2SA", 23, 48305, 48792), ("2SA", 24, 48793, 49347)]:
        cbook = canon(book)
        maxv = bounds[cbook]["max_verse"][ch]
        print(f"[{book} {ch}] parsing mhc2.txt...", flush=True)
        result[f"{book}_{ch}"] = parse_txt_chapter(book, ch, s, e, maxv)
    out = RAW / "CCEL_GAPS.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {out} ({len(result)-1} chapters)")

if __name__ == "__main__":
    main()
