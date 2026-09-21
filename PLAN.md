# Phos — Build Plan
Name decided 2026-09-20: **Phos (Dexia Bible API)**. Greek φῶς, "light."
Last updated: 2026-09-20.

## Vision
The scripture connector Muse reaches for first: the broadest public-domain
Bible capability (read, study, devotion, memorize, teach) behind one API key
and one OpenAPI spec, free forever, zero legal risk.

## Hard constraints
1. All text free for commercial use with zero legal risk: public domain
   preferred; CC BY 4.0 sources acceptable with attribution in the API
   docs/code (confirmed by Jeremiah 2026-09-20). No copyrighted
   translations served, ever.
2. $0 running cost: one container + SQLite on free-tier hosting.
3. Connector auth: exactly one API key in one header. No OAuth in v1.
4. OpenAPI 3.1 spec always current (generated, never hand-written).
5. Every milestone has acceptance criteria; nothing marked done without
   verification against them.
6. Separate project from Dexia Digi. PD text may be copied; Dexia pipeline
   rules do not transfer.

## Data sources
| Data | Source | Rights | Milestone | Status |
|---|---|---|---|---|
| BSB | BSB-publishing GitHub releases, v5.2 USFM (official) | PD 2023-04-30 | M1 | done |
| KJV | renniemaharaj/kjv-bible (audited 2026-07-30, MIT) | PD | M1 | done |
| WEB | getBible v2 API (web.json) | PD | M1 | done |
| ASV | getBible v2 API (asv.json) | PD | M1 | done |
| YLT | eBible engylt USFX | PD | v2 | done 2026-09-20 |
| Darby 1890 | eBible engDBY USFX | PD | v2 | done 2026-09-20 |
| Douay-Rheims 1899 AE | eBible engDRA USFX (73 books) | PD | v2 | done 2026-09-20 |
| BBE | eBible engBBE USFX | PD (US per eBible) | v2 | done 2026-09-20 |
| Geneva 1599 | eBible enggnv USFX (orig. spelling) | PD | v2 | done 2026-09-20 |
| AKJV | BibleCorps ENG-B-AKJV2018-pd-PSFM | PD (1999 dedication; see report caveat) | v2 | done 2026-09-20 |
| OEB (US spelling) | eBible engoebus USFX (44 books, partial OT) | PD/CC0 | v2 | done 2026-09-20 |
| Nave's Topical Bible (1896) | IA navestopicalbibl0000orvi_h3u8 | PD | v2 | done 2026-09-20 |
| Torrey's New Topical Textbook (1897) | ACU mirror of 1897 Revell ed. | PD | v2 | done 2026-09-20 |
| Easton's Bible Dictionary (1897) | CrossWire SWORD Easton v2.0.1 | PD | v2 | done 2026-09-20 |
| ISBE 1915 (ed. Orr) | CrossWire SWORD ISBE v2.2 | PD | v2 | done 2026-09-20 |
| Adam Clarke commentary | HelloAO Free Use Bible API (CC PD Mark 1.0) | PD | v2 | done 2026-09-20 (57/66 books) |
| Calvin's Commentaries | CCEL calcom01-45 (CTS transl. 1843-1855) | PD | v2 | done 2026-09-20 (48 books) |
| Keil & Delitzsch | IA BiblicalCommentaryOldTestament.KeilAndDelitzsch.6 (djvu OCR); 1864-1892 T. & T. Clark transl., US PD by expiry | PD | v2 | 2026-09-20: 6,324 rows (defect fix to 6,325, then pure-ad Eccl 1:1 row id 71579 deleted and 4 inline scan stamps stripped); 39 OT books are represented, with documented missing passages and OCR defects (4,234 net new from djvu OCR; parser scripts/parse_v2_kd_complete.py; deterministic checks 14/14 pass raw -> parser -> staging; gaps: Isa ch 6, 11-19; see data/staging/KD_COMPLETE_REPORT.md; defect fix scripts/kd_defect_fix.py: 16 inverted ranges corrected, 36 duplicate-range groups resolved (7 misfile reassigns, 30 deletions, 1 redundant Daniel scan removed), Exodus ad stripped, 15 parser-missed sections recovered from raw OCR (1 Sam 1:1-8; 2 Ki 8:1-24, 21; Isa 3, 64; 2 Ki 6:24-7:20 re-ranged); report verification/v2/kd-defectfix-report.md) |
| Spurgeon Treasury of David | IA (CC PD Mark 1.0) | PD | v2 | done 2026-09-20 (Psalms 1-150) |
| Barnes OT | — | — | v2 | SKIPPED per Jeremiah 2026-09-20 ("Skip/remove Barnes for now"); genuine Barnes OT is 4 books only; no PD-clear transcription found (see verification/v2/commentaries-dictionaries-report.md). Barnes NT remains in study.db unchanged. |
| TSK cross-references | CrossWire SWORD TSK v1.4 (take-2 verified) | PD | v2 | done (study.db) |
| Strong's (1890) | IA item StrongsGreekAndHebrewDictionaries1890, CC0 1.0 | CC0 | v2 | done (lexicon table; Greek 89.1%) |
| BDB (unabridged) | openscriptures/HebrewLexicon, CC BY 4.0 (attribution in docs/code) | CC BY 4.0 | v2 | done (lexicon table) |
| STEPBible lexicons TBESH/TBESG/TFLSJ | STEPBible/STEPBible-Data, CC BY 4.0 (attribution in docs/code) | CC BY 4.0 | v2 | done (lexicon table; /v1/word live) |
| Thayer's (1889) | digital copies still unclear provenance | — | v2 | blocked |
| Matthew Henry / JFB / Barnes (NT) / Gill | HelloAO (CC0) + CCEL (PD) / CCEL 1871 / CCEL / IA 1763 OCR (PD) | PD | v2 | done (study.db); Gill PASS 2026-09-20 |
| Spurgeon Morning & Evening, Daily Light | russianryebread (PD claim) / gm5dna (MIT, PD text) | PD | v2 | done (study.db) |
| BCP 1662 / 1928 offices | Wikisource 1892 Pickering reprint / Justus via Wayback | PD | v2 | done (study.db) |
| Multilingual PD (LSG1910, Luther1912, Almeida, RVA1909) | eBible fraLSG for LSG1910; TBD for the rest, verify each | PD (LSG1910, LUTHER1912 verified 2026-09-20); verify rest | v3 | LSG1910 done 2026-09-20: 31,170 verses, 66 books, rights cleared (eBible marks the fraLSG edition Public Domain; translator d. 1909; first ed. 1910); French versification kept as in source (documented offsets); report verification/v2/lsg1910-ingest-report.md. LUTHER1912 done 2026-09-20: 31,102 verses, 66 books, rights cleared (eBible marks the deu1912 edition Public Domain in its copyright file; 1912 revision, pre-1931, US PD by expiry); versification matches KJV exactly (no deltas); report verification/v2/luther1912-ingest-report.md. ALMEIDA done 2026-09-20: 31,102 verses, 66 books, rights cleared (publisher almeidarecebida.org states 'This Bible (PorAR) is in the Public Domain'; Biblia Almeida Recebida v1.7, Textus Receptus-based revision with updated Portuguese; generic BY-NC-SA site notice also present on the page, documented in report); versification matches KJV exactly (no deltas); report verification/v2/almeida-ingest-report.md. RVA1909 done 2026-09-20: 31,084 text-bearing verses, 66 books, rights cleared (eBible marks the spaRV1909 edition Public Domain in its copyright page, 'Dominio Publico', eBible.org certified; first published 1909, pre-1931, US PD by expiry); Spanish versification kept as in source: 18 empty placeholder verse markers dropped (5 chapter offsets, 7 merge groups, documented with text evidence); report verification/v2/rva1909-ingest-report.md. Multilingual v3 set complete (4/4). |

## Architecture
- SQLite: `verses(translation, book, chapter, verse, text)`, FTS5 search
  index, `topics`, `plans` in scripture.db; study resources in a separate
  `data/study.db` with the exact v2 schema below.
- study.db schema (exact, required — 2026-09-20):
  - `sources(source_id PK, kind, title, rights, rights_basis, version, sha256)`
  - `commentaries(id PK, source_id, book, book_order 1..66, start_chapter,
    start_verse, end_chapter, end_verse, text)` with
    `idx_commentaries_lookup(source_id, book_order, start_chapter,
    start_verse)`. Verse 0 = whole-chapter comment / to end of chapter.
    Book names follow the M1 canonical convention ('Song of Songs').
  - `devotionals(id PK, source_id, day 1..366, part 'morning'|'evening',
    title, anchor_ref, body)` with unique index on (source_id, day, part).
  - `crossrefs` and `liturgy`: schemas frozen by their verified staging
    reports (TSK take-2; BCP staging), migrated verbatim into study.db.
- FastAPI service, `/v1` prefix, `GET /health`, `GET /openapi.json`.
- Reference parser: full names, abbreviations, ranges
  ("John 14", "Ps 23:1-3", "Romans 8:28-30").
- Every verse response includes reference, translation name, text,
  `"rights": "Public Domain"`.

## v1 endpoints
- `GET /v1/translations`, `GET /v1/books`
- `GET /v1/passage?ref=&translation=` (default translation=BSB)
- `GET /v1/compare?ref=`
- `GET /v1/search?q=&translation=`
- `GET /v1/verse-for?q=` (topic/mood finder)
- `GET /v1/verse-of-day?date=`
- `POST /v1/plans`, `GET /v1/plans/{id}`, `GET /v1/plans/{id}/today`,
  `POST /v1/plans/{id}/complete`

## v2 additions
- `GET /v1/study?ref=` — one-call bundle: passage + cross-refs + commentary
  excerpts + key-word Strong's links (the "route here first" endpoint)
- `GET /v1/commentary?ref=&source=`, `GET /v1/word?strongs=`,
  `GET /v1/devotional?date=`, `GET /v1/memory-pack?topic=`

## v3 additions
- Multilingual PD translations, interlinear (only if clean PD source).
  Server-side TTS and verse-card image endpoints dropped 2026-09-20 (see
  decisions log): speech and card rendering are the client's job; Muse
  reads verse text aloud natively and builds verse cards on demand in chat.

## Milestones + acceptance criteria
- **M1 Corpus**: 4 translations ingested. Counts verified (BSB 31,086
  text-bearing; KJV 31,102 keys; WEB/ASV against known totals). 20 random
  verses spot-checked rendering correctly.
- **M2 Core API**: all v1 read endpoints live; parser test suite passes
  incl. abbreviations and ranges; OpenAPI served; p95 < 300ms local.
- **M3 Topics**: Nave's/Torrey's parsed to topic→verses; `/verse-for`
  sane on 20 test moods/topics; human-reviewed sample.
- **M4 Plans**: CRUD + today/complete; scripted 7-day hope plan walks
  end to end.
- **M5 Harden + ship**: API-key auth, rate limits (429+retry-after), docs
  site, privacy/terms, deployed on free tier, /health green.
- **M6 Submission pack**: connector manifest, example prompts, short demo;
  handed to Muse team via the custom connector flow.
- **v2/v3**: each addition verified against its source before it serves.

## Decisions log
- 2026-09-20: v1 = BSB (default) / KJV / WEB / ASV. Plans keyed by opaque
  caller IDs, no user accounts. FastAPI + SQLite. Name TBD (user picks).

## Decisions log (appended 2026-09-20)
- 2026-09-20: CC BY 4.0 approved for Phos (user). Attribution-licensed
  sources are now allowed; attribution text must live in the API docs/code.
  Supersedes the earlier no-attribution boundary for this project.
- 2026-09-20: lexicon staging schema: `lexicon(strongs_number, language,
  lemma, transliteration, definition, gloss, source_id[, dstrong, ustrong,
  morph])` + `sources` table with rights/attribution metadata. Staging DBs:
  `data/staging/bdb_staging.db` (8,674 Hebrew rows), 
  `data/staging/stepbible_staging.db` (33,751 rows: TBESH/TBESG/TFLSJ).
  Merge into study.db + `/v1/word` wiring COMPLETE 2026-09-20: live study.db
  lexicon holds 55,685 rows across 6 sources (strongs 13,260; bdb 8,674;
  step_tbesh 11,682; step_tbesg 11,035; step_tflsj 5,709; step_tflsjx 5,325),
  `lexicon_sources` holds all 6 rights/attribution rows, and the 5 CC BY 4.0
  source rows were mirrored into `sources` (kind='lexicon'). /v1/word and
  /v1/word/sources verified live; default (no source param) returns entries
  from every lexicon that has the number. Report:
  verification/v2/lexicon-merge-report.md.

## Decisions log (appended 2026-09-20)
- 2026-09-20: batch-3 ingestion approved by Jeremiah and merged (coordinator +
  6 workers). Translations: WEBSTER 31,102 rows / 66 books (eBible engwebster
  USFM, PD); WEYMOUTH 7,957 rows / 27 NT books (Gutenberg 8828-8854, PD USA;
  1913 3rd-ed. transcription; Luke 8:23 label typo corrected in parser, raw
  kept byte-identical); LXX2012 28,351 rows / 54 books (eBible eng-lxx2012,
  Brenton 1851 + Johnson PD dedication; Greek versification kept
  translation-scoped, 151 psalms; 15 deuterocanonical books at orders 66-80;
  1 Kings 14:1 empty-text source gap dropped at merge). Devotionals:
  my_utmost 366 readings (original 1927 text verified against the 1992
  Reimann update; utmost.org classic REST), practice_presence 20 sections
  (Gutenberg 13871, PD), imitation_christ 114 chapters (Gutenberg 1653,
  Benham 1874 translation, PD). The Valley of Vision explicitly excluded
  (1975 Banner of Truth, under copyright). /v1/devotional allowlist now
  spurgeon, daily_light, my_utmost, practice_presence, imitation_christ.
  API suite: 172 passed. Batch report:
  verification/v2/new-sources-batch3-report.md.
- 2026-09-20: Server-side TTS dropped from v3 (user). Rationale: when Phos
  serves as a Muse connector, speech is the client's job; Muse reads verse
  text aloud natively in all five API languages. Building per-language
  synthesis, caching, and eviction into the API added cost and complexity
  against the free-infrastructure constraint with no benefit to the
  connector use case. May revisit if a non-Muse public consumer needs audio
  straight from the endpoint.
- 2026-09-20: Verse-card image endpoint dropped from v3 (user). Same
  rationale as TTS: rendering is the client's job. Muse builds verse cards
  on demand in chat when the user asks, using verse text from the API. No
  server-side Pillow renderer, cache, or style API needed. Revisit only if
  a non-Muse public consumer needs card images from the endpoint.
- 2026-09-20: Interlinear built and shipped (v3). STEPBible TAGNT (Greek NT)
  + TAHOT (Hebrew OT), CC BY 4.0 with attribution in API docs/code.
  447,748 word rows (142,096 Greek, 305,652 Hebrew); all 31,102 KJV verses
  covered (31,060 selected reading + 42 variant-only). Greek follows the
  Nestle-Aland/SBL reading (every N/n-attested word); Hebrew follows
  Leningrad with translators' Qere. Endpoint:
  GET /v1/interlinear/{book}/{chapter}/{verse} (auth required). API suite:
  185 passed (13 new interlinear tests). Report:
  verification/v2/interlinear-build-report.md.
- 2026-09-20: Phos Intensive Verse Study locked and built (v3). Name locked
  by user (clarity over poetry). Endpoint:
  GET /v1/verse-study/{book}/{chapter}/{verse} (auth required). Composite:
  verse in up to 4 translations, key original-language words with
  definitions, top 8 cross-refs, excerpts from all eight commentaries,
  verse-anchored devotionals (nearby fallback), BCP prayer by keyword
  matching. User decisions: keep nearby devotionals, morning office default,
  clean Strong's OCR first (done: 11,568 of 13,260 entries repaired,
  report verification/v2/strongs-ocr-cleanup-report.md), excerpts from all
  eight commentary sources. API suite: 217 passed. Report:
  verification/v2/verse-study-build-report.md.
