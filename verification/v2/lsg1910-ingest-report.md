# LSG1910 ingest report (v3, 2026-09-20)

First non-English translation in Phos: Louis Segond 1910 (French).

## Rights clearance (gate, verified before ingest)

**Digital edition:** eBible.org "Louis Segond 1910" (`fraLSG`), eBible.org
certified.

**Edition page:** https://ebible.org/fraLSG/
**Rights statement page:** https://ebible.org/fraLSG/copyright.htm
(retrieved 2026-09-20)
**Download URL:** https://ebible.org/Scriptures/fraLSG_usfm.zip

The rights page lists the licensing field as **Public Domain** (linked to
the Wikipedia Public Domain article) and states, in French and English:

> Cette Bible est dans le domaine public. Il n'est pas protégé par copyright.
> This Bible is in the Public Domain. It is not copyrighted.

No copyright holder, no Creative Commons license, no additional terms; the
eBible.org certification badge is shown on the edition page.

**Underlying work:** Louis Segond's French translation, first edition
published 1910 (pre-1931, so US public domain by expiry). Louis Segond
died 1909, so life-plus-70 expired at the end of 1979.

**Caveat (kept in public docs):** US clearance is by pre-1931 expiry; that
does not by itself establish non-US status. The working non-US basis is
the translator's 1909 death (life-plus-70 expired 1980).

**Decision:** cleared for free commercial redistribution. No CC BY-SA or
other encumbered license involved.

## Source files

- `fraLSG_usfm.zip`: 3,467,489 bytes, SHA-256
  `3a0615e992ffd412b1afcaed50d146bba5ec8ae2378f04ca71459a4cd2d7cc33`
- 66 USFM files, one per book, named `NN-IDfraLSG.usfm` (GEN..REV, SNG for
  Song of Songs); source files dated 2026-08-08.
- Raw kept byte-identical in `data/raw_v2/lsg1910/` with `PROVENANCE.md`
  and `sha256sums.txt` (67 lines: 66 USFM files + zip).

## Ingest

- Parser: `scripts/ingest_lsg1910_v3.py` (mirrors the Webster batch-3
  pattern; Python stdlib + sqlite3 only). Stages to
  `data/staging/lsg1910.db`, table `verses`, translation = 'LSG1910',
  0-based book_order, canonical book-name table shared with
  `scripts/ingest_translations_batch2.py`.
- USFM specifics of this edition: words carry Strong's tags
  (`\w word|strong="H7225"\w*`; tag dropped, word kept),
  `\+w ... \+w*` and `\wj ... \wj*` kept as plain words,
  `\f ... \f*` footnotes and `\x ... \x*` cross-references dropped,
  verse text accumulated across `\q1`/`\q2`/`\m` continuation lines.
- Merge into `data/scripture.db`: `DELETE FROM verses WHERE
  translation='LSG1910'` (safety no-op) then `INSERT ... SELECT` with
  `CAST(verse AS TEXT)` (staging uses INTEGER; live schema verse is TEXT).
- Backup before any write: `data/scripture.db.bak-lsg1910-20260920`
  (110,579,712 bytes).

## Verification

- Deterministic three-way check (seed 20260920), script
  `scripts/verify_lsg1910_v3.py`, report `data/staging/lsg1910-VERIFY.md`:
  raw USFM verse block (independently cleaned) == parser output ==
  staging DB, 5 mandatory anchors + 50 seeded samples: **55/55 pass**.
- Two defects were caught by verification *before* merge and fixed:
  (1) `\+w` plus-markers were not stripped by the parser cleaner (e.g.
  Mark 9:49 rendered as `\+w Car\+w* ...`); (2) the verifier's raw-body
  extractor did not accumulate multi-line verses, producing 19 false
  failures. Both fixed; final run 55/55.
- Staging audits: **31,170 rows**, 66 books, 0 duplicate (book, chapter,
  verse) keys, 0 empty texts, 0 rows with stray markup (backslash, pipe,
  or `strong=` remnants).
- Post-merge: `PRAGMA integrity_check` = ok; LSG1910 = 31,170 live rows;
  total verses 396,979 -> **428,149**; 15 distinct translations.
- 10 well-known verses spot-checked in the live DB, all correct classic
  LSG1910 French: Genesis 1:1, John 3:16, Psalms 23:1, Romans 8:28,
  Matthew 6:33, Philippians 4:13, Proverbs 3:5, Isaiah 40:31,
  Jeremiah 29:11, Romans 10:9.

## Row-count note

31,170 verse keys vs 31,102 for KJV. The difference is genuine
versification, not a parser defect: Louis Segond 1910 follows traditional
French numbering. Verse keys are kept exactly as the edition prints them
(translation-scoped), the same policy as LXX2012's Greek numbering.
Documented offsets (LSG key = KJV key):

- Psalms: titles numbered as verse 1 (LSG Ps 3:1 is the title; LSG Ps
  3:9 = KJV Ps 3:8)
- Exodus 7:26-29 = KJV 8:1-4; 8:25-28 = KJV 8:29-32
- Leviticus 5:20-26 = KJV 6:1-7; 6:17-23 = KJV 6:24-30
- Numbers 30:1 = KJV 29:40; 30:17 = KJV 30:16
- 1 Samuel 20:43 = KJV 21:1; 24:1 = KJV 23:29; 24:23 = KJV 24:22;
  1 Kings 22:54 = KJV 22:53; 2 Chronicles 13:23 = KJV 14:1; 14:14 = KJV 14:15
- Job 39:31-40:28, 41:17-25 = KJV 40:1-41:34 (Behemoth/Leviathan
  chapter-break offset); Ecclesiastes 4:17 = KJV 5:1; 5:19 = KJV 5:20;
  12:15-16 = KJV 12:13-14; Song of Songs 7:1 = KJV 6:13; 7:14 = KJV 7:13
- Isaiah 8:23 = KJV 9:1; 9:20 = KJV 9:21; 64:11 = KJV 64:12
- Ezekiel 21:1-5 = KJV 20:45-49; 21:33-37 = KJV 21:28-32
- Hosea 2:1-2 = KJV 1:10-11; 2:24-25 = KJV 2:22-23; 12:1 = KJV 11:12;
  12:15 = KJV 12:14; Jonah 2:1 = KJV 1:17; 2:11 = KJV 2:10
- Micah 4:14 = KJV 5:1; 5:14 = KJV 5:15; Nahum 2:1 = KJV 1:15; 2:14 = KJV 2:13
- Mark 9:51 = KJV 9:50b (verse split); Mark 10:53 = KJV 10:52b;
  3 John 1:15 = KJV 1:14; Revelation 12:18 = KJV 13:1
- Acts 19:40 = KJV 19:41; 2 Corinthians 13:13 = KJV 13:14

Each offset above was confirmed by comparing actual verse text, not just
counts (Ezekiel 21:33 and Hosea 2:24-25 verified word-for-word against the
KJV counterparts).

## Files changed

- `api/translations.py`: LSG1910 metadata entry (rights + versification
  notes + territorial caveat).
- `api/openapi.json`: regenerated via `api/gen_openapi.py` (OpenAPI 3.1.0;
  translation example lists now carry all 15 codes).
- `api/app.py`: `/v1/translations` description "fourteen" -> "fifteen".
- `api/tests/test_api.py`: health assertion (15-code list, verse_count
  428149) and translations-metadata assertion (15-code set, LSG1910
  verse_count 31170).
- `docs/public/sources-and-attribution.md`: LSG1910 table row + rights
  bullet; "All 14 translations" -> "All 15 translations".
- `docs/public/coverage-and-availability.md`: "15 translations, 428,149
  verses total"; LSG1910 table row; French-versification coverage note.
- `PLAN.md`: v3 multilingual row updated (LSG1910 done; Luther1912,
  Almeida, RVA1909 still open).
- `BUILD_LOG.md`: entry appended.
- New: `scripts/ingest_lsg1910_v3.py`,
  `scripts/verify_lsg1910_v3.py`, `data/raw_v2/lsg1910/` (zip, 66 USFM,
  PROVENANCE.md, sha256sums.txt, copr.htm), `data/staging/lsg1910.db`,
  `data/staging/lsg1910-VERIFY.md`.

## API suite

Run directly 2026-09-20 (`cd api && python3 -m pytest tests/ -q`):
**172 passed, 3 warnings.** (One failure appeared mid-task:
`test_translations_metadata` hardcoded the 14-code set; updated to 15
codes and re-ran: full pass.)

## Environment note

`/tmp` (512M tmpfs) is 100% full on this VM. It did not block this task
(nothing needed /tmp), but it is worth clearing before work that does.
