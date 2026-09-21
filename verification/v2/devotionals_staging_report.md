# V2 Devotionals Staging Report

Date: 2026-09-20. Staging only. No application code was changed and no
`study.db` was created. `data/scripture.db` was opened read-only (via
`api/db.py` / `api/parser.py`) for reference validation; it was not written to.

## Result

`staging/devotionals.db` holds **1464 rows**: 732 Spurgeon + 732 Daily Light,
each source covering days 1-366 x morning/evening, including Feb 29 (day 60).

Schema (exact, as required):

```sql
CREATE TABLE devotionals (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  day INTEGER NOT NULL,          -- 1..366 (leap-year day-of-year; Feb 29 = 60)
  part TEXT NOT NULL,            -- 'morning' | 'evening'
  title TEXT,                   -- may be NULL
  anchor_ref TEXT NOT NULL,
  body TEXT NOT NULL
);
CREATE UNIQUE INDEX ux_devotionals ON devotionals(source_id, day, part);
```

Row layout per source:

- **spurgeon**: `title` = key-verse text (one layer of transcription quotes
  removed), `anchor_ref` = key-verse reference, `body` = devotional prose with
  the duplicated date/part heading and key-verse line stripped, paragraphs
  joined by `\n\n`.
- **daily_light**: `title` = theme-verse text, `anchor_ref` = every item
  reference in reading order joined by `"; "`, `body` = theme text followed by
  each verse text, paragraphs joined by `\n\n`.

## Rights basis and rejected editions

- **Spurgeon, *Morning and Evening* (1866).** First published 1866 (London:
  Passmore & Alabaster); author died 1892-01-31. Public domain in the US.
  Transcription: `russianryebread/morning-and-evening` (commit
  `6caf938672ee2ea777ec787c13573d439fe88bf7`), which claims no copyright on
  the transcription. REJECTED: `deweywellingtoncat/modernized-spurgeon-reflections`
  (explicitly modernized, GPL-3.0). REJECTED as ingest source: the CCEL edition
  (ccel.org/ccel/spurgeon/morneve) - CCEL's copyright policy limits its editions
  to personal/educational/non-profit use and requires permission for commercial
  republication; the underlying 1866 text is PD but the edition terms are
  incompatible with a public-domain-only API absent a separate rights decision.
  CCEL text was used only as a cross-check: all 732 date/part keys matched, and
  one error in the CCEL-derived comparison parse was found and not followed
  (Jan 13 PM: the verse text requires 2 Kings 6:6, not 6:9).
- **Bagster, *Daily Light on the Daily Path* (1875).** All-scripture KJV text,
  long public domain; no recent edition holds a copyright claim on the KJV
  text selection/arrangement (per CCEL's own research note on the work, used
  for rights research only). Transcription: `gm5dna/daily-light` (commit
  `c36a7bf63ffc6ef5290a0cb82bd26fa28f9ffcdf`), MIT-licensed repo asserting the
  text is public domain. REJECTED as ingest sources: the CCEL edition (same
  non-commercial terms issue) and Crossway's ESV edition (copyrighted Bible
  translation). Oneplace/Lightsource/Crosswalk were not scraped.

## Source processing

### Spurgeon (732 entries)

Raw: `data/raw_v2/spurgeon/m_e.json` (sha256
`2d86c9b47026f65cf041fb4ed5dca03d844296928d589535d346371bfbe7063b`).
744 list slots, 12 null month-grid paddings, 732 real entries (366 morning +
366 evening, Feb 29 present).

Encoding repairs (deterministic, wording untouched):
- UTF-8 curly quotes misdecoded as Latin-1 (`â` + C1 bytes), 4 occurrences,
  restored to `"` / `"`.
- Lone C1 controls as Windows-1252 punctuation: U+0097 -> em dash (103x),
  U+0092 -> `'` (2x), U+0093/U+0094 -> `"`/`"` (4x each), U+0096 -> en dash
  (2x). No other C1 characters remained after repair (asserted).
- One U+00A0 (poetry indent artifact) normalized to a plain space.

Structure: every body begins with a date/part heading line, the key-verse
line (verified byte-identical to the `keyverse` field in all 732 records),
and a blank line; all three were stripped. Paragraphs re-joined with `\n\n`;
inner line breaks (poetry) preserved.

Anchors: all 732 key-verse references validate through
`parser.parse_reference()` against KJV bounds. 729 parse directly; 3 are
semicolon-joined multi-references split on `;` first (Jun 13 PM
`Proverbs 30:8; Psalm 38:21`, Jul 12 AM `Jude 1:1; 1 Corinthians 1:2;
1 Peter 1:2`, Aug 30 PM `Jeremiah 17:14; Isaiah 57:18`).

### Daily Light (732 entries, 5,656 verse items)

Raw: `data/raw_v2/daily_light/readings.json` (sha256
`7a776c8c6e0015a7a5da5744ac50de16f6a08a6895b47d0141a5884cd2763f0b`).
732 entries (366 morning + 366 evening, Feb 29 present), each with a theme
verse and 2-15 verse items.

The transcription's **reference strings are defective** (shifted by one
position in many entries, concatenated multi-ref blobs, `Matthew 1511`,
`Ephesians L:13`, `Jude 24`, 39 empty references, 10 items with `.` text).
Verse **text** was kept byte-faithful, including minor transcription typos
(`sanctiflcation` 1x, `feIlowcitizens` 1x, `litile` 1x, doubled `the the` 3x,
U+2011 non-breaking hyphens 20x).

Every item's stored reference was confirmed or reconstructed from its verse
text against the KJV corpus (`data/raw_v2/daily_light/ref_reconciliation.json`,
5,656 decisions in raw item order):
- **keep** 5,127: supplied reference parsed and the verse text sits within it.
- **derive** 529: supplied reference empty, malformed, shifted, or
  inconsistent; replacement located from normalized KJV text (citation-aware
  tie-breaking; ellipsis treated as omission within one sentence; no
  multi-verse matching for clauses under six tokens; neighboring-verse
  expansion only when strictly better).
- **24 manual resolutions**, all documented with reasons in
  `verification/v2/raw/devotionals/reconciliation_summary.json`: 23 keep the
  source reference (short labels such as `Jesus wept.`, `Amen.`, altar-names
  like `Jehovah-nissi`, and 10 empty-text items whose refs validate), 1
  derives from a confirmed 5-item shift chain (Mar 3 PM `An incorruptible
  crown.` -> `1 Corinthians 9:25`; the item's neighbors each match the next
  item's reference). One suspected typo is kept verbatim and flagged
  (Jul 25 PM `Follow me.` anchored `Matthew 14:19`; likely Matthew 4:19).

All 5,656 final reference strings validate through `parser.parse_reference()`
when split on semicolons (6,514 anchor pieces total across both sources,
including Spurgeon's multi-refs).

## Verification

`verification/v2/verify_v2_devotionals.py` (independent reimplementation, not
importing the ingest script). All checks passed:

- Row counts: 1464 total; 732 per source; days 1-366 fully covered for both
  parts of both sources; Feb 29 (day 60) present twice per source.
- 6,514 anchor pieces re-parsed OK against KJV bounds.
- Leak checks: 0 HTML tags, 0 HTML entities, 0 USFM markers across all rows.
- `PRAGMA integrity_check` = ok. Unique index `ux_devotionals` present.
- **Seeded spot checks (seed 20260920), 12 per source, all exact matches** on
  title, anchor_ref, and body. The Daily Light sample covers entries with
  derived references. Evidence:
  `verification/v2/raw/devotionals/spot_checks.json`.

## Caveats and unresolved gaps

- Daily Light anchors for 529 items are reconstructions from verse text, not
  the transcription's printed references; the reconstruction method and every
  manual decision are documented, but this is a repaired corpus, not a clean
  transcription. If a traceable scan-faithful 1875 transcription surfaces, it
  should replace this source.
- 10 Daily Light items have `.` as their verse text; their anchors are the
  source's references (all validate). The text gap is in the transcription.
- The 1875 edition attribution rests on the repo README's public-domain
  assertion plus CCEL's research note; no scan was directly compared.
- `staging/` also contains `crossrefs.db` and `liturgy.db` from unrelated
  work; untouched by this task.

## File inventory

- `scripts/ingest_v2_devotionals.py` - deterministic ingest (stdlib+sqlite3).
- `data/raw_v2/spurgeon/m_e.json`, `provenance.json`.
- `data/raw_v2/daily_light/readings.json`, `provenance.json`,
  `ref_reconciliation.json`.
- `staging/devotionals.db` - the staged output.
- `verification/v2/verify_v2_devotionals.py` - independent verifier.
- `verification/v2/raw/devotionals/spot_checks.json` - seeded spot-check evidence.
- `verification/v2/raw/devotionals/reconciliation_summary.json` - decision
  counts and the 24 manual resolutions.
- This report: `verification/v2/devotionals_staging_report.md`.
