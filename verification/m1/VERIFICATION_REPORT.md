# M1 Verification Report — Phos (Dexia Bible API)

**Verification date:** 2026-09-20 (America/Los_Angeles)
**Verifier:** automated checks + manual review of `scripts/ingest_m1.py` (read end to end)
**Raw evidence:** `verification/m1/raw/` (26 files) + `verify_structure.py`, `verify_diffs.py`, `verify_random.py` in `verification/m1/`
**Verdict: M1 data corpus — PASS (with noted non-blocking gaps and hardening proposals)**

## PLAN.md M1 acceptance criteria (verbatim)
> 4 translations ingested. Counts verified (BSB 31,086 text-bearing; KJV 31,102 keys; WEB/ASV against known totals). 20 random verses spot-checked rendering correctly.

## Per-criterion results

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | 4 translations ingested | PASS | `verses` table: BSB 31,086 / KJV 31,102 / WEB 31,095 / ASV 31,086. Total 124,369 rows. Raw-to-DB tallies match exactly per translation (raw_hashes.txt, raw_vs_db_tally.txt). |
| 2 | Counts verified | PASS | KJV: 31,102 raw non-empty keys == DB 31,102. BSB: 31,086 raw `\v` markers == DB 31,086 text-bearing. WEB: 31,095 == DB. ASV: 31,086 == DB. (counts.txt) |
| 3 | 20 random verses spot-checked | PASS | 24/24 pass (20 random + 4 fixed), deterministic seed 20260920, spread 6 BSB / 6 KJV / 4 WEB / 4 ASV. Text pulled from RAW SOURCE files with independent readers (not ingest parsers) and compared to DB. KJV/WEB/ASV compared exact (whitespace-normalized); BSB compared as word sequences after marker stripping. (random_checks.txt) |
| 4 | All 66 books, canonical order | PASS | All 4 translations: 66/66 books, canonical order matches exactly. (books_*.txt) |
| 5 | Chapter counts match source | PASS | 264/264 book chapter counts match raw sources (MAX(chapter) in DB vs raw). (chapter_count_compare.txt) |
| 6 | No duplicate verse keys | PASS | 0 duplicates across (translation, book, chapter, verse). (duplicates.txt) |
| 7 | No empty/null/whitespace texts | PASS | 0 rows with NULL/empty/whitespace-only text. (empty_texts.txt) |
| 8 | No USFM/footnote markup leakage | PASS | 0 rows matching USFM backslash-marker, HTML/XML-tag, or curly-brace patterns. (markup_leakage.txt) |
| 9 | FTS5 returns expected verses | PASS | Queries return correct verses: "in the beginning" -> Gen 1:1 BSB; "shepherd" -> Gen 29 BSB; "lovingkindness" -> Hosea 2:19 etc. KJV; "grace" -> 1 Cor 1:3 WEB. (fts_checks.txt) |
| 10 | PRAGMA integrity_check | PASS | `ok`. (integrity_check.txt) |
| 11 | WEB 7 / ASV 16 verse-key diffs vs KJV | PASS (genuine versification) | WEB: 7 missing, 0 extra. ASV: 16 missing, 0 extra. ALL 23 verses verified ABSENT in the raw getBible source files (not parser drops). These are the classic textual-critical omissions (Acts 8:37, John 5:4, Mark 9:44/46, Matt 18:11, etc.). Data is not lost: e.g. the Romans doxology (16:25-27) is preserved in WEB appended to 14:23, the critical-text placement (verified word-for-word in DB). (verse_diffs_*.txt, diff_raw_presence.txt, verse_diffs_context.txt) |
| 12 | Commercial-use rights per corpus | PASS | BSB: public domain (publisher dedication 2023-04-30, independently re-verified on berean.bible/terms.htm 2026-09-20). KJV: public domain text; repo README asserts MIT at ingested commit; UK-only Crown-copyright caveat noted. WEB: public domain per ebible.org (sell/redistribute freely). ASV: public domain (1901). getBible: no second copyright layer, no fees/quotas; condition to preserve per-translation copyright metadata. Full record: provenance.md. |
| 13 | Provenance recorded (URLs, versions, hashes, dates) | PASS with gap | Versions, commit, hashes, retrieval date (2026-09-20) recorded. GAP: exact download URLs for the BSB v5.2 release asset and getBible v2 JSONs were not logged by the ingest session; content pinned by SHA-256. Record URLs on any future re-download. |

## What ingest_m1.py actually does (lossy transforms — verified by reading the full script)
- **BSB:** footnotes dropped ENTIRELY (`\f ... \f*` DOTALL) — note text (e.g. "Literally day one") does not reach the DB, by design; headings/section markers dropped; `\marker` sequences, `|` removed; whitespace collapsed. Spot-verified Gen 1:5: verse wording preserved word-for-word minus footnote. Verse ranges (`\v 3-4`) supported but 0 present in v5.2. "Song of Solomon" alias normalized to "Song of Songs" (N/A for BSB; applies to KJV).
- **KJV:** whitespace collapse only; empty texts skipped; `kjv.json` aggregate file skipped.
- **WEB/ASV:** whitespace collapse only; empty texts skipped.
- **DB schema:** `verses(translation, book, book_order, chapter, verse, text)` — NO constraints, NO indexes (pre-verification), `book_order` from a hardcoded canonical list; FTS5 with porter tokenizer over `text`.

## Indexes added (non-destructive, documented)
- `idx_verses_lookup ON verses(translation, book, chapter, verse)` — passage/reference lookups (M2 `/v1/passage` will need this).
- `idx_verses_book ON verses(translation, book_order, chapter)` — chapter scans.
- Row count verified unchanged (124,369) after creation. Backup of pre-index DB noted in raw (hash recorded).

## Proposed hardening (NOT applied — needs parent/user decision, some require rebuild)
- `UNIQUE(translation, book, chapter, verse)` + `NOT NULL` on all columns.
- A `translations` table carrying per-translation copyright/attribution metadata (getBible's "preserve and honor" condition + API rights display), referenced by `verses.translation`.
- A `books` table for `book_order` instead of the hardcoded list in the ingest script.
- Diff BSB v5.2 against the publisher's v5.9 USFM (Jeremiah's Dexia BSB was verified against v5.9) and decide which edition ships; current claim is v5.2 only.
- KJV in this DB is from `renniemaharaj/kjv-bible` @ 88723a4, NOT Jeremiah's corrected Dexia KJV file. Edition-level 1769 accuracy is NOT established by this verification.

## Data-quality or rights blockers
**None.** No data loss found, no markup leakage, no commercial-use blockers. The premature "M1 complete" claim is now backed by this evidence.

## Open non-blocking gaps
1. Exact download URLs for BSB zip asset and getBible JSONs not recorded (hashes recorded instead).
2. getBible usage agreement expects hash-validation of cached copies and metadata preservation — fold per-translation rights metadata into M2 API responses.
3. UK-only Crown copyright caveat on KJV distribution directed at the UK.
4. KJV repo README asserts MIT but no standalone LICENSE file was present in the checkout.

*Nothing in this report is legal advice.*
