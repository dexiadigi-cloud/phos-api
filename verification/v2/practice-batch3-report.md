# Batch 3 report: Practice of the Presence of God (practice_presence)

Date: 2026-09-20. Ingestion worker for Phos batch 3, approved by Jeremiah.

## Provenance verdict: PASS, public domain confirmed

Source: Project Gutenberg eBook No. 13871, "The Practice of the Presence
of God the Best Rule of a Holy Life" by Brother Lawrence.
Catalog page: http://www.gutenberg.org/ebooks/13871 (read 2026-09-20,
marked "Copyright: Public domain in the USA.").
Raw file downloaded: https://www.gutenberg.org/cache/epub/13871/pg13871.txt
(80,593 bytes, retrieved 2026-09-20).

Rights statement quoted verbatim from the digital edition header:

> The Project Gutenberg eBook of The Practice of the Presence of God the Best Rule of a Holy Life
>
> This eBook is for the use of anyone anywhere in the United States and
> most other parts of the world at no cost and with almost no restrictions
> whatsoever. You may copy it, give it away or re-use it under the terms
> of the Project Gutenberg License included with this eBook or online
> at www.gutenberg.org. If you are not located in the United States,
> you will have to check the laws of the country where you are located
> before using this eBook.

Rights basis for commercial use: the author (Nicolas Herman, Brother
Lawrence) died in 1691; the French work was first published circa
1691 (letters) and 1694 (letters plus conversations); Project Gutenberg
marks this eBook "Public domain in the USA." The copyrighted Lightheart
2002 edition (Gutenberg eBook 5657) was explicitly avoided; only eBook
13871 was used.

Raw SHA-256: 1f4df307f62f2be596e4be48afce14067cea1a1f54c957639087386b180716e9
Recorded in data/raw_v2/practice_presence/PROVENANCE.md and provenance.json.

## Row counts

- data/staging/practice_presence.db, table devotionals: **20 rows**
  (day 1 = Preface; days 2-5 = First through Fourth Conversation;
  days 6-20 = First through Fifteenth Letter; part = 'morning' for all;
  anchor_ref = '' for all, never NULL)
- table sources: **1 row** (source_id 'practice_presence', kind
  'devotional', rights 'Public Domain', version 'Gutenberg eBook 13871,
  plain text, release 2004-10-26, updated 2024-10-28', sha256 of raw)
- Unique index ux_devotionals (source_id, day, part) present;
  PRAGMA integrity_check: ok
- data/scripture.db and data/study.db were not touched (no reads, no
  writes). Coordinator merges later.

## Deterministic verification: PASS (seed 20260920)

Script: scripts/verify_v2_practice_presence.py. It re-derives expected
rows from the raw file with independent line-based splitting code (no
ingest-script imports) and compares character-for-character against the
staged rows. Full results: data/staging/practice_presence-VERIFY.md.

- Seeded sample: 16 of 20 sections drawn with random.Random(20260920),
  all 16 exact matches on title, body, and day (16/16 PASS)
- Full 20/20 title+body exact match (independent of the sample)
- Days 1..20 with no gaps; part/anchor_ref/source_id uniform; sources
  row well-formed; integrity_check ok
- OVERALL: PASS

One genuine divergence was caught and resolved during verification:
the first verify pass cut days 1 and 5 at the next section heading,
including the division headings (CONVERSATIONS., LETTERS.) in the body;
the parser excludes them. The parser's contract (division headings belong
to no section) is the intended one, so the verifier was corrected to
treat division headings as boundaries. Final state: 20/20 exact.

Parse contract (documented in PROVENANCE.md): sections split at the exact
all-caps heading lines; license preamble, Gutenberg title page, division
headings, and license footer excluded; CRLF normalized to LF; inline
footnote markers and the end-of-letter footnote block kept verbatim.

## Test fragment

api/tests/batch3_frag_practice.py (not collected until assembled). It
declares ROW_COUNT = 20, checks days 1..20 with no gaps via
/v1/devotional (evening entries must be None, anchor_ref ""), and has
three seeded spot checks (seed 20260920 drew days 5, 9, 19) asserting
title plus the first ~80 chars of body. Spot-check constants were
verified character-for-character against the staging DB. Uses the shared
client/auth fixtures and follows the /v1/devotional patterns in
test_study.py. The fragment will return HTTP 400 until the allowlist
change below is made.

## Required API change (coordinator)

In api/study.py, line 51:

    DEVOTIONAL_SOURCES = ("spurgeon", "daily_light")

must become:

    DEVOTIONAL_SOURCES = ("spurgeon", "daily_light", "practice_presence")

Also update the /v1/devotional endpoint description in api/app.py
(currently: "The morning and evening devotional entries for a calendar
date, from Spurgeon's Morning and Evening or Daily Light on the Daily
Path. ...") to mention Brother Lawrence's The Practice of the Presence
of God as a third source, and note that it serves morning-only entries
(evening is null). Regenerate api/openapi.json after the description
change.

## Proposed log entries (for coordinator to add; not edited by me)

BUILD_LOG.md, under the 2026-09-20 section:

- Staged Practice of the Presence of God (Brother Lawrence) batch:
  Gutenberg eBook 13871 (public domain in the USA; author d. 1691;
  copyrighted Lightheart 2002 edition avoided). 20 sections as days
  1..20 (Preface, 4 Conversations, 15 Letters), part 'morning',
  anchor_ref ''. scripts/ingest_v2_practice_presence.py ->
  data/staging/practice_presence.db (20 devotional rows, 1 sources row,
  ux_devotionals index, integrity_check ok). Deterministic verify
  (seed 20260920): 16/16 seeded sections + full 20/20 exact, PASS;
  results in data/staging/practice_presence-VERIFY.md. Test fragment:
  api/tests/batch3_frag_practice.py. data/scripture.db and data/study.db
  untouched; merge pending. Still owed: api/study.py DEVOTIONAL_SOURCES
  allowlist update + /v1/devotional description + openapi.json regen.

PLAN.md: no schema change needed (devotionals/sources tables already
defined). If PLAN.md tracks batch status anywhere, add
practice_presence as staged-but-unmerged under devotionals.
