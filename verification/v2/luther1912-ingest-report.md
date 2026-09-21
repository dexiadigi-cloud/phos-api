# LUTHER1912 ingest report (v3, 2026-09-20)

Second non-English translation in Phos: Luther Bible 1912 (German).

## Rights clearance (gate, verified before ingest)

**Digital edition:** eBible.org "Lutherbibel 1912" (`deu1912`), eBible.org
certified.

**Download URL:** https://ebible.org/Scriptures/deu1912_usfm.zip
(retrieved 2026-09-20)

The edition's copyright file (`copr.htm`, bundled in the source zip),
text extracted 2026-09-20, lists the licensing field as **Public Domain**
with the title "The Holy Bible in German, Luther 1912" and "Translation
by: Martin Luther". No copyright holder, no Creative Commons license, no
additional terms; the eBible.org certification badge is shown on the
edition page. (Note: the browser page-fetch tool was unavailable for this
pass, so the edition's copyright.htm web page could not be read directly;
the rights statement travels with the edition inside the zip and was
verified from it.)

**Underlying work:** the 1912 revision of Martin Luther's German Bible
(second official church revision; spelling aligned to Duden standards,
Luther's diction preserved). First published 1912 (pre-1931, so US public
domain by expiry). Martin Luther died 1546.

**Caveat (kept in public docs):** US clearance is by pre-1931 expiry; that
does not by itself establish non-US status.

**Decision:** cleared for free commercial redistribution. No CC BY-SA or
other encumbered license involved.

## Source files

- `deu1912_usfm.zip`: 2,494,967 bytes, SHA-256
  `650a8192134a8f0057286c469754edcfaee4fbb18800621aee4563f3055bb39b`
- 66 USFM files, one per book, named `NN-IDdeu1912.usfm` (GEN..REV, SNG
  for Song of Songs); source files dated 2025-12-29.
- Raw kept byte-identical in `data/raw_v2/luther1912/` with
  `PROVENANCE.md` and `sha256sums.txt` (67 lines: 66 USFM files + zip).

## Ingest

- Parser: `scripts/ingest_luther1912_v3.py` (mirrored from the LSG1910
  parser via scripted substitution; Python stdlib + sqlite3 only). Stages
  to `data/staging/luther1912.db`, table `verses`, translation =
  'LUTHER1912', 0-based book_order, canonical book-name table shared with
  `scripts/ingest_lsg1910_v3.py`.
- The deu1912 USFM is structurally identical to fraLSG: `\w
  word|strong="H7225"\w*` (tag dropped, word kept), verse text accumulated
  across `\q1` continuation lines, structural markers skipped. No
  footnotes or cross-reference markers occur in this edition.
- Merge into `data/scripture.db`: `DELETE FROM verses WHERE
  translation='LUTHER1912'` (safety no-op) then `INSERT ... SELECT` from
  staging. Column order matches the live schema; chapter stays INTEGER,
  verse lands as TEXT (same as KJV), verified by `typeof()` audit.
- Backup before any write: `data/scripture.db.bak-luther1912-20260920`
  (117,760,000 bytes).

## Verification

- Deterministic three-way check (seed 20260920), script
  `scripts/verify_luther1912_v3.py`, report
  `data/staging/luther1912-VERIFY.md`: raw USFM verse block
  (independently cleaned) == parser output == staging DB, 5 mandatory
  anchors + 50 seeded samples: **55/55 pass**. No parser or verifier
  defects found in this pass.
- Staging audits: **31,102 rows**, 66 books, 0 duplicate (book, chapter,
  verse) keys, 0 empty texts, 0 rows with stray markup (backslash, pipe,
  or `strong=` remnants).
- Post-merge: `PRAGMA integrity_check` = ok; LUTHER1912 = 31,102 live
  rows; total verses 428,149 -> **459,251**; 16 distinct translations.
- 10 well-known verses spot-checked in the live staging DB, all correct
  classic Luther 1912 German: Genesis 1:1, John 3:16, Psalms 23:1,
  Romans 8:28, Matthew 6:33, Philippians 4:13, Proverbs 3:5,
  Isaiah 40:31, Jeremiah 29:11, Romans 10:9.

## Row-count note

31,102 verse keys, exactly matching KJV. No versification deltas: Luther
1912 follows KJV numbering throughout. One edition convention: psalm
titles are joined to verse 1 of the text (e.g. Psalms 23:1 reads "Ein
Psalm Davids. Der HERR ist mein Hirte; mir wird nichts mangeln."),
kept exactly as printed (translation-scoped).

## Files changed

- `api/translations.py`: LUTHER1912 metadata entry (rights + versification
  notes + territorial caveat).
- `api/openapi.json`: regenerated via `api/gen_openapi.py` (OpenAPI 3.1.0;
  translation example lists now carry all 16 codes).
- `api/app.py`: `/v1/translations` description "fifteen" -> "sixteen".
- `api/tests/test_api.py`: health assertion (16-code list, verse_count
  459251) and translations-metadata assertion (16-code set, LUTHER1912
  verse_count 31102).
- `docs/public/sources-and-attribution.md`: LUTHER1912 table row + rights
  bullet; "All 15 translations" -> "All 16 translations".
- `docs/public/coverage-and-availability.md`: "16 translations, 459,251
  verses total"; LUTHER1912 table row; versification coverage note.
- `PLAN.md`: v3 multilingual row updated (LUTHER1912 done; Almeida,
  RVA1909 still open).
- `BUILD_LOG.md`: entry appended.
- New: `scripts/ingest_luther1912_v3.py`,
  `scripts/verify_luther1912_v3.py`, `data/raw_v2/luther1912/` (zip, 66
  USFM, PROVENANCE.md, sha256sums.txt, copr.htm, keys.asc, latin.css),
  `data/staging/luther1912.db`, `data/staging/luther1912-VERIFY.md`.

## API suite

Run directly 2026-09-20 (`cd api && .venv/bin/python -m pytest tests/ -q`):
**172 passed, 3 warnings.** (One mid-task wrinkle: `gen_openapi.py`
needs `PHOS_API_KEY` set, same as the test conftest uses; the system
python lacks fastapi, so the api/.venv python was used for both the
regeneration and the suite run.)
