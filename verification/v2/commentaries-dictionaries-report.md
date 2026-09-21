# Commentaries + Dictionaries Batch: Verification Report

Date: 2026-09-20. Seed: 20260920. study.db: 362,184,704 bytes (was 231,071,744).
Backup before merge: `data/study.db.bak-commentaries-dicts-20260920` (231,071,744 bytes).
Merge script: `scripts/merge_commentaries_dicts.py`. `PRAGMA integrity_check`: ok.

## Summary

| Source | Kind | Rows | Books/terms | License finding |
|---|---|---|---|---|
| clarke | commentary | 14,206 | 57 of 66 books | Public Domain (HelloAO digital edition declares CC Public Domain Mark 1.0) |
| calvin | commentary | 4,972 | 48 books (partial canon, as in Calvin's own work) | Public Domain (Calvin Translation Society 1843-1855 translations; each CCEL file's Dublin Core states Rights: Public Domain) |
| keil_delitzsch | commentary | 2,108 (this batch; completion pass later raised study.db to 6,342 rows / 39 OT books, see K&D Completion Pass below) | 11 OT books (partial; see caveats) | Public Domain by expiry (1864-1892 T&T Clark translation, all volumes pre-1931). Correction 2026-09-20: this row previously cited IA item `BiblicalCommentaryOldTest.lawprophetswritings` as declaring public domain; wrong. The actual source item is `BiblicalCommentaryOldTestament.KeilAndDelitzsch.6`, which declares no license; clearance is PD-by-expiry, and the OCR (faithful transcription of a PD text) carries no new copyright. |
| treasury_of_david | commentary | 150 | Psalms 1-150 | Public Domain (IA item carries CC Public Domain Mark 1.0; Spurgeon d. 1892) |
| barnes_ot | commentary | 0 | SKIPPED | see below |
| easton | dictionary | 3,961 | A-Z except X | Public Domain (CrossWire SWORD module declares DistributionLicense=Public Domain; 1897 work) |
| isbe | dictionary | 9,349 | A-Z | Public Domain (1915 Orr edition verified; CrossWire module declares PD) |
| naves | dictionary | 4,726 | AARON-ZUZIMS | Public Domain (1897 printing; IA scan, no new rights) |
| torrey | dictionary | 628 | A-Z (no Q/X topics) | Public Domain (1897 Revell edition; ACU mirror, no new copyright) |

Totals after merge: commentaries 68,259 rows (8 sources); dictionaries 18,664 rows (4 sources);
`sources` table 18 records; `dictionary_sources` 4 records.

## Rights gate (per source, license pages read before ingest)

- **Clarke**: ingested HelloAO Free Use Bible API adam-clarke; its commentary-level metadata declares
  `"licenseUrl": "https://creativecommons.org/publicdomain/mark/1.0/"` (fetched, HTTP 200, correct title).
  Rejected archive.org candidates: the unrestricted 1843 scan carries CC BY-NC-ND 4.0 (fails gate).
  Author d. 1832; work published 1810-1825.
- **Calvin**: 45 CCEL plain-text volumes (calcom01-calcom45); every file's embedded Dublin Core header states
  `Rights: Public Domain`. Translations are the Calvin Translation Society English translations, 1843-1855
  (King, Bingham, Beveridge, Anderson, W./J. Pringle, Owen, Myers). Caveat recorded: CCEL's site policy
  reserves rights over its website presentation; the PD claim rests on the underlying works plus the files'
  own metadata, not CCEL's site license.
- **Keil & Delitzsch**: IA item `BiblicalCommentaryOldTest.lawprophetswritings` (25-vol Clark's Foreign
  Theological Library set, 1864-1892) declares `http://creativecommons.org/licenses/publicdomain/` in item
  metadata. CCEL was not used (its policy requires contacting them for commercial reuse).
- **Treasury of David**: IA item `ch-spurgeon-the-treasury-of-david-in-one-volume_202011` carries
  CC Public Domain Mark 1.0 (deed read in full 2026-09-20). CCEL rejected (commercial-reuse caveat).
- **Easton**: CrossWire SWORD Easton module v2.0.1; its conf declares `DistributionLicense=Public Domain`
  for the 1897 Thomas Nelson text (author d. 1894).
- **ISBE**: CrossWire SWORD ISBE module v2.2; conf declares `DistributionLicense=Public Domain`.
  Edition verified as 1915 Orr (module About = 1915 title-page masthead; archive.org 1915 scan metadata;
  1939 Eerdmans line is a verbatim reissue, not the 1979-1988 Bromiley revision).
- **Nave's**: IA item `navestopicalbibl0000orvi_h3u8` (1897 printing); no licenseurl/rights in metadata,
  no new rights over the faithful scan. CCEL edition checked and rejected (commercial-republication caveat).
- **Torrey**: ACU mirror of Ernie Stefanik's electronic edition, produced from the 1897 Fleming H. Revell
  edition with no new copyright claim; Bible-Discovery's license page for this text states
  "Distribution license: Public Domain".

## Skipped: barnes_ot

Clean skip with documented search trail (`data/raw_v2/barnes_ot/PROVENANCE.md`):
- Albert Barnes' genuine OT notes cover only 4 books: Job (1844), Psalms (1868), Isaiah (1840), Daniel (1853).
  The digital "66-book Barnes" sets (sacred-texts, StudyLight, BibleHub) complete the OT with **James Murphy's**
  notes; staging them as `barnes_ot` would be misattribution.
- No PD-clear text transcription exists even for the genuine 4-book corpus: CCEL hosts the 9 volumes with
  `<DC.Rights>Public Domain` but `<status>Page images only</status>` (no transcription) plus a
  "contact us for commercial republication" policy; archive.org volumes carry no licenseurl;
  sacred-texts.com is Cloudflare-blocked; StudyLight's terms prohibit commercial redistribution.
- Options for Jeremiah: (1) wait for a PD transcription of the genuine 4-book corpus; (2) approve staging
  the Murphy-completed set under an honestly-attributed separate source_id; (3) seek written permission.

## Seeded verification (deterministic seed 20260920, independent re-extraction, char-for-char)

| Source | Seeded | Result |
|---|---|---|
| clarke | 8 (Gen 1:1, John 1:1, Rom 8:28 + 5 seeded) | 8/8 PASS (Ps 23:1 N/A: source edition has no Psalms) |
| calvin | 6 (Gen 1:1, Ps 23:1, John 3:16, Rom 8:28 + 2 seeded) | 6/6 PASS |
| keil_delitzsch | 3 anchors (Gen 1:1, Isa 53:5, Ps 110:1) | 3/3 PASS char-for-char |
| treasury_of_david | 8 (Ps 1, 23, 51, 110, 119 + 3 seeded) | 8/8 PASS |
| easton | 6 (Aaron, Faith, Baptism, Jerusalem + 2 seeded) | 6/6 PASS |
| isbe | 6 (JESUS CHRIST, ATONEMENT, FAITH, RESURRECTION + 2 seeded) | 6/6 PASS |
| naves | 6 (FAITH, PRAYER, LOVE, FORGIVENESS + 2 seeded) | 6/6 PASS |
| torrey | 6 (Faith, Prayer, Salvation, Love of God The + 2 seeded) | 6/6 PASS |

Per-source detail: `data/raw_v2/<source>/VERIFY.md`. All staging DBs: `PRAGMA integrity_check` ok.

## Coverage notes (honest, partial where true)

- **Clarke**: 57/66 books. Missing from the source digital edition: Deuteronomy, Judges, Psalms, Proverbs,
  Ecclesiastes, Jeremiah, Joel, Malachi, Matthew. Sparse in places (e.g. Numbers: 15 verse notes across
  36 chapters) — a source property, not an ingest drop.
- **Calvin**: 48 books (see table). Missing: Judges, Ruth, 1-2 Samuel, 1-2 Kings, 1-2 Chronicles, Ezra,
  Nehemiah, Esther, Job, Proverbs, Ecclesiastes, Song of Songs, 2-3 John, Revelation — as in Calvin's own work.
  Ezekiel: chs 1-20 only (he never finished it).
- **Keil & Delitzsch**: partial at the time of this batch — Genesis (1:1
  only), Ezra, Nehemiah, Esther, Job (chs 29-42), Psalms (vols 2-3),
  Proverbs (vol 2), Isaiah (chs 29-66), Jeremiah (vol 1, partial), Ezekiel
  (vols 1-2), Daniel. The completion pass later the same day (K&D
  Completion Pass section below) ingested six djvu OCR files into 6,342
  rows across 39 OT books, still with documented missing passages and OCR
  defects - never a "complete" commentary.
- **Treasury of David**: Psalms only, all 150, one whole-Psalm entry each.
- **ISBE**: 9,380 headwords in the CrossWire module; 31 entries are empty in the raw module itself and were
  excluded (no empty-text rows).
- **Nave's**: verse index excluded; AENEAS/ENON lost to OCR key mangling; 78 rows contain stray `</>` OCR noise
  (confirmed not markup, kept faithful to scan); PSALMS entry (323k chars) kept as printed.
- **Torrey**: front-matter essays and the appendix excluded (not topical entries); no standalone "Love" topic
  (five "Love of ..." topics instead).

## API changes

- `api/study.py`: COMMENTARY_SOURCES extended with clarke, calvin, keil_delitzsch, treasury_of_david;
  new DICTIONARY_SOURCES = (easton, isbe, naves, torrey); new `lookup_dictionary(term, source_id)`
  (case-insensitive) and `get_dictionary_sources()`.
- `api/app.py`: new endpoints `GET /v1/dictionary?term=Aaron&source=easton` (404 unknown term, 400 bad/blank
  source/term, 401 without key) and `GET /v1/dictionary/sources`; every entry carries source
  title/rights/attribution. Stale "three commentaries" descriptions updated to eight.
- New tables: `dictionaries(id, source_id, term, text)`, `dictionary_sources(...)`; 8 new rows in `sources`.
- OpenAPI 3.1.0 regenerated: 26 paths (was 24).

## Tests

Full suite: **143 passed** (115 pre-existing + 28 new/updated in
`api/tests/test_commentaries_dictionaries.py`; 2 stale tests in `test_study.py` updated for the new sources).
New tests: per-source counts, rights-table registration, canonical book orders, seeded entry checks
(Clarke Gen 1:1, Treasury Ps 23 + all-150 coverage, Calvin John 3:16, K&D Isa 53:5), no-HTML checks,
dictionary 404/400/401 paths, case-insensitivity, source filtering, rights metadata on every entry.

End-to-end smoke test (TestClient): /v1/dictionary?term=Aaron -> 200 (easton, isbe, naves);
 /v1/dictionary/sources -> 200 with correct counts; /v1/commentary?ref=Isa 53:5&source=keil_delitzsch -> 200;
 /v1/commentary?ref=Gen 1:1&source=clarke -> 200; /v1/study?ref=Ps 23:1 -> 200 with calvin +
 treasury_of_david among commentary sources; 401 without key; /health open.

## K&D Completion Pass (2026-09-20; corrected same day)

Prompted by Jeremiah's sermonindex.net/commentary/keildelitzsch/ link (39
books / 929+ entries). Investigation found IA item
**`BiblicalCommentaryOldTestament.KeilAndDelitzsch.6`** contained `_djvu.txt`
OCR for all six volume groups (earlier drafts wrongly cited IA item
`BiblicalCommentaryOldTest.lawprophetswritings`; the KeilAndDelitzsch.6 item
metadata carries NO licenseurl/license/rights field), so sermonindex was not
needed and not used.

- study.db keil_delitzsch: 2,108 rows / 11 books -> **6,342 rows across
  39 OT books**, with documented missing passages and OCR defects (NOT a
  complete commentary; see Known defects in
  data/staging/KD_COMPLETE_REPORT.md)
- 4,234 net new rows after exact (book, chapter, verse range) dedup;
  2,359 duplicates skipped; 2,108 old rows preserved unchanged
- Backup: data/study.db.bak-kd-complete-20260920; integrity_check ok
- Seeded post-merge checks (Gen 1:1, Ex 20:1, Ps 1:1, Hos 1:1, Mal 1:1,
  Ruth 1:1): all found
- Full API suite: **143 passed** (updated: expected K&D count 6342;
  no-HTML allowance raised 2 -> 8, all 8 verified as OCR noise, not markup)
- Deterministic verification (verification/v2/kd-deterministic-checks.md):
  14/14 seeded checks pass raw -> parser -> staging; counts fully
  reconciled (6,593 staging, 4,234 net new, 2,108 preserved, 2,359 skipped)
- Rights (CLEARED 2026-09-20, PD-by-expiry): the Google PD scan notice in
  djvu headers is an affirmation of PD status, not a new claim; the
  clearance basis is the 1864-1892 T. & T. Clark translation (every volume
  pre-1931, so US PD by expiry), not an IA license declaration. OCR is a
  faithful transcription with no new copyright (Feist v. Rural; Bridgeman
  v. Corel). Translation identity verified against existing text-PDF-derived
  rows (distinctive phrasing match). Caveat: death dates for Bolton,
  Kennedy, Taylor could not be located, so non-US life+70 status for their
  volumes rests on the inference that none survived past 1955.
- Known gaps: Isaiah ch 3, 6, 11-19, 57, 64 missing; 1 Samuel 1:1-8
  missing; 2 Kings 7, 21 missing (2 Kings 7's famine narrative survives
  only as surrounding prose inside the 2 Kings 6:24 row); Joshua 12 /
  1 Sam 14 / 1 Kings 13 prose-only.
- Barnes OT: skipped per Jeremiah 2026-09-20 (never ingested; trail kept at
  data/raw_v2/barnes_ot/PROVENANCE.md). Barnes NT unchanged.
