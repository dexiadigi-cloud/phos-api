# Weymouth NT (WEYMOUTH) - batch-3 ingest report

Date: 2026-09-20. Worker: Phos ingestion worker (subagent).

## Provenance verdict

**PASS - cleared for commercial use.** Source: Project Gutenberg per-book
ebooks 8828-8854 ("Weymouth New Testament in Modern Speech", one ebook per
NT book), downloaded 2026-09-20 from
`https://www.gutenberg.org/ebooks/<id>.txt.utf-8`.

- Each ebook page carries the metadata field
  `Copyright: Public domain in the USA.` (verified on ebooks 8828, 8832;
  catalog classification identical across all 27).
- Each file header quotes the Gutenberg terms verbatim: "This eBook is for
  the use of anyone anywhere in the United States and most other parts of
  the world at no cost and with almost no restrictions whatsoever. You may
  copy it, give it away or re-use it under the terms of the Project
  Gutenberg License included with this eBook or online at
  www.gutenberg.org."
- Edition note: the Gutenberg files transcribe the **Third Edition 1913**
  (posthumous, prepared for the press by Ernest Hampden-Cook; Weymouth
  died 1902), not the 1903 first edition. Both are PD in the US by age
  (pre-1923); the third edition is the form Gutenberg digitized and the
  form most widely distributed. Recorded in PROVENANCE.md so no one
  mistakes it for a first-edition claim.
- The sacred-texts.com index
  (https://www.sacred-texts.com/bib/wey/index.htm) states the same basis
  ("This text is in the public domain in the US because it was published
  prior to 1923") but its HTTPS endpoint dropped connections through this
  network path, so it was not used as a source; Gutenberg was.
- SHA-256 hashes of all 27 downloaded files: recorded in
  `data/raw_v2/weymouth/manifest.json` and in
  `data/raw_v2/weymouth/PROVENANCE.md`.

Full provenance: [PROVENANCE.md](../data/raw_v2/weymouth/PROVENANCE.md).

## Source anomaly (documented, corrected)

`pg8830.txt` (Luke), line 1301, mislabels the verse between 008:022 and
008:024 as "002:023" ("During the passage He fell asleep, and there came
down a squall of wind on the Lake..."). This is Luke 8:23, the
calming-of-the-storm verse; the genuine Luke 2:23 (Exodus quotation)
appears at line 365. The typo is in Gutenberg's transcription. The parser
(`scripts/parse_weymouth.py`, CORRECTIONS table) remaps exactly this one
occurrence to (Luke, 8, 23); the raw file is kept byte-identical and the
correction is documented in PROVENANCE.md. After correction: zero
duplicate (book, chapter, verse) keys.

## Row counts (staged)

Staging DB: `data/staging/weymouth.db`, table `verses`
(translation TEXT, book TEXT, book_order INTEGER, chapter INTEGER,
verse INTEGER, text TEXT). All 7,957 rows have translation='WEYMOUTH'.
Book names and 0-based book_order follow the canonical table from
`scripts/ingest_translations_batch2.py` (Matthew=39 .. Revelation=65).
Code check: no existing "WEYMOUTH" anywhere in code or docs; no collision
with AKJV, ASV, BBE, BSB, DARBY, DRB, GENEVA, KJV, OEB, WEB, YLT.

| Book | Rows | Book | Rows | Book | Rows |
|------|------|------|------|------|------|
| Matthew | 1071 | Galatians | 149 | Hebrews | 303 |
| Mark | 678 | Ephesians | 155 | James | 108 |
| Luke | 1151 | Philippians | 104 | 1 Peter | 105 |
| John | 879 | Colossians | 95 | 2 Peter | 61 |
| Acts | 1007 | 1 Thessalonians | 89 | 1 John | 105 |
| Romans | 433 | 2 Thessalonians | 47 | 2 John | 13 |
| 1 Corinthians | 437 | 1 Timothy | 113 | 3 John | 14 |
| 2 Corinthians | 257 | 2 Timothy | 83 | Jude | 25 |
| | | Titus | 46 | Revelation | 404 |
| | | Philemon | 25 | | |

Total: **7,957 rows, 27 books** (complete NT; no OT books; no partial
coverage to flag).

## Deterministic verification (seed 20260920)

Script: `data/staging/verify_weymouth.py`. It independently re-extracts
verse text from the raw files (separate code path from the parser),
samples 50 keys with `random.Random(20260920)`, compares
character-for-character against staged rows, checks full key-set
agreement (raw labels vs staged keys), and checks 3 hand-transcribed
spot-check verses.

Results (full log: `data/staging/weymouth-VERIFY.md`):

- 50/50 seeded samples PASS, char-for-char raw -> staged.
- 3/3 hand-transcribed spot checks PASS:
  - John 3:16: "For so greatly did God love the world that He gave His
    only Son, that every one who trusts in Him may not perish but may
    have the Life of Ages."
  - John 1:1: "In the beginning was the Word, and the Word was with God,
    and the Word was God."
  - Luke 8:23 (exercises the source-typo correction): "During the passage
    He fell asleep, and there came down a squall of wind on the Lake, so
    that the boat began to fill and they were in deadly peril."
- Key-set agreement: staged keys exactly equal raw verse labels
  (after the one documented correction). Zero duplicates.
- Book count: exactly 27 distinct books; 0 rows with book_order < 39
  (no OT contamination).
- `PRAGMA integrity_check`: ok.
- **OVERALL: PASS**

## Test fragment

`api/tests/batch3_frag_weymouth.py` (not collected by pytest until
assembled). Contains:

- `EXPECTED_WEYMOUTH_COUNT = 7957` asserted against
  `db.translation_counts()`.
- 3 spot-check verses (John 3:16, John 1:1, Luke 8:23 with distinctive
  Weymouth markers).
- `test_weymouth_books_exactly_27_nt`: mirrors the OEB pattern from
  `test_translations_batch2.py` - exactly the 27 NT books in order
  39-65, Genesis/Malachi absent.
- `test_weymouth_per_book_counts_sane`: per-book row counts match the
  raw label counts exactly.
- `test_weymouth_no_empty_chapters`: every chapter has rows, chapter
  numbers >= 1, no chapter gaps per book.

## Artifacts produced (for the coordinator's merge)

- `data/raw_v2/weymouth/pg8828.txt` .. `pg8854.txt` (raw downloads)
- `data/raw_v2/weymouth/manifest.json` (URLs, bytes, SHA-256)
- `data/raw_v2/weymouth/PROVENANCE.md`
- `scripts/parse_weymouth.py` (parser)
- `data/staging/weymouth.db` (7,957 rows, table `verses`)
- `data/staging/verify_weymouth.py` (deterministic verifier)
- `data/staging/weymouth-VERIFY.md` (per-sample results)
- `api/tests/batch3_frag_weymouth.py` (pytest fragment)

`data/scripture.db` and `data/study.db` were not touched (not even opened).
No backups were made on this worker's side, per instructions.

## Notes for the coordinator

1. The task schema uses verse INTEGER (unlike batch-2's TEXT verse).
   The merge should normalize if the canonical schema requires TEXT.
2. The single Luke 8:23 correction should be re-verified at merge time
   (the remap lives only in the parser's CORRECTIONS table).
3. The API's `api/translations.py` metadata table will need a WEYMOUTH
   entry at merge (not touched here).

## Proposed PLAN.md entry

Add to the Data sources table, after the OEB row:

`| Weymouth NT (3rd ed. 1913) | Project Gutenberg ebooks 8828-8854 (per-book) | PD (US) | v2 | staged 2026-09-20 (7,957 rows, merge pending) |`

## Proposed BUILD_LOG.md entry

```
## 2026-09-20 - Weymouth NT staged (WEYMOUTH, 7,957 rows)

- Source: Project Gutenberg ebooks 8828-8854, each marked
  "Copyright: Public domain in the USA." Files identify the print
  edition as Third Edition 1913 (posthumous Hampden-Cook revision).
  Hashes + rights quotes: data/raw_v2/weymouth/PROVENANCE.md.
- Parser scripts/parse_weymouth.py -> data/staging/weymouth.db
  (7,957 rows, 27 NT books, canonical book_order 39-65, no dupes).
- One source typo corrected and documented: pg8830.txt labels Luke 8:23
  as "002:023"; remapped in the parser, raw kept byte-identical.
- Verification (seed 20260920): 50/50 seeded samples char-for-char
  PASS, 3/3 hand-transcribed spot checks PASS (John 3:16, John 1:1,
  Luke 8:23), key-set agreement exact, integrity_check ok.
- Test fragment: api/tests/batch3_frag_weymouth.py (count 7957,
  3 spot checks, exactly-27-NT-books incl. no-OT assertion,
  per-book counts, no-empty-chapters).
- Not merged: data/scripture.db / data/study.db untouched per worker
  instructions. Merge must normalize verse INTEGER -> canonical type
  and add api/translations.py metadata.
```
