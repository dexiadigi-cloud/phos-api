# Batch 3 report: The Imitation of Christ (imitation_christ)

Ingestion worker report, 2026-09-20. Staging only; data/scripture.db and
data/study.db were not touched. No backups created on my side (per batch
instructions; the coordinator owns the merge).

## Provenance verdict: PUBLIC DOMAIN, cleared for ingest

- **Digital edition:** Project Gutenberg eBook #1653,
  https://gutenberg.org/files/1653/1653-0.txt (downloaded 2026-09-20,
  374,767 bytes, SHA-256
  `d5c1a5b7820ac4b7da8600730932b0b84a6be9fce58cfa43008dae771b738451`).
- **Edition rights statement (quoted verbatim from the file header):**
  "This eBook is for the use of anyone anywhere in the United States and
  most other parts of the world at no cost and with almost no restrictions
  whatsoever. You may copy it, give it away or re-use it under the terms
  of the Project Gutenberg License included with this eBook or online at
  www.gutenberg.org." The PG catalog page for #1653 lists "Copyright |
  Public domain in the USA."
- **Translator PD status:** Translator named in the file header and PG
  catalog as William Benham (1831-1910), died 30 July 1910. His translation
  of the Imitation was first published 1874 (new ed. 1905) per the
  biographical record (Wikipedia, William Benham, priest). 19th century,
  pre-1930, so the translation is public domain by age in the US. This is
  not a modern copyrighted translation. The original author, Thomas a
  Kempis, died 1471. Ingest proceeded on that basis.
- Full provenance (exact URLs, edition, translator, rights terms, SHA-256,
  and the CCEL 1940 alternative considered and rejected):
  [data/raw_v2/imitation_christ/PROVENANCE.md](../../data/raw_v2/imitation_christ/PROVENANCE.md)

## Row counts

- Staging DB: [data/staging/imitation_christ.db](../../data/staging/imitation_christ.db)
- `devotionals`: **114 rows** (source_id='imitation_christ', part='morning'
  on every row, anchor_ref='' on every row, days 1..114 with no gaps).
  Book/chapter counts verified against the edition: Book 1: 25, Book 2: 12,
  Book 3: 59, Book 4: 18.
- `sources`: **1 row** (source_id='imitation_christ', kind='devotional',
  title='Thomas a Kempis, The Imitation of Christ', rights='Public Domain',
  rights_basis as quoted in PROVENANCE.md, version='PG ebook 1653
  (2023-05-05 update)', sha256 of the raw file).
- Notes: title format `Book <b>, Chapter <c>: <chapter title>` from the
  edition's chapter titles. The unnumbered Book 4 preface ("A devout
  exhortation to the Holy Communion") is not a chapter and was excluded
  (documented in PROVENANCE.md). Leak check: 0 HTML tags, 0 HTML entities.
  `PRAGMA integrity_check`: ok. Unique index
  ux_devotionals(source_id, day, part) present.

## Deterministic verification (seed 20260920)

- Script: scripts/verify_v2_imitation.py (independent re-derivation from
  the raw file, own code path, not the parser).
- 20 sampled days [76, 81, 91, 36, 17, 58, 105, 53, 45, 31, 57, 3, 93, 38,
  66, 61, 113, 111, 51, 16]: **20 passed, 0 failed**, title/body/day
  character-for-character raw source -> staging DB.
- Global checks: row count 114, independent parse count 114, days exactly
  1..114, one sources row, sha256 matches raw file: all PASS.
- Results: [data/staging/imitation_christ-VERIFY.md](../../data/staging/imitation_christ-VERIFY.md)

## Test fragment

- Path: [api/tests/batch3_frag_imitation.py](../../api/tests/batch3_frag_imitation.py)
  (not collected until the coordinator assembles it).
- Contents: ROW_COUNT = 114 constant; days 1..114 no-gap check via
  /v1/devotional (2024 leap-year dates, day 1 = 2024-01-01, day 114 =
  2024-04-23); book/chapter sequence ordering check against title regex
  (days 1-25 = Book 1 ch 1-25, 26-37 = Book 2 ch 1-12, 38-96 = Book 3
  ch 1-59, 97-114 = Book 4 ch 1-18); 3 seeded spot checks (days 76, 81,
  91: exact title + first 80 chars of body); boundary check that day 115
  (2024-04-24) returns no entry.
- Fragment assertions were simulated against the staging DB before
  delivery: all pass. NOTE: the fragment asserts evening is None and
  anchor_ref == "" for this source; this is correct for the merged data
  (morning-only rows, empty anchor_ref). `_devotional_entry` in api/app.py
  already handles empty anchor_ref (anchor_verses = []).

## Required API change (for the coordinator)

1. api/study.py line 51: `DEVOTIONAL_SOURCES = ("spurgeon", "daily_light")`
   must become `DEVOTIONAL_SOURCES = ("spurgeon", "daily_light",
   "imitation_christ")`.
2. api/app.py get_devotional query description: "Devotional source:
   spurgeon or daily_light." must become "Devotional source: spurgeon,
   daily_light, or imitation_christ." (and the source_title will resolve
   from the sources row automatically).

## Proposed log entries (do NOT apply; for the coordinator to edit)

PLAN.md Decisions log (appended 2026-09-20):
- 2026-09-20: devotional staging schema unchanged; batch-3 devotional
  source `imitation_christ` staged at
  data/staging/imitation_christ.db (114 devotionals rows, days 1..114,
  morning-only, empty anchor_ref; 1 sources row, Public Domain). Source:
  PG eBook #1653 (Benham 1874/1905 translation). Merge into study.db +
  DEVOTIONAL_SOURCES allowlist update still pending.

BUILD_LOG.md, new section:
## 2026-09-20 — The Imitation of Christ staged (batch 3, merge pending)

- Source: Project Gutenberg eBook #1653, William Benham translation
  (first published 1874, new ed. 1905; translator d. 1910; PD by age).
  Catalog: "Public domain in the USA." Raw at
  data/raw_v2/imitation_christ/1653-0.txt (sha256
  d5c1a5b7820ac4b7da8600730932b0b84a6be9fce58cfa43008dae771b738451);
  provenance in data/raw_v2/imitation_christ/PROVENANCE.md.
- Parsed with scripts/parse_v2_imitation.py to
  data/staging/imitation_christ.db: **114 rows** (Book 1: 25, Book 2: 12,
  Book 3: 59, Book 4: 18; days 1..114, part morning, anchor_ref empty) +
  1 sources row. Verification (seed 20260920): 20/20 seeded chapters
  character-for-character PASS; integrity_check ok.
  Results: data/staging/imitation_christ-VERIFY.md.
- Test fragment: api/tests/batch3_frag_imitation.py (assembled later;
  requires DEVOTIONAL_SOURCES += "imitation_christ" in api/study.py).
- study.db NOT touched. Merge + allowlist update are the coordinator's
  steps.

## Files produced

- data/raw_v2/imitation_christ/1653-0.txt (raw download)
- data/raw_v2/imitation_christ/PROVENANCE.md
- data/staging/imitation_christ.db
- data/staging/imitation_christ-VERIFY.md
- api/tests/batch3_frag_imitation.py
- scripts/parse_v2_imitation.py, scripts/verify_v2_imitation.py (worker tooling)

No em dashes were used in any doc written for this batch.
