# V2 Study Data — Final Verification Report

**Date:** 2026-09-20
**Artifact:** `data/study.db` (141 MB), built by `scripts/merge_v2_study.py`
from independently verified staging databases.
**Scope:** DATA ONLY. No API endpoints were added or changed.

## Final verdicts

| Source | Verdict | Rows in study.db |
|---|---|---|
| Matthew Henry, Complete Commentary | **PASS** | 5,387 |
| JFB, Commentary Critical and Explanatory (1871) | **PASS** | 2,046 |
| Barnes' New Testament Notes (NT only) | **PASS** | 7,354 |
| Treasury of Scripture Knowledge (CrossWire v1.4, take-2) | **PASS** | 573,192 |
| Spurgeon, *Morning and Evening* (1866) | **PASS** | 732 |
| Bagster, *Daily Light on the Daily Path* (1875) | **PASS** | 732 |
| BCP 1662, Morning/Evening Prayer | **PASS** | 332 |
| BCP 1928 (US), Morning/Evening Prayer | **PASS** | 371 |
| Strong's Hebrew/Greek dictionaries (1890 text) | **SKIP — not verified** | 0 |
| BDB Hebrew Lexicon (1906) | **SKIP — not verified** | 0 |
| Thayer's Greek Lexicon (1889) | **SKIP — not verified** | 0 |
| Gill's Exposition of the Entire Bible (1763) | **PASS** | 32,036 |

## Commentaries (new work this pass)

Staged by `scripts/build_v2_commentaries.py` into
`staging/commentaries_v2.db` using the **exact PLAN.md study.db schema**
(`commentaries(id, source_id, book, book_order 1..66, start_chapter,
start_verse, end_chapter, end_verse, text)` +
`idx_commentaries_lookup(source_id, book_order, start_chapter,
start_verse)`). Section titles are folded into `text` as the first
paragraph (the schema has no title column); this is a documented encoding,
not a schema deviation. Verse 0 = whole-chapter comment.

- **Matthew Henry:** HelloAO `matthew-henry` (CC0) 1,166 chapters + CCEL
  gap-fill (PD, "Public domain. May be copied and distributed freely")
  23 chapters = 1,189 chapters, 5,387 rows. Verse-item end verses inferred
  as next-start-minus-1 (documented).
- **JFB:** CCEL 1871 proofed text, 1,189 chapters, 2,046 rows. 8
  cross-chapter sections (e.g. `Isa 8:1-9:7`) stored with true
  end_chapter/end_verse parsed from the original ref string.
- **Barnes:** CCEL New Testament Notes only, 27 books / 260 chapters,
  7,354 rows. Full-Bible Barnes: no faithful PD transcription located
  (Sacred Texts Cloudflare-blocked, CrossWire NT-only) — source id stays
  `barnes_nt`.

**Verification performed:**
- All (book, chapter, verse) bounds validated against the live KJV corpus
  via `api/db.py` (read-only). 2 JFB rows skipped and logged: `Jer 21:1-44`
  and `Ac 15:36-46` are print errors *in the 1871 source text itself*
  (Jer 21 has 14 chapters' verses, Acts 15 has 41) — verified against raw
  `jfb_ccel_1871.txt` lines 91976 and 161724. Honest loss, not misattributed.
- Zero-hit scans: 0 HTML tags, 0 HTML entities, 0 lowercase-USFM markers.
  One CCEL transcription artifact (`\Ro` in Barnes Acts 2:23) kept
  source-faithful and documented (same artifact class as the Luke 6:40
  `\\` case from the earlier pass).
- **Seeded raw-to-DB spot checks (seed 20260920), 12 per source: 36/36
  PASS** — independent re-read of raw JSONs (never via the build script),
  checking ref bounds, raw-body containment in DB text, and title placement.
  Evidence: `verification/v2/raw/commentaries/spot_checks.json`.
- `PRAGMA integrity_check = ok`. No empty texts, no inverted ranges, no
  book_order outside 1..66.
- Supersedes the quarantined `staging/INVALID_PROVISIONAL_commentaries.db`
  (invented schema), which must never be used.

## Merged sources (from earlier verified staging)

- **TSK cross-refs:** `staging/crossrefs2.db` take-2 (PASS per
  `TSK_VERIFICATION_TAKE2.md`; 10/10 raw-to-DB checks). Take-1
  (`staging/crossrefs.db`) was rejected for 11.7% silent misattribution
  and was **never merged**. Migrated verbatim: 573,192 rows.
- **Devotionals:** `staging/devotionals.db` (PASS per
  `devotionals_staging_report.md`; 12/12 seeded checks per source).
  Migrated verbatim: 1,464 rows (732 Spurgeon + 732 Daily Light).
- **Liturgy:** `staging/liturgy.db` (PASS per `liturgy_staging_report.md`;
  20/20 seeded checks). Migrated verbatim except one mechanical rename:
  the staging `sources` table is now `liturgy_sources` to avoid colliding
  with the global PLAN.md `sources` table; the FK was rewritten to
  `liturgy_sources(id)`. 703 liturgy rows, 2 edition rows.
- **Global `sources` table** (exact PLAN.md schema): 8 rows with rights
  metadata, versions, and SHA-256 pins for every ingested source.
- **Merge fidelity:** per-table counts match staging exactly; 5/5 random
  row samples byte-identical per table; all commentary/devotional
  `source_id` values resolve in `sources`; all liturgy FKs resolve;
  `PRAGMA integrity_check = ok`.

## scripture.db untouched

Opened read-only throughout (via `api/db.py` / URI `mode=ro`). Still
124,369 rows, `PRAGMA integrity_check = ok`, mtime predates this work.

## Lexicon verdicts (updated 2026-09-20 — CC BY 4.0 approved, both ingested to staging)

On 2026-09-20 Jeremiah approved CC BY 4.0 sources for Phos (attribution
lives in the API docs/code), superseding the earlier no-attribution
boundary recorded for this project. Both sources below are CC BY 4.0,
parsed into staging DBs, verified, and ready for merge into `study.db`.

- **BDB Hebrew (OpenScriptures HebrewLexicon) — PASS.** `HebrewStrong.xml`
  (commit `21c9add`, 2019-09-02): all 8,674 entries H1–H8674 recovered,
  zero duplicates, zero empty definitions, 12/12 seeded raw-to-DB checks
  PASS. Staging: `data/staging/bdb_staging.db` via `scripts/ingest_bdb.py`.
- **STEPBible extended lexicons — PASS.** TBESH 11,682 rows (Hebrew,
  extended Strong's incl. affixes), TBESG 11,035 rows (Greek, Abbott-Smith),
  TFLSJ 5,709 + TFLSJ extra 5,325 rows (Greek, full LSJ formatted).
  Total 33,751 rows; 48/48 seeded raw-to-DB checks PASS (12 per file).
  Staging: `data/staging/stepbible_staging.db` via
  `scripts/ingest_stepbible.py`. Commit `b99716b0` (2026-09-18).
  TFLSJ extra has 77 name rows (G21425+) with blank definitions in the
  source itself — honest source gaps, documented.
  `PRAGMA integrity_check = ok` on both staging DBs.

Required API docs/code attribution (both):
- "Brown-Driver-Briggs Hebrew lexicon XML transcription by the Open
  Scriptures Hebrew Bible Project, licensed under CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/)."
- "STEPBible lexicon data (TBESH, TBESG, TFLSJ), Tyndale House,
  Cambridge, licensed under CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/). Source:
  https://github.com/STEPBible/STEPBible-Data, www.STEPBible.org."

Not yet done: merging staging DBs into `data/study.db`, `/v1/word` lexicon
endpoint wiring (endpoint exists in PLAN; data source pending), Thayer's
Greek (1889) — digital editions still lack a verified license → SKIP.

- **Strong's (1890) digital editions:** the IA CC0 scan (Strong's Greek +
  Hebrew dictionaries, CC0 1.0 item license) passed the rights gate and is
  being ingested by a parallel agent; `openscriptures/strongs` still shows
  no license file → not used.

## Gill's Exposition — PASS (gap closed 2026-09-20)

Source: Internet Archive `john-gills-commentary-on-the-whole-bible`
djvu.txt OCR (49,188,464 bytes, SHA-256
`0bd13225955a61956d826299122e7d8946a7c7b81a17e9e70395576e32c073ea`).
John Gill d. 1771; the 1763 edition is public domain. The IA OCR is a
mechanical reproduction of the PD text; commercial use OK, no attribution
required.

Ingested by `scripts/ingest_v2_gill.py` (rerunnable, deletes/reinserts only
`source_id='gill'`): 32,036 rows (66 book intros, 1,044 chapter intros,
30,926 verse notes). Verse-note coverage: 30,926/31,102 KJV verses (99.4%).

The IA file has scrambled page regions (whole sections displaced, single
pages interleaved across books, e.g. Isaiah pages inside Exodus, a
Leviticus page inside Jude). The parser handles this by:
- Parsing book/chapter identity from introduction titles themselves, not
  positional anchors.
- Accepting verse headings only via contextual validation (next line is
  INTRODUCTION, "Ver. N." for its verse, or exact expected-next-verse).
- KJV-validating "Ver. 1." splits (rejects foreign interleaved notes).
- Truncating verse blocks at foreign "Ver. W." markers; rehoming 62
  orphaned notes to their KJV-validated verses (e.g. Jude 1:1, 3 John 1:1).
- Dropping 45 unverified foreign-page blocks and 6 citation-like false
  headings; all logged in `verification/v2/raw/gill_skips.log` (293 lines).

176 verses honestly missing (pages lost from the OCR, e.g. Luke 2:12-52).
12/12 seeded raw-to-DB checks PASS. Zero page-marker/running-head leakage.
`PRAGMA integrity_check = ok`. `scripture.db` untouched (124,369 rows).

Known limitation: rare foreign prose without "Ver." markers may remain in
a verse block (e.g. Jude intro fragment in Leviticus 25:49); not reliably
separable from legitimate cross-references.

## Known limitations (carried forward, not blocking)

1. Daily Light: 529 of 5,656 item references are reconstructions from verse
   text, not the transcription's printed references (fully documented in
   `verification/v2/raw/devotionals/`); 10 items have `.` as verse text.
2. MH HelloAO verse-range ends are inferred (next-start-minus-1); HelloAO
   edition unpinned (CC0) vs CCEL proofed — overlapping passages not diffed.
3. TSK: 6.1% of phrases honestly unattributed (skipped); phrase-less blocks
   may misattribute to an adjacent verse; Proverbs 10-24 and Isaiah 24-27
   have no TSK data in the SWORD source.
4. Liturgy: 30-day Psalter and lectionary tables excluded by design; page-57
   scope and 1662 rubric-vs-text classification carry the staging report's
   open questions.
5. Historical-edition comparisons for JFB/Barnes not performed.

## Reproducibility

- `python3 scripts/build_v2_commentaries.py` → `staging/commentaries_v2.db`
- `python3 verification/v2/verify_v2_commentaries_final.py` → spot checks
- `python3 scripts/merge_v2_study.py` → `data/study.db`
- Stdlib + sqlite3 only. `data/study.db` refuses to build if it exists.
