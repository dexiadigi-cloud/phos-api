#!/usr/bin/env python3
"""Dump raw TSK cross-ref text for a chapter (independent of ingest script)."""
import struct, zlib, re, sys
sys.path.insert(0, '.')
from api import parser as P

def load_blocks():
    base = 'data/raw_v2/tsk/TSK_raw/modules/comments/zcom/tsk'
    out = []
    for prefix in ('ot', 'nt'):
        bzs = open(f'{base}/{prefix}.bzs','rb').read()
        bzz = open(f'{base}/{prefix}.bzz','rb').read()
        n = len(bzs)//12
        for i in range(n):
            o,s,u = struct.unpack('<III', bzs[i*12:(i+1)*12])
            out.append(zlib.decompress(bzz[o:o+s]).decode('utf-8','replace'))
    return out

BOOK_ABBR = {
    'Genesis':'Ge','Exodus':'Ex','Leviticus':'Le','Numbers':'Nu','Deuteronomy':'De',
    'Joshua':'Jos','Judges':'Jud','Ruth':'Ru','1 Samuel':'1Sa','2 Samuel':'2Sa',
    '1 Kings':'1Ki','2 Kings':'2Ki','1 Chronicles':'1Ch','2 Chronicles':'2Ch',
    'Ezra':'Ezr','Nehemiah':'Ne','Esther':'Es','Job':'Job','Psalms':'Ps',
    'Proverbs':'Pr','Ecclesiastes':'Ec','Song of Songs':'So','Isaiah':'Isa',
    'Jeremiah':'Jer','Lamentations':'La','Ezekiel':'Eze','Daniel':'Da',
    'Hosea':'Ho','Joel':'Joe','Amos':'Am','Obadiah':'Ob','Jonah':'Jon',
    'Micah':'Mic','Nahum':'Na','Habakkuk':'Hab','Zephaniah':'Zep',
    'Haggai':'Hag','Zechariah':'Zec','Malachi':'Mal','Matthew':'Mt',
    'Mark':'Mr','Luke':'Lu','John':'Joh','Acts':'Ac','Romans':'Ro',
    '1 Corinthians':'1Co','2 Corinthians':'2Co','Galatians':'Ga',
    'Ephesians':'Eph','Philippians':'Php','Colossians':'Col',
    '1 Thessalonians':'1Th','2 Thessalonians':'2Th','1 Timothy':'1Ti',
    '2 Timothy':'2Ti','Titus':'Tit','Philemon':'Phm','Hebrews':'Heb',
    'James':'Jas','1 Peter':'1Pe','2 Peter':'2Pe','1 John':'1Jo',
    '2 John':'2Jo','3 John':'3Jo','Jude':'Jude','Revelation':'Re',
}

if __name__ == '__main__':
    book, chap = sys.argv[1], int(sys.argv[2])
    books = load_blocks()
    bi = P.CANONICAL_BOOKS.index(book)
    text = books[bi]
    abbr = BOOK_ABBR[book]
    # find chapter start and end
    m1 = re.search(rf'<scripRef passage="{abbr} {chap}:\d+">', text)
    # next chapter
    m2 = re.search(rf'<scripRef passage="{abbr} {chap+1}:\d+">', text)
    if not m1:
        print(f"No marker for {book} {chap}")
        sys.exit(1)
    start = m1.start()
    end = m2.start() if m2 else len(text)
    chunk = text[start:end]
    # find xref section (after triple br or after outline)
    tb = re.search(r'<br />\s*<br />\s*<br />', chunk)
    if tb:
        xref = chunk[tb.end():tb.end()+8000]
    else:
        xref = chunk[:8000]
    print(xref)
