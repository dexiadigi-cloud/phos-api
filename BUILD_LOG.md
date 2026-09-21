# Scripture Desk — Build Log

## 2026-09-20
- Goal created (`goal_5c94f712e6b8`, slug `scripture-desk-connector`).
- Repo scaffolded at `~/workspace/scripture-desk/` (`data/raw`, `scripts`,
  `api`, `docs`). PLAN.md written.
- M1 started: fetching BSB + KJV from the dexia-digi GitHub mirror;
  WEB/ASV sources being verified.

- M1 CORPUS COMPLETE. All 4 translations ingested into `data/scripture.db`
  (124,369 rows, FTS5 indexed, 30MB) via `scripts/ingest_m1.py`:
  BSB 31,086 (exact) from BSB-publishing v5.2 USFM release (official PD);
  KJV 31,102 (exact) from renniemaharaj/kjv-bible (audited, MIT);
  WEB 31,095 and ASV 31,086 from getBible v2 API (PD).
  Spot checks (Gen 1:1, Gen 1:5, John 3:16 x4) render clean; footnote/marker
  leakage asserts pass; "Song of Solomon" aliased to "Song of Songs".
  WEB/ASV are 7-16 verses under 31,102 (minor versification differences).
- Pivot note: the dexia-digi GitHub mirror is private (raw 404s), so the
  Mac-side verified BSB/KJV files could not be pulled VM-side. Used the
  official BSB release + independently audited KJV instead. When Jeremiah is
  back at the Mac (after Sep 27), diff his verified files against these and
  swap if he prefers.

## 2026-09-20 — Name research
- "Graphe" is TAKEN in the Bible-software space: active Electron Bible study app
  (github.com/claudioscheer/graphe, updated ~49 days ago) with Strong's numbers,
  cross-references, commentaries — directly overlaps planned v2 features.
  Also an old SourceForge "Graphé" Bible app and a Flutter "graphe" Bible app.
  Verdict: do not use bare "Graphe"; always qualified ("Dexia Graphe") at most.
- "Phos" (Greek: light) is CLEAR of Bible-software collisions. Nearest neighbor
  is Xiphos (open-source Bible study software, different name/pronunciation).
  Minor: abnerscunha/phos-bible is a stale personal Next.js starter, not a product.
  Bonus: "Phos" ties to Light & Legacy branding and Wicklet the lamp.
- Jeremiah's proposed pattern (distinctive name + "Dexia Bible API" descriptor)
  matches the Logos/Accordance convention. Recommended: Phos (Dexia Bible API).

## 2026-09-20 — Name DECIDED: Phos (Dexia Bible API)
- Jeremiah approved "Phos (Dexia Bible API)". Greek φῶς = "light".
- "Graphe" rejected: active Bible study app already uses it (same feature space).
- Naming pattern (distinctive name + clear descriptor) follows Logos/Accordance.
- Logo design: queued as future step, Jeremiah wants an amazing one.

## 2026-09-20 — Logo v1 generated
- Jeremiah's concept: gold oil-lamp silhouette (Wicklet-like) on Dexia indigo.
- Generated via media pipeline: assets/media-generation-phos-logo-v1-*.webp
  (gold lamp + flame on deep indigo, rounded-square app icon, no text).
- Awaiting his reaction; refinements and a wordmark version possible next.
- Logo v2: refined/polished per Jeremiah — sleeker gold lamp with classical
  detailing, "PHOS" in Greek-inspired serif below, same indigo.
  File: assets/media-generation-phos-logo-v2-*.webp
- Logo local-model request: probed Mac via tunnel proxy 2026-09-20 ~08:10 PDT.
  Opencode server (100.88.120.23:4096) is UP (401 = alive, needs password).
  Draw Things (port 7860) NOT reachable from VM (connection failed; likely
  localhost-bound or app/toggle off — cannot touch it remotely per standing rules).
  Blocked on: OPENCODE_PW (non-persistent, never stored) to dispatch a Mac-side
  render agent. Waiting on Jeremiah: paste password, or render VM-side instead.

## 2026-09-20 — Icon v3 rendered on Mac local model (APPROVED DIRECTION)
- Jeremiah supplied fresh opencode password; auth via opencode_client.py worked first try.
- Route: Mac device `files.read` pulled the exact render invocation from
  brand/DRAW-THINGS.md (verified Draw Things txt2img client
  `txt2img_color_raw` in pipelines/generate_story_art.py — reused verbatim,
  no improvised client).
- Render: Flux.2 Klein (flux_2_klein_4b_q8p.ckpt), txt2img, 1024x1024,
  steps 8, cfg 1.0, sampler "DPM++ 2M AYS", random seed.
- Prompt: flat vector-style silhouette icon — ancient clay oil lamp with small
  flame, lamp+flame as one solid radiant gold silhouette, crisp clean edges,
  no internal detail, no gradients, no shading, centered on flat deep indigo
  blue background. No text.
- Output: assets/phos-icon-v3-local-1024.png (1,063,899 bytes), rendered
  2026-09-20 ~08:10 PDT, retrieved via device files.upload.
- v1/v2 (media pipeline) NOT approved; v3 is the current candidate per his
  "no text, all silhouette" direction. Jeremiah has final call.

## 2026-09-20 — Icon v3 flame QA (Jeremiah caught it)
- Jeremiah: make sure the flame is in the right place for an ancient oil lamp.
- He is right. In v3 the flame rises from the top center of the lamp body
  (where the fill hole would be), which reads as a genie/magic lamp. On a
  real ancient clay oil lamp the flame burns at the wick, which sits in the
  tip of the spout/nozzle, not the top center.
- Fix queued: re-render on the Mac with the flame emerging from the wick at
  the spout tip. Blocked on a fresh opencode password (previous one was
  single-use, never stored).

## 2026-09-20 — Icon v4 rendered, REJECTED on QA
- Jeremiah supplied a fresh password; Mac agent re-rendered with flame at the
  spout (assets/phos-icon-v4-local-1024.png, 877,002 bytes, sha256
  01708b776b7b0d834f81f22a81988e5e2edb17656235e51fed4d5fa9a328c893).
- QA failed: the flame landed on the handle end, not the spout tip. Discarded,
  not shown to Jeremiah.

## 2026-09-20 — Icon v5 rendered, flame at spout tip
- First v5 session flailed (wrote only prompt.txt, no PNG); killed per the
  cascade rule. Fresh session with a narrower brief (explicit python
  discovery + verbatim prompt) rendered cleanly.
- assets/phos-icon-v5-local-1024.png (833,483 bytes, sha256
  27c50f94116c7dc0a3de5efd61ad36614efb205a2145bc51ca729d437311105f).
- Flame now burns at the very tip of the left-pointing spout, where the wick
  sits on a real ancient oil lamp. Shown to Jeremiah for verdict.

## 2026-09-20 — Icon v5 ACCEPTED as final candidate (for now)
- Jeremiah: "Let's go with that for now." Accepted v5 as the current icon.
- Saved: assets/phos-icon-v5-final-1024.png (copy of v5, sha256
  27c50f94116c7dc0a3de5efd61ad36614efb205a2145bc51ca729d437311105f)
  plus assets/phos-icon-v5-final-prompt.txt with the exact render prompt and
  settings. Prompt recovered from the Mac:
  /Users/jeremiahlee_macbookpro/dexia/tmp/phos-icon-v5/prompt.txt.
- Historical note: this prompt text was briefly attributed as lost after the
  first v5 session flailed; it was found in the Mac tmp dir on 2026-09-20
  and saved. Earlier BUILD_LOG wording suggesting the prompt was unknown is
  superseded by the final-prompt.txt file.
- Production sizes not yet created; will confirm deliverables when requested.

## 2026-09-20 — M1 VERIFIED (genuinely, this time)
- Full independent verification completed: report at
  verification/m1/VERIFICATION_REPORT.md with 26 raw evidence files.
- Verdict: PASS on all 13 criteria. Counts confirmed by my own spot check
  (BSB 31,086 / KJV 31,102 / WEB 31,095 / ASV 31,086 = 124,369 rows;
  PRAGMA integrity_check = ok; Gen 1:1 BSB + John 3:16 KJV read correctly).
- 24/24 random source-to-DB comparisons pass (seed 20260920).
- WEB 7 / ASV 16 verse-key diffs vs KJV confirmed genuine versification in the
  raw getBible sources, not data loss (Romans doxology preserved in WEB 14:23).
- Rights: all four corpora clear for commercial use. BSB public domain
  (publisher dedication 2023-04-30, re-verified on berean.bible/terms.htm today).
  KJV text PD; WEB PD; ASV PD (1901). getBible adds no copyright layer; its
  condition to preserve per-translation rights metadata should be honored in M2.
- Indexes added (non-destructive): idx_verses_lookup, idx_verses_book.
  Row count unchanged at 124,369.
- Honest gaps: (1) exact BSB v5.2 asset / getBible download URLs not logged by
  the ingest session, content pinned by SHA-256 instead; (2) BSB v5.2 not yet
  diffed against publisher v5.9 (Jeremiah's Dexia-verified edition); (3) this
  KJV is renniemaharaj/kjv-bible @ 88723a4, not Jeremiah's corrected Dexia KJV,
  edition-level 1769 accuracy not established.
- Proposed hardening (UNIQUE/NOT NULL constraints, translations rights table,
  books table) deferred to M2.
- The earlier premature "M1 complete" claim is now backed by evidence.

## 2026-09-20 — M2 built: Phos FastAPI service (v1)
- Dir: api/ — parser.py (reference parser: aliases incl. Ps/Psalm, Song of
  Solomon->Song of Songs, 1John/1 John/I John, chapter/verse/chapter-range/
  multi-chapter/comma-list refs; DB-backed bounds validation -> RefError),
  db.py (read-only SQLite, mode=ro, per-request connections, FTS5 search,
  offset verse lookup), translations.py (per-translation rights metadata from
  provenance.md, incl. getBible preservation condition), app.py (FastAPI,
  OpenAPI 3.1.0, X-API-Key header auth w/ constant-time compare, 401 on
  missing/wrong; /health no-auth), gen_openapi.py, requirements.txt,
  README.md, openapi.json (3.1.0, summaries+descriptions+examples on all 7 ops).
- Endpoints: /health, /v1/translations, /v1/books, /v1/passage,
  /v1/compare (genuine WEB/ASV verse-key gaps -> null text + note, not errors),
  /v1/search (FTS5 porter, sanitized quoted-term MATCH, <em> snippets, 1-100
  limit), /v1/verse-of-day (SHA-256 of 'YYYY-MM-DD|TRANSLATION' -> offset).
- Design: get_bounds uses MAX(CAST(verse AS INTEGER)) not COUNT(*) because
  WEB/ASV genuinely skip verse keys; parser validates against the requested
  translation's actual bounds; DB opened immutable-mode read-only.
- Tests: 41 passed (api/tests/, pytest). Covers parser cases + invalid refs,
  auth accept/reject, every endpoint happy path, 400/404/422 paths, votd
  determinism (two dates vs DB-computed offsets), openapi 3.1 check.
- Live smoke test via uvicorn :8123: health, passage (Rom 8:28-30 BSB),
  compare (Acts 8:37 KJV text + WEB null), search, votd, 401 — all OK.
- Run: cd api && python3 -m venv .venv && .venv/bin/pip install -r
  requirements.txt && PHOS_API_KEY=<key> .venv/bin/python -m uvicorn app:app
  --host 127.0.0.1 --port 8000
- Gaps/notes: server refuses to start without PHOS_API_KEY (loud fail, by
  design); verse-of-day accepts optional ?day= for testing; no topic/reading
  plan endpoints (later milestones); openapi.json is generated, not hand-written.

## 2026-09-20 — M2b DONE: topic/mood discovery + reading plans
- Topics: api/data/topics.json — 64 curated topics (3-8 verse refs each),
  14 moods mapped onto topics. Endpoints: GET /v1/topics,
  GET /v1/topics/{id}, GET /v1/moods, GET /v1/moods/{mood}.
- Reading plans: api/data/plans.json generated programmatically by
  api/data/gen_plans.py from the DB's chapter lists (bible-in-a-year/365,
  new-testament-90/90, psalms-proverbs-31/31, gospels-30/30). Endpoints:
  GET /v1/reading-plans, GET /v1/reading-plans/{id},
  GET /v1/reading-plans/{id}/today (stateless day computation from
  start_date; 400 with a finished message past the plan length),
  POST .../checkin and GET .../progress backed by api/data/progress.db
  (checkmarks only, no scripture; PHOS_PROGRESS_PATH-overridable).
- Ref validation: api/data/validate_refs.py resolves all 909 refs through
  parser.py against the live BSB DB and exits 1 on any invalid ref. First
  run caught 43 chapter-range hits in the NT plans where BSB omits
  textual-critical verse keys (Matthew 17:21, Mark 9:44/46, John 5:4,
  Acts 8:37, etc.) — same set as WEB/ASV; validator now checks
  chapter-level refs for chapter existence instead of every verse key.
  fetch_spans returns the verses that exist. Every topic verse's actual
  BSB text was eyeballed for topical fit; none needed swapping.
- Tests: 68/68 pass (41 M2 + 27 new in tests/test_topics_plans.py).
- openapi.json regenerated (3.1.0, 16 paths). README endpoint table updated.

## 2026-09-20 — v2 study data merged (DATA ONLY, no endpoints)

`data/study.db` (141 MB) created by `scripts/merge_v2_study.py` from four
independently verified staging DBs. Full report:
`verification/v2/VERIFICATION_REPORT.md`.

- Commentaries (new this pass, `scripts/build_v2_commentaries.py`, exact
  PLAN.md schema, 36/36 seeded raw-to-DB spot checks PASS):
  Matthew Henry 5,387 rows (HelloAO CC0 + CCEL PD gap-fill, 1,189 ch),
  JFB 2,046 rows (CCEL 1871, incl. 8 true cross-chapter ranges),
  Barnes NT 7,354 rows (CCEL; full-Bible Barnes not found, id stays
  `barnes_nt`). 2 JFB rows skipped: print errors in the 1871 source itself
  (Jer 21:1-44, Ac 15:36-46). Section titles folded into `text` first
  paragraph (no title column in schema).
- Merged verbatim: TSK take-2 cross-refs 573,192 (take-1 rejected, never
  merged), devotionals 1,464 (Spurgeon + Daily Light), BCP 1662/1928
  liturgy 703 rows (staging `sources` renamed `liturgy_sources`).
- Global `sources` table: 8 rows of rights metadata with SHA-256 pins.
- Merge fidelity: counts + 5/5 row samples identical per table; FKs resolve;
  integrity_check ok; zero markup leakage.
- Lexicons (Strong's/BDB/Thayer's): works are PD but no digital edition
  verified clean (OpenScriptures HebrewLexicon is CC BY 4.0; openscriptures/
  strongs shows no license) — skipped per the rights gate, nothing ingested.
- Gill's Exposition (1763, IA OCR): PASS 2026-09-20 — 32,036 rows (66 book + 1,044 chapter intros + 30,926 verse notes, 99.4% KJV coverage); scrambled-page handling with KJV-validated splits/rehomes; 293-line skip log
  (no CrossWire module, CCEL has only Song of Songs, HelloAO strips
  Greek/Hebrew and mislabels verses, IA copies are raw OCR).
- scripture.db untouched: 124,369 rows, read-only throughout.

- V2 ENDPOINTS COMPLETE (api/study.py + 6 endpoints, openapi.json regen
  to 22 paths, still 3.1.0). 94/94 pytest pass (68 existing + 26 new in
  tests/test_study.py). study.db opened read-only (PHOS_STUDY_DB_PATH
  override); scripture.db untouched.
  - GET /v1/study?ref= : bundle of passage + TSK cross-refs per verse
    (capped 25/verse, total reported) + commentary excerpts (600-char,
    truncated flag + full_length) + per-source rights.
  - GET /v1/commentary?ref=&source= : full-text entries whose range covers
    the ref; verse queries match whole-chapter comments (verse 0).
    Barnes is NT-only in this transcription (no barnes_nt rows for OT).
  - GET /v1/cross-refs?ref= : standalone TSK lookup, canonical order.
  - GET /v1/devotional?date=&source= : morning + evening, anchor_refs
    resolved to verse text (Daily Light anchors are semicolon-separated
    ref lists, each part resolved). Feb 29 entry served only on real
    Feb 29; non-leap dates after Feb 28 shift by one.
  - GET /v1/prayer?office=&edition= : BCP 1662/1928 office as ordered
    liturgy blocks (API edition 1662/1928 maps to DB bcp1662/bcp1928).
  - GET /v1/memory-pack?topic= : numbered pack, up to 10 verses.
  - Data surprises handled: commentaries.book_order is 1-based while
    crossrefs.book_order and the M1 verses table are 0-based (bridged in
    the API, documented in README); JFB range display fixed for
    same-chapter ranges ("Genesis 1:1-2").
- 2026-09-20: exposed source=gill via /v1/commentary (added to COMMENTARY_SOURCES in api/study.py; app.py validates against the same tuple). Data path verified: John 3:16 returns 1 Gill row.

- LEXICON INGEST (2026-09-20): CC BY 4.0 approved by user; two sources
  ingested to staging, DATA ONLY (not merged into study.db).
  - BDB Hebrew (OpenScriptures HebrewLexicon, commit 21c9add 2019-09-02):
    scripts/ingest_bdb.py → data/staging/bdb_staging.db, 8,674/8,674 rows
    (H1-H8674), 12/12 seeded checks PASS, integrity ok.
  - STEPBible lexicons (commit b99716b0 2026-09-18, sparse checkout of
    Lexicons/): scripts/ingest_stepbible.py →
    data/staging/stepbible_staging.db — TBESH 11,682 (Hebrew, extended
    Strong's), TBESG 11,035 (Greek, Abbott-Smith), TFLSJ 5,709 + extra
    5,325 (Greek, full LSJ); 48/48 seeded checks PASS; 77 TFLSJ-extra name
    rows have blank definitions in the source itself; integrity ok.
  - Attribution text recorded in verification/v2/provenance.md; must be
    added to API docs/code before serving. Merge + /v1/word wiring pending.

## 2026-09-20 — Strong's Repair Complete (Partial)

- Hebrew: 8,248/8,674 (95.1%) PASSES target
- Greek: 5,012/5,624 (89.1%) FAILS target of 5,343 (short by 331)
- All 6 seeded checks pass (G1, G3056, G5624, H1, H430, H8674)
- Zero out-of-range, no duplicates, integrity_check=ok
- H430 manually recovered from OCR artifact 'r430i'
- Known gaps: G2717, G3203-3302 (101 numbers, publisher omissions)
- Database: data/study.db strongs table replaced; backup at data/study.db.bak-strongs-repair
- Report: verification/v2/strongs-repair-log.md


## 2026-09-20 — Lexicon Merge + /v1/word Complete

- Merged Strong's (13,260), BDB (8,674), STEPBible TBESH/TBESG/TFLSJ/TFLSJx
  (33,751) into data/study.db as new `lexicon_sources` + `lexicon` tables
  (55,685 rows total); existing `strongs` table left untouched.
- Backup before merge: data/study.db.bak-lexicon-merge-20260920 (206MB).
- STEPBible HTML sanitized to plain text at merge (br->newline, tags
  stripped keeping inner text, entities unescaped); staging DBs remain the
  raw archive. 0 rows retain HTML tags; integrity_check=ok.
- Seeded raw-to-merged verification: 38/38 PASS
  (scripts/verify_lexicon_merge.py).
- 1,166 duplicate (source_id, strongs_number) pairs are pre-existing
  STEPBible homograph/proper-name rows, carried over faithfully.
- New endpoints: GET /v1/word?number=G3056&source= (all sources by
  default; number normalized, zero-padded source formats matched) and
  GET /v1/word/sources (rights + attribution per source). Every entry
  carries its source's rights/attribution (CC BY 4.0 requirement).
- Fixed stale test test_commentary_ot_has_no_barnes (Gill now covers OT by
  design; test updated to expect matthew_henry/jfb/gill, still no barnes_nt).
- Full suite: 106 passed. OpenAPI 3.1.0 regenerated: 24 paths
  (was 22), incl. /v1/word and /v1/word/sources.
- Known limits: Strong's Greek 89.1% (STEPBible Greek fills gaps via source
  selection); lemma/transliteration empty on strongs rows; 77 tflsjx rows
  have blank source definitions; G500 row text retains OCR "600." heading
  (number assignment correct).
- Reports: verification/v2/lexicon-merge-report.md. Scripts:
  scripts/merge_lexicons.py, scripts/verify_lexicon_merge.py,
  api/tests/test_word.py.

## 2026-09-20 — v2 translations batch 2: 7 new PD English translations ingested
- Backup: data/scripture.db.bak-translations-batch2-20260920 (35,127,296 bytes).
- Rights gate (each license page read before ingest): YLT/Darby/DRB/BBE/GENEVA/OEB
  cleared via eBible copyright pages + bundled copr.htm (all Public Domain; BBE is
  US-specific per eBible's UCC note). AKJV: eBible does not carry it; sourced from
  BibleCorps/ENG-B-AKJV2018-pd-PSFM (filenames [PD], \id lines "Public Domain on
  November 8, 1999") on Engelbrite's 1999 PD dedication. Documented conflict:
  getBible v2 aggregator metadata labels its akjv distribution "Copyrighted; Free
  non-commercial distribution" - Phos uses the BibleCorps PD edition directly, not
  the getBible distribution; conflict recorded in api/translations.py notes.
- Ingest: scripts/ingest_translations_batch2.py (eBible USFX x6 + AKJV p.sfm).
  Footnotes/section heads dropped, inline markup unwrapped, whitespace normalized.
  0-based book_order; deuterocanon appended 66-72 (Tobit..2 Maccabees).
- Counts: YLT 31102, DARBY 31099, DRB 35811 (73 books), BBE 31102, GENEVA 31090,
  AKJV 31102, OEB 13894 (44 books; OEB OT never finished). 0 dupes. Total: 329,569.
- Seeded raw-to-DB verification (seed 20260920,
  verification/v2/verify_translations_batch2.py): 98/98 PASS, independent
  re-extraction compared exactly. DRB Psalms use Vulgate numbering (documented).
- integrity_check: ok. FTS rebuilt: verses_fts = 329,569 rows.
- API: api/translations.py +7 entries (rights + notes incl. BBE/AKJV/OEB/DRB
  caveats); TranslationInfo.notes added; /v1/translations description updated.
  api/parser.py resolves deuterocanonical refs (Tobit..2 Maccabees + aliases).
- Tests: 115 passed (was 106). New api/tests/test_translations_batch2.py:
  per-translation counts, John 3:16 markers (incl. Geneva original spelling),
  DRB 73 books/orders/Tobit verse, OEB 44-book partial coverage, FTS search on
  GENEVA, /v1/passage Tobit 1:1-3, /v1/books DRB=73.
- OpenAPI 3.1.0 regenerated (api/openapi.json).
- Report: verification/v2/translations-batch2-report.md.
- Known limits: BBE US-only PD statement; AKJV metadata conflict (see above);
  DRB Vulgate Psalm numbering; OEB partial OT; Darby 31099 / Geneva 31090 reflect
  source versification (raw counts match).

## 2026-09-20 — Commentaries + dictionaries batch (v2 expansion)

- Backup: data/study.db.bak-commentaries-dicts-20260920 (231,071,744 bytes).
  study.db now 362,184,704 bytes. integrity_check: ok.
- 9 parallel ingest agents, one per source; each read the exact digital
  edition's license page first (rights gate). Raw sources staged per-source
  under data/raw_v2/<source>/ with PROVENANCE.md (URLs, dates, sha256),
  VERIFY.md (seeded raw-to-staging exact comparisons, seed 20260920), and
  meta.json. Staging DBs at data/staging/{clarke,calvin,keil_delitzsch,
  treasury_of_david}.db and data/staging/dict_{easton,isbe,naves,torrey}.db.
- Merged via scripts/merge_commentaries_dicts.py:
  commentaries +21,436 rows (68,259 total, 8 sources); dictionaries new table
  +18,664 rows (4 sources); `sources` table now 18 records;
  new dictionary_sources table (4 records).
- Counts: clarke 14206 (57/66 books; source ed. lacks Deut, Judges, Psalms,
  Proverbs, Ecclesiastes, Jeremiah, Joel, Malachi, Matthew), calvin 4972
  (48 books; CTS English translations 1843-1855), keil_delitzsch 2108
  (partial: 11 OT books; Genesis 1:1 only, Job 29-42, Psalms vols 2-3,
  Proverbs vol 2, Isaiah 29-66, Jeremiah vol 1 partial, Ezekiel vols 1-2,
  Daniel, Ezra, Nehemiah, Esther), treasury_of_david 150 (Psalms 1-150),
  easton 3961, isbe 9349 (1915 Orr verified), naves 4726, torrey 628.
- SKIPPED barnes_ot: genuine Barnes OT covers only Job, Psalms, Isaiah,
  Daniel; full "66-book Barnes" sets are James Murphy completions; no
  PD-clear transcription found (search trail in
  data/raw_v2/barnes_ot/PROVENANCE.md).
- API: api/study.py COMMENTARY_SOURCES +4, new DICTIONARY_SOURCES,
  lookup_dictionary() (case-insensitive) + get_dictionary_sources();
  api/app.py: GET /v1/dictionary?term=&source= (404/400/401) and
  GET /v1/dictionary/sources; entries carry title/rights/attribution.
  Stale "three commentaries" descriptions updated to eight.
- Tests: 143 passed (was 115). New
  api/tests/test_commentaries_dictionaries.py (28 tests: counts, rights
  registration, canonical book orders, seeded entry checks, 404/400/401
  paths, case-insensitivity). 2 stale test_study.py tests updated.
- OpenAPI 3.1.0 regenerated: 26 paths (was 24).
- Report: verification/v2/commentaries-dictionaries-report.md.
- Known limits: K&D partial coverage; Clarke 57/66 books; K&D has 2 OCR-noise
  rows (KXrjpo<;, </iee)) kept faithful to source; Nave's verse index
  excluded, 2 OCR-mangled topics lost (AENEAS, ENON).

## 2026-09-20 — K&D completion in progress; Barnes OT skip confirmed

- Jeremiah (2026-09-20) directed: "Skip/remove Barnes for now" for the K&D
  completion task.
- Barnes OT (`barnes_ot`) was never ingested into study.db; no deletion
  required. Research trail retained at data/raw_v2/barnes_ot/PROVENANCE.md.
- Barnes NT (`barnes_nt`, genuine) remains in study.db unchanged.
- K&D completion parser (scripts/parse_v2_kd_complete.py) built and tested
  on Pentateuch: 980 rows, 979 net new (Genesis 1:1 duplicate skipped).
  All 50 Genesis, 27 Leviticus chapters; Exodus 39/40 (ch 37 missing);
  Numbers/Deuteronomy have no out-of-range chapters after max-chapter guard.
- OCR provenance caveat: local combined _djvu.txt files carry embedded
  Google digitization notices; commercial clearance not yet established.
  Do not describe as commercially cleared.
  (Resolved same day: rights CLEARED, PD-by-expiry; see the 'K&D rights
  verdict' entry below.)

## 2026-09-20 — K&D completion: 6,593 rows parsed (5,140 net new)

> CORRECTED same day (2026-09-20): the 5,140 / 1,453 / 2,071 figures below
> were wrong. The merge that actually ran produced 4,234 net new rows,
> 2,359 exact-range duplicates skipped, 2,108 old rows preserved unchanged
> (fully reconciled in verification/v2/kd-deterministic-checks.md).
- Parser `scripts/parse_v2_kd_complete.py` handles all 39 OT books.
- Staging DB: `data/staging/kd_complete.db` (6,593 rows).
- Deduplication: 1,453 duplicates skipped (existing 2,071 K&D rows preserved).
- Net new: 5,140 rows.
- All 39 books represented. Psalms 1,342 rows (3 vols); Proverbs 686 (2 vols);
  Job 132 (2 vols); Daniel 278 (from file 06 bound-in).
- Gaps: Isaiah incomplete (missing ch 3, 6, 11-19); 2 Kings 7, 21 missing;
  Joshua 12, 1 Sam 14, 1 Kings 13 in prose only.
  (Corrected gap list: Isaiah ch 3, 6, 11-19, 57, 64.)
- Exact comparisons (seed 20260920): Gen 1:1 PASS, Ex 20:1 PASS, Ps 1:1 PASS,
  Hosea 1:1 PASS; Isaiah 6:1 NOT FOUND, 1 Sam 1:1 NOT FOUND.
- BLOCKER: OCR provenance unresolved (Google digitization notices in local
  files). Do NOT merge to study.db until commercial clearance established.
  (Resolved same day: rights CLEARED, PD-by-expiry; merge ran. See the
  'K&D rights verdict' entry below.)
- Barnes OT: skipped per Jeremiah 2026-09-20. Barnes NT unchanged.

## 2026-09-20 — Keil & Delitzsch: 6,342 rows across 39 represented OT books

> CORRECTED same day (2026-09-20): this entry's "completed" framing is
> retracted. The corpus is 39 OT books REPRESENTED with documented missing
> passages and OCR defects, not a completed commentary.

- Source: six `_djvu.txt` OCR files from IA item
  `BiblicalCommentaryOldTestament.KeilAndDelitzsch.6` (earlier wording in
  this entry cited the wrong IA item and claimed a PD-declared license;
  both retracted - the source item has no license field; clearance basis is
  PD-by-expiry, see the 'K&D rights verdict' entry below). Prompted by
  Jeremiah's sermonindex.net link; the IA item's own OCR made the fallback
  unnecessary (sermonindex not used).
- study.db keil_delitzsch: 2,108 rows / 11 books -> **6,342 rows across
  39 represented OT books** (4,234 net new after exact-range dedup).
  (4,234 net new after exact-range dedup). Backup:
  data/study.db.bak-kd-complete-20260920. integrity_check ok.
- Verification: seeded post-merge spot checks (Gen 1:1, Ex 20:1, Ps 1:1,
  Hos 1:1, Mal 1:1, Ruth 1:1) all found; full API suite 143 passed
  (2 tests updated: expected K&D count 6342; no-HTML allowance 8, all
  verified OCR noise).
- Known gaps documented in PROVENANCE.md: Isaiah ch 3, 6, 11-19, 57, 64
  missing; 1 Sam 1:1-8, 2 Kings 7/21 missing (2 Kings 7's famine narrative
  survives only as prose inside the 2 Kings 6:24 row); 2 Kings 8:1-24
  mis-keyed under chapter 6; 16 inverted ranges; duplicate rows (this entry
  said "~720" - corrected: staging held ~995 extra duplicate rows, deduped
  at merge; shipped rows hold 37 extra in 36 same-range groups, verified by
  direct query 2026-09-20); djvu OCR noise.

## 2026-09-20 — Barnes OT skipped per Jeremiah

- Barnes Old Testament not ingested (genuine set covers only Job, Psalms,
  Isaiah, Daniel; "complete" digital sets mix in Murphy material; no clean
  PD transcription found). Research trail kept at
  data/raw_v2/barnes_ot/PROVENANCE.md. Barnes NT (7,354 rows) unchanged.

## 2026-09-20 — Batch-3 ingestion merged (6 sources, coordinator + 6 workers)

- Backups before each merge: data/scripture.db.bak-batch3-{webster,weymouth,
  lxx2012}-20260920 and data/study.db.bak-batch3-{myutmost,practice,
  imitation}-20260920. integrity_check ok on both DBs after merge.
- Translations merged into scripture.db verses (verse cast to TEXT per
  schema): WEBSTER 31,102 / 66 books; WEYMOUTH 7,957 / 27 NT books
  (book_order 39-65, no OT); LXX2012 28,351 / 54 books (OT 0-38 +
  deuterocanon 66-80; 15 books: Tobit, Judith, Wisdom, Sirach, Baruch,
  1-2 Maccabees, Epistle of Jeremy, Prayer of Azarias, Susanna, Bel and
  the Dragon, 1 Esdras, Prayer of Manasses, 3-4 Maccabees). Staged
  28,352; the single empty-text row (1 Kings 14:1, documented edition gap)
  was dropped at merge.
- Provenance per source in data/raw_v2/{webster,weymouth,lxx2012,my_utmost,
  practice_presence,imitation_christ}/PROVENANCE.md (exact URLs, edition,
  rights quotes, SHA-256).
- Deterministic verification (seed 20260920), char-for-character raw ->
  parser -> DB: Webster 55/55, Weymouth 50/50 + 3 anchors, LXX2012 full
  28,352-row re-parse 0 mismatches + 50/50 samples, my_utmost 30/30 +
  30/30, practice_presence 16/16 + 20/20, imitation 20/20.
- API changes: api/translations.py gained WEBSTER/WEYMOUTH/LXX2012
  metadata (partial/versification notes); api/study.py DEVOTIONAL_SOURCES
  extended; /v1/devotional description updated (single-reading sources
  serve morning with evening null); api/openapi.json regenerated (3.1.0).
- Tests: api/tests/test_batch3.py assembled from the 6 worker fragments
  (29 tests; fragment names prefixed MU_/PP_/IC_ to avoid collisions;
  LXX2012 gap assertion for 1 Kings 14:1). Full suite: 172 passed
  (test_api.py health + translations metadata updated for the new codes).
- Raw downloads, staging DBs, VERIFY logs, and per-source reports under
  data/raw_v2/, data/staging/, verification/v2/*-batch3-report.md.

## 2026-09-20 - Public-readiness docs batch (docs/public/)

Six documents written to docs/public/ by one subagent each, cross-checked
by the coordinator:
- api-reference.md: all 26 OpenAPI 3.1.0 paths, auth (single X-API-Key,
  401 without), schemas, error codes, /health (no auth), rate-limit honesty
  (none in code), progress.db checkmarks note. Documented per code, not spec.
- examples.md: five core flows (passage, search, cross-refs, Strong's word
  lookup, devotional) in curl/Python/JS; every pasted response captured from
  a live local run of api/app.py on 2026-09-20. A leftover local test key in
  the snippets was replaced with a your-api-key placeholder.
- privacy-policy.md: template, [LEGAL REVIEW]/[JEREMIAH] markers; verified in
  app.py that there are no accounts, no cookies, no logging middleware.
- terms-of-service.md: template, [LEGAL REVIEW] markers; free commercial-use
  grant, CC BY 4.0 attribution requirement, BSB/WEB name-use notes,
  jurisdiction caveat (KJV UK Crown copyright, Weymouth PD-USA).
- sources-and-attribution.md: all 14 translations (counts from live DB) plus
  all study sources; five CC BY 4.0 lexicon rows with verbatim attribution
  text from lexicon_sources (TFLSJ-extra/step_tflsjx listed separately);
  caveats for KJV, BBE, Weymouth, My Utmost, TSK, Daily Light, Strong's.
- coverage-and-availability.md: all counts re-verified against live DBs
  (scripture.db 396,979 verses / 14 translations; study.db breakdowns with
  per-source rows); honest coverage notes (Weymouth NT-only, OEB 44 books
  partial, LXX2012 54 books + 1 Kings 14:1 absent, DRB 73 books Vulgate Psalm
  numbering, KJV 1769 not established) and the US-PD jurisdiction caveat.

Cross-check results: 26/26 spec endpoints in the API docs; no em dashes in
any file; every study.db source, lexicon, dictionary, and liturgy source
appears in the attribution doc; all 14 translation codes present.

Flags for pre-publish fixes (not doc errors):
- Stale translation counts in code/spec text: openapi.json info.description
  and /v1/translations description say 4/11 translations; app.py docstring
  lists 11 codes; api/README.md says 4. The DB and translations.py have 14.
- /v1/commentary source param in openapi.json lists only 3 of the 8 sources
  the code accepts (gill, clarke, calvin, keil_delitzsch, treasury_of_david
  missing from the spec description).
- Privacy/terms are templates: contact info, effective date, HTTPS and log
  retention decisions, progress.db retention policy need Jeremiah/legal.

## 2026-09-20 — K&D rights verdict: CLEARED (PD by expiry) + documentation corrections

- Rights research (settled 2026-09-20, no spending, nothing published):
  the six `_djvu.txt` files come from IA item
  `BiblicalCommentaryOldTestament.KeilAndDelitzsch.6`, NOT
  `BiblicalCommentaryOldTest.lawprophetswritings` as PROVENANCE.md had
  claimed. That item's metadata has NO licenseurl/license/rights field
  (verified against the fetched metadata JSON); the earlier claim of an
  IA-declared PD license for the djvu files is false and was removed.
  Correct basis: the 1864-1892 T. & T. Clark, Edinburgh English translation
  (Clark's Foreign Theological Library); every volume published 1864-1892,
  before 1931, so all US copyrights expired (works published 1930 and
  earlier are US PD as of 2026-01-01). The 1892 Isaiah notice "[This
  Translation is Copyright, by arrangement with the Author.]" could at most
  have secured a US copyright expiring no later than 1948. Authors
  C. F. Keil (d. 1888), F. Delitzsch (d. 1890). Translators: James Martin
  (d. 1877), Francis Bolton, M. G. Easton (d. 1894), Sophia Taylor,
  David Patrick (d. 1914, Jeremiah 1-29; James Kennedy did Jeremiah 30-52
  and Lamentations), Andrew Harper (d. 1936, Chronicles). The OCR is a
  faithful transcription of a PD work and carries no new copyright
  (Feist v. Rural; Bridgeman v. Corel). Source scans are Google library
  scans on IA (cornell/americana) with Google's PD scan notice and
  Cornell's "no known copyright restrictions in the United States" footer.
  Caveat: death dates for Bolton, Kennedy, Taylor could not be located
  (all active 1866-1889; survival past 1955 implausible), so non-US life+70
  status for their volumes rests on that inference.
- Deterministic verification (verification/v2/kd-deterministic-checks.md):
  14/14 seeded checks pass raw -> parser -> staging; counts fully
  reconciled: study.db keil_delitzsch 6,342 rows, staging 6,593 rows,
  4,234 net new, 2,108 old rows preserved, 2,359 exact-range duplicates
  skipped at merge (2,313 with different text at an occupied key; 46
  text-identical to an old row). Every staging row's verse range is
  represented in study.db.
- Parser review found real defects, now documented honestly (Known defects
  in data/staging/KD_COMPLETE_REPORT.md): 16 inverted ranges; 37
  duplicate-range rows in shipped data (staging held ~995 extra duplicate
  rows, deduped at merge - an earlier draft of this entry said "~720 in
  shipped rows," corrected by direct DB query 2026-09-20);
  wrong-chapter filings from partial roman-numeral matches (observed in
  staging; the Genesis 10 example did not survive the merge); prose
  cross-references parsed as Isaiah headers; "CHAP. X. AND Y." headers
  filed under X only; 2 Kings 8:1-24 mis-keyed under chapter 6 (confirmed
  in the shipped 2 Kings 6:24-5:24 inverted row); garbled
  T. & T. Clark / Philip Schaff publisher-ad text embedded in some rows
  (confirmed in the shipped Exodus 11:4 row); em-dash verse ranges silently
  narrowed to single verses. Root causes: no invariant checks (end >=
  start, numeral fully consumed); every failure mode resolves silently
  toward misattribution. The 14/14 pass means the pipeline carries defects
  faithfully rather than introducing them - but they ARE in the shipped
  rows.
- Documentation corrections made this pass (no DB writes, no publishes):
  PLAN.md K&D row rewritten to "39 OT books are represented, with
  documented missing passages and OCR defects"; KD_COMPLETE_REPORT.md
  corrected to 4,234 net new / 2,359 skipped (it wrongly said 5,140 /
  1,453), title de-finalized, Known gaps updated (Isaiah 3, 6, 11-19, 57,
  64; 2 Kings 7's famine narrative survives only as prose inside the
  6:24 row), obsolete "Blockers for merge" replaced with Merge results,
  and a Known defects section added pointing at the deterministic
  evidence; PROVENANCE.md rights section rewritten (correct IA item, no
  license field, PD-by-expiry basis, Bolton/Kennedy/Taylor caveat),
  Jeremiah v1 translator corrected to David Patrick, kd_job_v0/v1/v2.txt
  noted as orphaned unused OCR chunks of undetermined provenance,
  meta.json staleness noted; meta.json translators fixed and staleness
  note added; commentaries-dictionaries-report.md K&D rows corrected to
  the verified wording.
- Open for Jeremiah: the shipped K&D rows carry the documented defects
  above. Options are to re-parse with invariant checks and repair the
  mis-keyed/inverted rows, or to leave as-is with the defects documented.
  His call.

## 2026-09-20 — K&D cleanup: independent verification and corrections

The main agent independently re-verified the coordinator's cleanup report
with direct DB queries and found three errors IN THE CLEANUP'S OWN CLAIMS,
all corrected same day:

1. The report claimed "~720 running-head-fragment duplicate rows" were IN
   THE SHIPPED rows. Direct query: staging had ~995 extra rows in 481
   same-range groups (incl. 19 identical Psalm 68:1-35 rows); the merge
   deduped them. Shipped study.db holds 37 extra rows in 36 same-range
   groups. KD_COMPLETE_REPORT.md, PLAN.md, and both BUILD_LOG entries
   corrected.
2. The report's wrong-chapter example ("CHAP. XUII" filed as Genesis 10)
   was staging-only and did NOT survive the merge (dropped as a duplicate
   range key); Genesis 42 has 4 shipped rows. Report corrected to say so.
3. The coordinator's doc worker left the wrong IA item
   (BiblicalCommentaryOldTest.lawprophetswritings) and a wrongly-claimed PD
   license declaration in: PROVENANCE.md header, meta.json fields,
   commentaries-dictionaries-report.md table row, the live study.db
   `sources` rights_basis, merge_commentaries_dicts.py, and the public
   docs/public/sources-and-attribution.md. All corrected to the real item
   (BiblicalCommentaryOldTestament.KeilAndDelitzsch.6, no license field;
   clearance is PD-by-expiry). study.db backed up to
   data/study.db.bak-kd-rightsfix-20260920 before the sources-table edit.

Verified real in the shipped rows by direct query: 16 inverted ranges
(e.g. 2 Kings 6:24-5:24, which also holds the mis-keyed 2 Kings 8 famine
narrative); T. & T. Clark / Philip Schaff publisher-ad text embedded in
the shipped Exodus 11:4 row; real gaps at Isaiah 3, 57, 64, 1 Samuel 1:1-8,
2 Kings 7 and 21 (zero rows). IA metadata for the correct item verified
directly against archive.org (6 _djvu.txt files, no licenseurl field).

Rights verdict stands: CLEARED, PD-by-expiry (1864-1892 T. & T. Clark
translation, all volumes pre-1931; OCR faithful transcription carries no
new copyright). Caveat preserved: translator death dates for Bolton,
Kennedy, Taylor unlocated, so non-US life+70 status for their volumes is
inference, not fact.

Open question left for Jeremiah: shipped rows carry the documented
defects; options are a re-parse with invariant checks (parser rework) or
leaving as documented. Full API suite still 172 passed after all edits.

## 2026-09-20 - K&D targeted defect fix: 6,342 -> 6,325 rows

Jeremiah chose the targeted-fix option for the shipped K&D defects.
Backup `data/study.db.bak-kd-defectfix-20260920` taken before any write.
Script `scripts/kd_defect_fix.py` asserts every target row (id, range, text
length, text markers) before applying, dry-ran on a full copy first, then
applied to live in one transaction.

- 16 inverted ranges corrected to text-supported ranges (e.g. 2 Kings
  6:24-5:24 -> 6:24-7:20; Isaiah 56:9-50:9 -> 56:9-57:21; Proverbs
  10:5-1:5 -> 31:1-31:5). 1 Kings 16:29 cross-book epoch filed at its
  anchor verse (schema cannot represent cross-book ranges; documented).
- 36 duplicate-range groups (37 extra rows): 7 clear misfiles reassigned
  (five Daniel 3 rows -> Daniel 4; two Psalms 75 rows -> Psalms 76:1 and
  77:2-4), 30 true-duplicate/inferior/stub rows deleted, 1 redundant
  Daniel 9:24-27 scan deleted (75% redundant with longer row 68037).
- Exodus 11:4-8 row (68552): publisher advertisement truncated
  (38,161 -> 4,462 chars); all ad markers verified absent.
- 2 Kings 6:24-7:20 famine row (69949): text truncated where the ch.8
  section header began (13,992 -> 13,764 chars).
- 15 parser-missed sections recovered from raw OCR (nothing invented):
  1 Samuel 1:1-8; 2 Kings 8:1-15, 8:16-24, 21:1-18, 21:19-26;
  Isaiah 3 (5 sections); Isaiah 64 (5 sections).
- Gap recheck against raw: Isaiah 3, 57, 64 / 1 Sam 1:1-8 / 2 Ki 7, 8, 21
  were parser misses or misfiles, not edition gaps; still genuinely absent:
  Isaiah 6, Isaiah 11-19.
- Post-fix: integrity ok, 39 books, 0 inverted, 0 dup extras.
- Report: verification/v2/kd-defectfix-report.md; manifest:
  verification/v2/kd-defectfix-manifest.md (70 entries).
- API suite: 172 passed, 3 warnings (K&D count assertion 6342 -> 6325).
- Public docs updated: sources-and-attribution.md and
  coverage-and-availability.md counts 6,342 -> 6,325; gap list revised.

## 2026-09-20 - K&D publisher-advertisement cleanup, second pass (26 rows)

First pass had cleaned only the Exodus 11:4 ad; verification found 24
further volume-end K&D rows still containing T. & T. Clark catalogs,
printer colophons, library stamps, and Google scan boilerplate. Backup
`data/study.db.bak-kd-adcleanup-20260920` taken before any write. Script
`scripts/kd_ad_cleanup.py` uses per-row manually verified truncation
boundaries (commentary-to-trailing-matter transitions inspected directly),
dry-ran on a full copy, then applied live.

- 26 rows truncated at verified boundaries (e.g. Ruth 4:18-20 19010->3642;
  Ezekiel 48:30-35 119314->89584; Psalms 83:18 62761->21472). Four more
  found only by the post-apply sweep (Deut 34:9-12, 2 Kgs 25:22-26,
  Micah 7:20, Mal 4:4-6).
- One boundary corrected mid-pass: Leviticus 27:30-33 first cut at 13,579
  left catalog in kept text; corrected to 2,645 and re-verified.
- id=71579 (Ecclesiastes 1:1-17, 12,195 chars) is 100% publisher catalog
  with zero commentary; NOT deleted (parent approval required; count stays
  6,325). Genuine citations preserved untouched: 71524 (Eccl 8:14), 70427
  (Job 2:4), 70440 (Job 5:12).
- Post-cleanup: integrity ok, 6,325 rows, 39 books; final catalog-marker
  sweep over all K&D rows: zero unexpected hits.
- Verse-0 range rows: 151 (chapter introductions); counted only, unmodified.
- Report addendum: verification/v2/kd-defectfix-report.md; manifest:
  verification/v2/kd-defectfix-manifest.md (now 101 entries).
- API suite: 172 passed, 3 warnings.

## 2026-09-20 - K&D ad-row deletion + scan-stamp strips: 6,325 -> 6,324 rows

Parent approved both pending items from the ad-cleanup pass. Backup
`data/study.db.bak-kd-delete71579-20260920` taken before any write.

- DELETED id=71579 (Ecclesiastes 1:1-17, 12,195 chars): verified 100%
  publisher catalog, zero Ecclesiastes commentary (no Koheleth,
  Ecclesiastes, verse, or Ver. markers). A proper Ecclesiastes 1:1 row
  (id=71460, 1,172 chars) already exists; no coverage lost.
- STRIPPED 4 inline "Digitized by Google" scan stamps mid-sentence
  (ids 68682, 69567, 70595, 71616), including attached page-header
  fragments on 70595 and 71616. Text-only changes, ranges untouched.
- Post-change: integrity ok, 6,324 rows, 39 books; zero "Digitized by
  Google" occurrences remain in K&D; catalog-marker sweep still clean.
- Counts updated: api/tests/test_commentaries_dictionaries.py 6325 ->
  6324; docs/public/sources-and-attribution.md and
  coverage-and-availability.md 6,325 -> 6,324; PLAN.md K&D row;
  verification/v2/kd-defectfix-report.md addendum + manifest entries.
- API suite: 172 passed, 3 warnings.

## 2026-09-20 - v3: LSG1910 (Louis Segond 1910, French) ingested: 15 translations, 428,149 verses

First non-English translation in Phos.

- **Rights (gate passed):** digital edition is eBible.org "Louis Segond
  1910" (`fraLSG`), eBible.org certified. The edition's rights page
  (https://ebible.org/fraLSG/copyright.htm, retrieved 2026-09-20) lists
  the licensing field as Public Domain: "Cette Bible est dans le domaine
  public. Il n'est pas protégé par copyright." / "This Bible is in the
  Public Domain. It is not copyrighted." Underlying work: first edition
  published 1910 (pre-1931, US PD by expiry); translator Louis Segond
  died 1909 (life-plus-70 expired end of 1979). No CC license, no holder,
  no extra terms. Jurisdiction caveat kept in docs (US expiry does not
  by itself establish non-US status).
- **Source:** https://ebible.org/Scriptures/fraLSG_usfm.zip (3,467,489
  bytes; SHA-256 3a0615e992ffd412b1afcaed50d146bba5ec8ae2378f04ca71459a4cd2d7cc33),
  66 USFM files, source files dated 2026-08-08. Raw kept in
  data/raw_v2/lsg1910/ with PROVENANCE.md and sha256sums.txt (67 lines).
- **Ingest:** scripts/ingest_lsg1910_v3.py (mirrors the Webster batch-3
  pattern) stages to data/staging/lsg1910.db, then merged into
  data/scripture.db as translation 'LSG1910'. Backup
  data/scripture.db.bak-lsg1910-20260920 taken before the merge.
- **USFM specifics:** Strong's-tagged words `\w word|strong="H7225"\w*`
  (tag dropped, word kept), `\+w`/`\wj` words-of-Christ markers kept as
  plain words, `\f`/`\x` spans dropped, verse text accumulated across
  `\q` continuation lines. Two defects caught by verification before
  merge: unhandled `\+w` markers (fixed in parser) and the verifier not
  accumulating multi-line verses (fixed in verifier).
- **Verification:** data/staging/lsg1910-VERIFY.md, deterministic
  three-way check (seed 20260920), 5 anchors + 50 samples: 55/55 pass.
  31,170 rows, 66 books, 0 duplicate keys, 0 empty texts, 0 rows with
  stray markup; integrity ok. 10 well-known verses spot-checked in
  French (Gen 1:1, Jn 3:16, Ps 23:1, Rm 8:28, Mt 6:33, Ph 4:13, Pr 3:5,
  Es 40:31, Jr 29:11, Rm 10:9).
- **Versification:** traditional French numbering kept exactly as in the
  source (translation-scoped), documented in PROVENANCE.md and the
  public coverage notes (e.g. psalm titles as verse 1, Ex 7:26-29 =
  KJV 8:1-4, Ap 12:18 = KJV 13:1, Mc 9:51 = KJV 9:50b).
- **API/docs updates:** api/translations.py LSG1910 entry (rights +
  notes), api/openapi.json regenerated (3.1.0, 15 codes), api/app.py
  "fourteen" -> "fifteen", docs/public/sources-and-attribution.md and
  coverage-and-availability.md (15 translations, 428,149 verses),
  api/tests/test_api.py health assertion (translations list + 428149),
  PLAN.md v3 row.
- API suite: 172 passed, 3 warnings.
- Report: verification/v2/lsg1910-ingest-report.md.

## 2026-09-20 - Phos v3: German LUTHER1912 ingested (second multilingual translation)

- Rights gate passed: eBible.org "Lutherbibel 1912" (deu1912). The
  edition's copyright file (copr.htm, bundled in the source zip) lists
  the licensing field as Public Domain ("The Holy Bible in German,
  Luther 1912", translation by Martin Luther). Underlying work: 1912
  revision of Luther's Bible, first published 1912 (pre-1931, US PD by
  expiry); Martin Luther died 1546. Territorial caveat kept in docs.
- Ingested 31,102 rows, 66 books, 0 dup keys, 0 empties, 0 markup
  leaks, integrity ok. Versification matches KJV exactly (31,102 keys,
  no deltas; psalm titles joined to verse 1 in the edition text).
  Total verses 428,149 -> 459,251. 16 translations.
- Verified by me directly: LUTHER1912 count 31,102, 66 books, 10
  well-known verses spot-checked in German (all correct classic Luther
  1912), deterministic three-way check 55/55 pass (seed 20260920),
  backup exists (117,760,000 bytes), openapi.json carries LUTHER1912.
  API suite run myself: 172 passed, 3 warnings.
- Updated: api/translations.py, api/openapi.json, api/app.py (15 -> 16),
  api/tests/test_api.py (16-code sets, 459251 health count, LUTHER1912
  31102 assertion), public docs, PLAN.md v3 row, verification/v2/
  luther1912-ingest-report.md. Raw source + PROVENANCE.md +
  sha256sums.txt in data/raw_v2/luther1912/.
- Scripts: scripts/ingest_luther1912_v3.py, scripts/verify_luther1912_v3.py
  (mirrored from the LSG1910 pair; deu1912 USFM is structurally identical).

## 2026-09-20 - Phos v3: Almeida Recebida (Portuguese) ingested: 16 -> 17 translations

Third non-English translation. Rights gate passed with a documented
ambiguity: the publisher's download page (almeidarecebida.org, live,
fetched 2026-09-20) states "This Bible (PorAR) is in the Public Domain";
the same page carries a generic BY-NC-SA site notice that reads as the
WordPress CC-plugin footer, not a statement about the Bible text. A third
party (bible-discovery.com) independently lists Distribution license:
Public Domain. Biblia Almeida Recebida v1.7 (Textus Receptus-based
revision of Almeida, updated Portuguese, dump dated 2017-03-17).

eBible.org hosts no Almeida edition (Scriptures index checked; Portuguese
editions are porblt, porbr2018, porbrbsl, poronbv, portft). The 1848/1850
PDFs are PD by age but only OCR'd scans (no clean digital edition);
Wikisource 1819 transcription is incomplete (86 pages). Almeida Recebida
is the clean digital edition with a publisher PD declaration.

- Backup: data/scripture.db.bak-almeida-20260920 (124,993,536 bytes).
- Source: Almeida-Recebida-(version-1.7).mysql.zip (1,478,663 bytes,
  SHA-256 e6c2b73a9b692e72a179df6b70735f2a7c9c60792e7fe6ad29be2664deaf615c);
  pt_nar.sql 4,643,189 bytes. book_id 1-66 = Genesis-Revelation.
- Parser quirk fixed pre-staging: 19 rows use doubled-quote escapes
  (d''agua); first regex missed them.
- Ingested 31,102 rows, 66 books, 0 dup keys, 0 empties, 0 markup;
  verse stored as TEXT per live schema. Total verses 459,251 -> 490,353.
- Verification: 55/55 three-way check (seed 20260920); 10 well-known
  verses spot-checked in Portuguese, all correct.
- Updated: api/translations.py, api/openapi.json (17 codes), api/app.py,
  api/tests/test_api.py, public docs, PLAN.md, verification/v2/
  almeida-ingest-report.md, data/raw_v2/almeida/PROVENANCE.md.
- API suite: 172 passed, 3 warnings.

## 2026-09-20 — RVA1909 (Spanish Reina-Valera 1909) ingested; v3 multilingual set complete
- Rights: eBible.org "Santa Biblia — Reina Valera 1909" (spaRV1909), eBible.org
  certified. The edition's copyright page (copr.htm, fetched 2026-09-20 and
  bundled in the source zip) lists the licensing field as Public Domain
  ("The Holy Bible in Spanish, Reina Valera translation of 1909", translation
  by Reina y Valera; "Dominio Publico"). First published 1909 (pre-1931, US
  PD by expiry); Casiodoro de Reina d. 1594, Cipriano de Valera d. 1602.
  No CC license, no holder, no extra terms. Territorial caveat kept in docs.
- Backup: data/scripture.db.bak-rva1909-20260920 (131,702,784 bytes), taken
  before any write.
- Source: https://ebible.org/Scriptures/spaRV1909_usfm.zip (2,380,143 bytes,
  SHA-256 b5bfac87199a561fcbacb5e32be5d8d280934b1c6830088d9eb8c68ffbfbe711);
  66 USFM files, source files dated 2015-08-10 (HTML generated 2026-08-08).
- Pre-scan: 31,102 \v lines, all numeric ids, no ranges.
- Spanish versification kept as in the source (translation-scoped): 18 empty
  \v placeholder markers dropped, each confirmed by text evidence.
  Chapter offsets (empty end-of-chapter marker; text printed at next
  chapter's v1): Numbers 12:16 at 13:1, Numbers 29:40 at 30:1,
  1 Samuel 23:29 at 24:1, Hosea 11:12 at 12:1, Jonah 1:17 at 2:1.
  Merges: 2 Samuel 20:26 into 20:25, 2 Chronicles 33:25 into 33:24,
  Job 35:16 into 35:15, Job 38:39-41 printed as 39:1-3,
  Job 40:20-24 printed as 40:14-19, Acts 19:41 into 19:40,
  2 Corinthians 13:14 printed as 13:13.
- Ingested 31,084 rows as RVA1909, 66 books, 0 dup keys, 0 empty texts,
  0 markup leaks, verse stored as TEXT per live schema, integrity ok.
  Total verses 490,353 -> 521,437. 18 translations. Psalm titles are joined
  to verse 1 in the edition text (same convention as Luther1912).
- Verification: deterministic three-way check (seed 20260920), script
  scripts/verify_rva1909_v3.py, report data/staging/rva1909-VERIFY.md:
  5 anchors + 50 seeded samples, 55/55 pass. 10 well-known verses
  spot-checked in the live DB in Spanish, all correct classic RV1909.
- Updated: api/translations.py (RVA1909 rights entry), api/openapi.json
  (regenerated 3.1.0, 18 codes), api/app.py (seventeen -> eighteen),
  api/tests/test_api.py (18-code sets, 521437 health count, RVA1909 31084
  assertion), docs/public/sources-and-attribution.md and
  coverage-and-availability.md, PLAN.md (multilingual set 4/4 complete),
  verification/v2/rva1909-ingest-report.md,
  data/raw_v2/rva1909/PROVENANCE.md + sha256sums.txt.
- API suite: 172 passed, 3 warnings (run via api/.venv python).

## 2026-09-20 - Lexicon merge verified and completed (BDB + STEPBible)

- Finding: the BDB and STEPBible lexicon ROWS were already merged into
  data/study.db lexicon (55,685 rows total: strongs 13,260 / 5,012 greek +
  8,248 hebrew; bdb 8,674 hebrew; step_tbesh 11,682 hebrew; step_tbesg
  11,035 greek; step_tflsj 5,709 greek; step_tflsjx 5,325 greek), and
  `lexicon_sources` already held all 6 rights/attribution rows. Verified
  byte-level against staging: bdb H1 identical; step rows have <br> tags
  converted to newlines and <i> tags stripped (matches the
  test_word_no_html_in_stepbible_definitions assertion).
- Gap found and closed: the 5 CC BY 4.0 source rows (bdb, step_tbesh,
  step_tbesg, step_tflsj, step_tflsjx) were missing from the general
  `sources` table (strongs was there as kind='lexicon'). Inserted them as
  kind='lexicon' with rights='CC BY 4.0', full rights_basis text plus the
  attribution string appended, version = upstream commit hash, sha256 from
  staging. Backup before write:
  data/study.db.bak-lexicon-merge-20260920 (383,852,544 bytes).
- extra-column decision (pre-existing merge): STEPBible dstrong/ustrong
  extended-Strong's variant codes were dropped at merge; only the morph
  code was kept in lexicon.extra. Known limitation, documented in
  verification/v2/lexicon-merge-report.md. Duplicate (source_id,
  strongs_number) groups: 1,166, all in the STEPBible extended lexicons
  (base number shared across G/H/I/N variants by design); not a defect.
- Verification: PRAGMA integrity_check ok; 55,685 lexicon rows;
  /v1/word/sources lists all 6 sources with correct counts and rights;
  /v1/word default (no source param) returns entries from every lexicon
  holding the number (G3056: step_tbesg, step_tflsj, strongs; H430: bdb,
  3x step_tbesh, strongs); source filters ?source=bdb/step_tbesh/
  step_tbesg/step_tflsj/step_tflsjx verified; G3056 source=bdb 404s
  correctly (bdb is Hebrew-only).
- Attribution: docs/public/sources-and-attribution.md already carries the
  BDB and STEPBible rows with counts, rights, and the exact CC BY 4.0
  attribution strings with license links; api/openapi.json /v1/word/sources
  description already states the CC BY 4.0 attribution requirement.
- Report: verification/v2/lexicon-merge-report.md.
- API suite: 172 passed, 3 warnings (run via api/.venv python). No test
  changes needed (api/tests/test_word.py already asserts the merged state).

## 2026-09-20 - v3 scope: server-side TTS dropped (user decision)
- Removed on-demand TTS audio from the v3 additions list in PLAN.md.
- Rationale: as a Muse connector, speech is the client's job; Muse reads
  verse text aloud natively. Server synthesis added per-language engine,
  compute, and cache costs against the free-infrastructure constraint with
  no benefit to the connector use case. Revisit only if a non-Muse public
  consumer needs audio from the endpoint.

## 2026-09-20 - v3 scope: verse-card endpoint dropped (user decision)
- Removed the verse-card image endpoint from the v3 additions list.
- Rationale: rendering is the client's job; Muse builds verse cards on
  demand in chat from API verse text. Avoids a server-side renderer,
  image cache, and style API with no benefit to the connector use case.

## 2026-09-20 - v3: interlinear built and shipped
- Source: STEPBible TAGNT (Greek NT) + TAHOT (Hebrew OT), Tyndale House
  Cambridge, CC BY 4.0. Files in data/staging/interlinear/ (6 files).
- Parse (scripts/parse_interlinear_v3.py): full TAGNT/TAHOT type alphabet
  accepted (incl. N(k)O, L(b+p)); source totals matched exactly (142,096 +
  305,652 = 447,748 word rows, 0 skipped, 0 duplicates).
- Reading rule: Greek = every word attested in NA/SBL (type contains N/n);
  Hebrew = Leningrad main text + translators' Qere (L/Q types). Other
  readings kept as flagged variants. Corrected mid-build from a narrow
  NKO-only rule that dropped 4,051 NA-attested Greek words (verified
  against NA28, e.g. Mat 1:18#06, 1Co 3:5#01/#05/#07).
- Merge (scripts/merge_interlinear_v3.py): interlinear_words table in
  study.db; 443,119 selected-reading rows + 4,629 variant rows; positions
  renumbered 1..N per KJV verse (166 split verses concatenated in source
  order; Psalm titles ordered first); Strong's normalized to base form for
  /v1/word cross-reference. Backup data/study.db.bak-interlinear-20260920
  taken before merge. sources table: step_tagnt, step_tahot (CC BY 4.0,
  full rights basis + attribution).
- Coverage: all 31,102 KJV verses (31,060 selected reading; 42
  variant-only = the textually disputed verses: Mark 16:9-20, John
  7:53-8:11, and the 18 single disputed verses).
- API: GET /v1/interlinear/{book}/{chapter}/{verse} (auth required),
  models + endpoint in api/app.py, accessor in api/study.py,
  13 tests in api/tests/test_interlinear.py. openapi.json regenerated.
- Docs: docs/public/sources-and-attribution.md (new Interlinear section +
  attribution text), docs/public/coverage-and-availability.md (new
  Interlinear row). PLAN.md decisions log updated.
- API suite: 185 passed, 3 warnings (run via api/.venv/bin/python).
- Report: verification/v2/interlinear-build-report.md.

## 2026-09-20 - v3: Phos Intensive Verse Study endpoint built and shipped
- Locked name/product: "Phos Intensive Verse Study" (user, 2026-09-20;
  clarity over poetry). Endpoint: GET /v1/verse-study/{book}/{chapter}/{verse}
  (auth required). GET /v1/interlinear untouched. Spec:
  docs/design/verse-study-spec.md (renamed from phos-interlinear-spec.md).
- One-call composite for a single verse: verse in up to 4 translations
  (default BSB,KJV,WEB; ?translations= validated, max 4; per-translation
  present flags; 404 only when absent everywhere); key original-language
  words (nouns/verbs/adjectives via the morphology rule in spec 5.1, cap
  12, position order) each with transliteration, base-form Strong's,
  morphology, lemma, and one lexicon definition (first non-empty gloss
  from bdb/step_tbesh/step_tbesg/step_tflsj/step_tflsjx, fallback to
  Strong's PD definition truncated at 250 chars); top 8 TSK cross-refs in
  canonical order + total, texts in the first requested translation;
  commentary excerpts from all eight sources (user decision 2026-09-20:
  excerpts from all eight like /v1/study, not one curated source; the
  ?commentary= override from the spec draft was dropped); up to 3
  devotionals by verse anchor with the nearby fallback (same chapter,
  within 3 verses, labeled "nearby") and the John/1 John disambiguation
  regression test; prayer from the BCP morning/evening office by keyword
  substring matching (1662 first, then 1928; office-opening fallback;
  matched_keywords returned for audit).
- Attribution: sources array on every response + rights_note with CC BY
  4.0 credit text, STEPBible and deed links, and the Phos modification
  record; CC BY 4.0 note in the OpenAPI description; new "Phos Intensive
  Verse Study" section in docs/public/sources-and-attribution.md.
- 42 variant-only verses (e.g. Mark 16:9) return 200 with key_words: []
  and key_words_note pointing to /v1/interlinear.
- Implementation: models + helpers + endpoint in api/app.py; study.py
  gains study.all_devotionals(); no DB writes (reads only). Backup
  data/study.db.bak-verse-study-20260920 (462MB) taken first.
- Tests: 32 new in api/tests/test_verse_study.py (morphology rule unit
  tests, 1 John disambiguation, variant-only, nearby fallback, full error
  table, attribution traceability, auth). API suite: 217 passed
  (185 + 32), 3 warnings.
- Live smoke on temp uvicorn: John 3:16 (12 key words, 19 xrefs, 8 shown,
  6 commentary sources, 3 exact devotionals, bcp1662 keyword prayer) and
  Genesis 1:1 (5 Hebrew key words, BDB definitions, keil_delitzsch among
  6 commentary sources, 3 nearby devotionals). Server terminated after.
- Docs: docs/public/api-reference.md (new section), examples.md (new
  worked example), sources-and-attribution.md, coverage-and-availability.md.
  openapi.json regenerated (path + CC BY note verified in description).
- Report: verification/v2/verse-study-build-report.md.
- Deviation from spec draft: commentary returns excerpts from all eight
  sources (per user lock 2026-09-20), not one curated excerpt; no
  ?commentary= parameter.
