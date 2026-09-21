# Batch 3 report: My Utmost for His Highest (Oswald Chambers)

## Edition-verification verdict: ORIGINAL 1927 TEXT - ingest proceeds

The digital source is utmost.org's "classic" post type (WP REST API
`https://utmost.org/wp-json/wp/v2/classic`), the official publisher site
(Our Daily Bread Publishing / Discovery House). CCEL was checked first and
rejected: `ccel.org/ccel/chambers` is a bio page with no hosted full text
(404 on probed work paths).

Evidence the text is the original 1927 text, NOT the 1992 Reimann updated
edition:

1. Jan 1 reading is verbatim the publisher's Classic Language Gift Edition
   excerpt ("My eager desire and hope being that I may never feel ashamed...",
   "My Undeterredness for His Holiness", "providential crisis",
   "over-weening consideration"). The updated edition's Jan 1
   ("my earnest expectation and hope that in nothing I shall be ashamed",
   NKJV) is absent from the entire corpus.
2. KJV-era diction throughout: "ye" x89, "hath" x18 (e.g. Mar 14:
   "He hath anointed me ... to preach deliverance to all captives").
3. Anchor verses are not NKJV: Feb 29 quotes "They rebuked him, that he
   should hold his peace" (Mark 10:48 KJV); anchor verse wordings are
   period translations (KJV, MOFFATT, RV), never NKJV wording. (One anchor
   link URL carries a version=NIV page-builder query parameter; the verse
   text it quotes is Moffatt's rendering, and the "(see moffatt)" note is
   preserved in the staged entry.)
4. Independent transcription agreement: godrules.net per-day pages
   (Jan 1, Mar 14, Aug 19) match on substance and KJV-era wording; only
   trivial orthographic variance ("over-weening" vs "overweening").
5. Update-edition markers absent: "with all boldness",
   "my unstoppable determination", "my earnest expectation and hope".
   The one surface-similar phrase "it makes no difference" occurs in the
   Apr 18 "Readiness" reading as Chambers' own original diction.
6. utmost.org labels this post type "classic"; the updated edition is a
   separate post type that was never queried.

Conclusion: original 1927 text (Simpkin & Marshall; 1935 Dodd, Mead US;
author d. 1917), US public domain since 2023-01-01. Skip was not needed.

## Provenance verdict: PASS

`data/raw_v2/my_utmost/PROVENANCE.md` records exact URLs, edition, rights
basis, the six-point edition-verification evidence above, and SHA-256
hashes of the downloaded files. *The Valley of Vision* was not touched in
this batch: no source of it was fetched, parsed, or staged.

- `utmost_classic_raw.json`: 367 REST posts (366 readings + 1 empty
  "today" redirect placeholder, excluded).
  SHA-256: b5898c39f45053ceba031c707a5f3328ab88bd088489bed570eb19959ff329d1
- `anchor_verses.json`: anchor verse block scraped from each reading's
  rendered page (REST content omits it). All 366 pages yielded exactly one
  anchor block: 344 used the standard markup (anchor link with `title`
  attribute); 22 used variant markup (no `title` attribute) handled by a
  paragraph-level re-extraction; 1 page (`god-first-classic`) cites three
  verses in section paragraphs, anchor taken as the top-of-page verse
  paragraph; 1 page carries a trailing "(see moffatt)" note preserved in
  the entry. A full re-extraction diffed all 366 entries (362 agreed;
  4 diffs: 2 trailing-dash normalizations, 1 version-tag fix, 1 empty
  entry fixed).
  SHA-256: dc40ee846a5d35602d52e8949923db02f4ff3650edb867649643d7a313d03d49
- `utmost_classic_type.json`: the site's own post-type record for
  `classic`: name "Classic Edition Devotionals", description "Classic
  Edition daily devotionals".
  SHA-256: f3aa89d86b76c7f29517661faa2cf8c54c8a457ccd38fc2d8d3b26d962daca68

## Row counts

- `data/staging/my_utmost.db`, table `devotionals`: 366 rows
  (source_id='my_utmost', part='morning', days 1..366, no gaps).
- Table `sources`: 1 row (source_id='my_utmost', kind='devotional',
  title='Oswald Chambers, My Utmost for His Highest', rights=
  'Public Domain', version='original-1927', sha256 of the raw REST dump).
- Unique index on (source_id, day, part); PRAGMA integrity_check ok.
- All 366 anchor refs validated against the Phos KJV bounds via
  api/parser.py. Feb 29 present as day 60 (leap-year convention, same as
  spurgeon/daily_light). Ref normalizations (refs only, never prose):
  "2 Peter 1:5, 7" -> "2 Peter 1:5; 2 Peter 1:7"; "Jude 20" -> "Jude 1:20";
  "3 John 7" -> "3 John 1:7"; trailing period stripped from "Romans 14:7.".
- Leak check: 0 HTML tags, 0 HTML entities, 0 USFM markers in title/body.

## Deterministic check results (seed 20260920)

`scripts/verify_v2_myutmost.py` -> `data/staging/my_utmost-VERIFY.md`:
30 seeded readings (seed 20260920: days 11, 36, 64, 65, 66, 95, 97, 113,
124, 129, 144, 150, 166, 178, 194, 202, 210, 220, 225, 232, 241, 245, 253,
262, 287, 301, 324, 335, 356, 364) compared character-for-character in two
stages: A = raw source (independently re-derived) -> parser output
(`parse_v2_myutmost.build_rows`); B = parser output -> staging DB rows.
Fields per stage: day, title, anchor_ref, body.

- Structural checks: 7/7 PASS (row count 366; days 1..366 no gaps;
  all source_id my_utmost; all part morning; no empty anchor_ref/title/body)
- Stage A (raw -> parser): 30/30
- Stage B (parser -> DB): 30/30
- Verdict: PASS

## Test fragment

`api/tests/batch3_frag_myutmost.py` (not collected until assembled):
ROW_COUNT = 366; days 1..366 with no gaps and exactly one entry per day
(morning set, evening None, non-empty title/anchor_ref/body); seeded
spot-checks (seed 20260920) for days 301 ("The Method Of Missions"), 324
("When He Is Come"), 364 ("Deserter Or Disciple?") with day/title/
body-prefix assertions via the /v1/devotional endpoint (follows the
batch3_frag_imitation.py pattern); Feb 29 (day 60) present; day 367
absent.

## Required API allowlist change (coordinator)

In `api/study.py`, `DEVOTIONAL_SOURCES = ("spurgeon", "daily_light")`
(line 51) must gain `"my_utmost"` after merge, plus the endpoint
description update. No API code was changed on my side.

## Proposed log entries

PLAN.md (append under the batch-3 section):
- `[x] my_utmost: staged 366 devotionals (original 1927 text, utmost.org
  "classic" REST) + sources row -> data/staging/my_utmost.db; edition
  verified original vs 1992 update (6 evidence points in PROVENANCE.md);
  deterministic verify (seed 20260920) PASS: 30/30 raw->parser and 30/30
  parser->DB; fragment api/tests/batch3_frag_myutmost.py. Coordinator:
  add "my_utmost" to DEVOTIONAL_SOURCES in api/study.py.`

BUILD_LOG.md (append):
- `2026-09-20 my_utmost ingest: source utmost.org WP REST /wp-json/wp/v2/classic
  (CCEL has no hosted full text; IA 1935 scans are lending-restricted).
  Edition-verified original 1927 text (not 1992 Reimann update).
  366 rows staged (days 1..366, morning only, Feb 29 = day 60), all anchors
  validated vs KJV bounds, verify PASS (30/30 raw->parser, 30/30
  parser->DB), pytest fragment written.
  Raw: data/raw_v2/my_utmost/ (PROVENANCE.md + sha256s).`
