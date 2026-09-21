# Batch-3 ingestion report (2026-09-20)

Six sources approved by Jeremiah, staged by six worker subagents and merged
by the coordinator in order (translations first, then devotionals).
Per-source detail: verification/v2/{webster,weymouth,lxx2012,myutmost,practice,imitation}-batch3-report.md.

## Row counts (live in DB after merge)

| Source | Code / source_id | Rows merged | Scope |
|---|---|---|---|
| Webster Bible 1833 | WEBSTER | 31,102 | 66 books, book_order 0-65 |
| Weymouth New Testament | WEYMOUTH | 7,957 | 27 NT books, book_order 39-65, no OT |
| LXX2012 Septuagint in English | LXX2012 | 28,351 | 54 books: OT 0-38 + 15 deuterocanonical 66-80 |
| My Utmost for His Highest | my_utmost | 366 | days 1-366, morning only |
| Practice of the Presence of God | practice_presence | 20 | days 1-20, morning only |
| The Imitation of Christ | imitation_christ | 114 | days 1-114, morning only |

scripture.db: 396,979 verses total across 14 translations (was 329,569 / 11).
study.db devotionals: 1,964 rows (was 1,464).

## Provenance verdicts (all PASS)

- WEBSTER: eBible engwebster USFM; licensing field verbatim "Public Domain"
  (ebible.org/engwebster/copyright.htm). Zip SHA-256
  fb12085e48a2a4ada77d6b12497411c9bd321aae929d58afe74861d450009db8.
- WEYMOUTH: Project Gutenberg ebooks 8828-8854, each "Public domain in the
  USA." Files transcribe the 1913 3rd edition (posthumous Hampden-Cook
  revision); both 1903 and 1913 are PD by age.
- LXX2012: eBible eng-lxx2012; edition's own copr.htm states Brenton's 1851
  translation "has entered the Public Domain" and Michael Paul Johnson's
  updates "are dedicated to the Public Domain ... Therefore this edition
  may be freely copied, published, etc." SHA-256
  6f4018d9cde4e49fa176bb546fd0c52423fd974e46105e50f02e6b6a831cdce4.
- my_utmost: utmost.org "classic" WP REST; edition verified as the original
  1927 text (6 evidence points: Classic Language Gift Edition match, KJV-era
  diction, period anchor wordings, no NKJV markers). The copyrighted 1992
  Reimann "Updated Edition" was not used.
- practice_presence: Gutenberg eBook 13871, "Public domain in the USA";
  author d. 1691. The copyrighted Lightheart 2002 edition was avoided.
- imitation_christ: Gutenberg eBook 1653; Rev. William Benham translation
  first published 1874 (translator d. 1910), PD by age.

Explicitly excluded: The Valley of Vision (1975 Banner of Truth, under
copyright). Not touched.

## Deterministic verification (seed 20260920, char-for-character)

- Webster: 55/55 three-way checks (raw USFM -> parser -> staging DB).
- Weymouth: 50/50 seeded samples + 3 hand-transcribed anchors (John 3:16,
  John 1:1, Luke 8:23).
- LXX2012: full-table re-parse 0 mismatches across 28,352 staged rows +
  50/50 samples (10+ deuterocanon, 10+ Psalms).
- my_utmost: 30/30 raw->parser + 30/30 parser->DB.
- practice_presence: 16/16 seeded + full 20/20 exact.
- imitation_christ: 20/20 seeded chapters exact.

## Merge notes

- Backups taken before each merge:
  data/scripture.db.bak-batch3-{webster,weymouth,lxx2012}-20260920,
  data/study.db.bak-batch3-{myutmost,practice,imitation}-20260920.
- Staging DBs used INTEGER verse columns; scripture.db's convention is
  TEXT, so verse was CAST to TEXT on merge for all three translations.
- Weymouth: Gutenberg's Luke file mislabels Luke 8:23 as "002:023"; the
  parser remapped it (documented in PROVENANCE.md; raw kept byte-identical).
  Verified present exactly once post-merge.
- LXX2012: 1 row dropped at merge (1 Kings 14:1 has empty text in the
  source edition; documented gap). Merged count 28,351 vs 28,352 staged.
  Greek versification kept exactly as source (translation-scoped numbering,
  151 psalms, 1 Kings <vp>-appendix merged in document order).
- Both DBs: PRAGMA integrity_check ok after merge. No empty-text rows in
  any merged source.

## API changes

- api/translations.py: WEBSTER, WEYMOUTH, LXX2012 metadata entries with
  rights text and notes (WEYMOUTH partial NT-only + Luke 8:23 correction;
  LXX2012 Greek versification + deuterocanon list + 1 Kings 14:1 gap).
- api/study.py: DEVOTIONAL_SOURCES extended with my_utmost,
  practice_presence, imitation_christ.
- api/app.py: /v1/devotional summary/description updated (single-reading
  sources serve morning with evening null); source query description lists
  all five sources.
- api/openapi.json regenerated (3.1.0).

## Test outcomes

- api/tests/test_batch3.py assembled from the six worker fragments (29
  tests; MU_/PP_/IC_ prefixes applied to avoid module-level name
  collisions; one fragment assertion corrected: the "day 367 absent" test
  rested on a wrong date->day mapping, replaced with the day-366 boundary
  check).
- test_api.py updated: health translation list + verse_count 396,979;
  /v1/translations metadata set now includes the three new codes.
- Full suite: **172 passed, 3 warnings** (warnings are pre-existing
  deprecation notices).

## Open items / caveats

- LXX2012 verse numbering follows the Septuagint and does not align 1:1
  with Hebrew-based Bibles; the metadata notes say so, but a machine-
  readable `versification` flag was suggested and not yet implemented.
- The devotional endpoint's morning/evening model is a mild fit for the
  three new single-reading sources (evening is null); documented in the
  endpoint description.
