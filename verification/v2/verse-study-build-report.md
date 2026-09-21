# Phos Intensive Verse Study: build report

Date: 2026-09-20. Endpoint: `GET /v1/verse-study/{book}/{chapter}/{verse}`.
Spec: docs/design/verse-study-spec.md. Status: built, tested, smoke-verified.
Local only; no public deployment.

## What was built

One-call composite for a single verse (auth required, API key):

- **Translations:** up to 4, default `BSB,KJV,WEB`; `?translations=` validated
  against the registry, max 4 (400 beyond). Per-translation `present` flags;
  404 only when the verse is absent from every requested translation.
- **Key words:** nouns/verbs/adjectives via the spec 5.1 morphology rule
  (Greek POS tag before the first `-`, `+`-compounds split first; Hebrew
  `/`-segments with one leading `H` stripped), cap 12, verse position order.
  Each carries word, transliteration, base-form Strong's (e.g. `G0025` ->
  `G25`), gloss, morphology, lemma, one lexicon definition, and
  `definition_source`. Definition priority: first non-empty gloss from
  `bdb`, `step_tbesh`, `step_tbesg`, `step_tflsj`, `step_tflsjx`; fallback
  is the public-domain Strong's definition truncated to 250 chars at a word
  boundary. The Strong's OCR cleanup (11,568 of 13,260 entries repaired,
  report verification/v2/strongs-ocr-cleanup-report.md) ran before this
  build per the user's order.
- **Cross-references:** top 8 in canonical order plus total; texts in the
  first requested translation.
- **Commentaries:** excerpts from all eight sources (per the user's locked
  decision, not one curated excerpt; the spec draft's `?commentary=`
  parameter was dropped). Reuses the existing 600-char excerpt convention.
- **Devotionals:** matched by verse anchor with the real reference parser
  (book-exact; substring matching forbidden), ordered by anchor count then
  source priority, cap 3; nearby fallback (same chapter, within 3 verses,
  labeled `nearby`) when nothing is anchored exactly.
- **Prayer:** `?office=morning|evening` (default morning); keyword substring
  scoring against `kind='text'` liturgy blocks, 1662 BCP searched before
  1928, ties by lowest `seq`; office-opening fallback with
  `match_kind: "office_opening"`. `matched_keywords` returned for audit.
  Matching is keyword relevance, not semantic understanding (spec is
  explicit about this).
- **Attribution:** per-response `sources` array (every contributing source
  with rights status) plus `rights_note` carrying the CC BY 4.0 credit
  text, STEPBible and deed links, and the Phos modification record. The
  CC BY 4.0 note is also in the endpoint's OpenAPI description.
- **Variant-only verses:** the 42 textually disputed verses (e.g. Mark 16:9)
  return 200 with `key_words: []` and `key_words_note` pointing to
  `GET /v1/interlinear/{book}/{chapter}/{verse}`; all other sections behave
  normally (prayer falls back to the office opening when there are no
  key-word keywords).

No database writes: the endpoint reads `scripture.db` and `study.db` only.
Backup `data/study.db.bak-verse-study-20260920` (462,688,256 bytes) taken
before the build. `GET /v1/interlinear` untouched.

## Verification evidence

Full API suite: **217 passed** (185 existing + 32 new), 3 warnings, via
`cd api && .venv/bin/python -m pytest tests/ -q`. New tests in
api/tests/test_verse_study.py cover: the morphology rule as unit tests
(Greek `ADV` excluded, `A-ASM` kept; Hebrew `HTd/Ncmpa` kept, `HC/To`
excluded), the John/1 John devotional disambiguation (the 1 John 3:16
devotional "Hereby perceive we the love of God ..." does not appear in the
John 3:16 response), Mark 16:9 variant-only behavior, the nearby fallback
(John 1:2), the full error table (unknown book 400, out-of-range 400,
unknown translation 400, 5 translations 400, unknown office 400, missing
everywhere 404, missing key 401), partial translation presence
(Acts 15:34: KJV present, BSB/WEB absent), attribution traceability (every
`definition_source` appears in `sources`; `rights_note` names STEPBible and
links the CC BY 4.0 deed), and OpenAPI regeneration (path present, CC BY
note in the description, verified programmatically).

Live smoke on a temporary local uvicorn server (terminated after):

- **John 3:16:** 200. 3 translations, all present. 12 key words in position
  order, first `ἠγάπησεν` G25 ("to love", step_tbesg). Cross-refs total 19,
  8 shown. Commentary sources: barnes_nt, calvin, clarke, gill, jfb,
  matthew_henry. 3 devotionals, all `exact` (my_utmost, daily_light x2).
  Prayer: bcp1662 keyword match, "The second Collect for Peace", matched
  keywords love/god/all/trust/life/eternal. `sources` includes `step_tagnt`
  with rights CC BY 4.0.
- **Genesis 1:1:** 200. Testament OT. 3 translations present. 5 Hebrew key
  words with BDB definitions (CC BY 4.0). Commentary sources: calvin,
  clarke, gill, jfb, keil_delitzsch, matthew_henry. 3 devotionals, all
  `nearby` (none anchored exactly). Prayer: bcp1662 keyword match.
  `sources` includes `step_tahot` and `bdb`, both CC BY 4.0.

## Deviations from the spec draft

One, per the user's locked decision (2026-09-20): commentary returns
excerpts from all eight sources like `/v1/study` does, not one curated
excerpt; the `?commentary=` override parameter was dropped. Everything
else follows the spec exactly.

## Notes

- The 1,692 Strong's entries left untouched by the OCR cleanup (ambiguous,
  not clearly mechanical) and the still-damaged transliterations are logged
  in data/staging/strongs_ocr_skipped.jsonl for a future pass.
- Pre-existing data quirk (not introduced here): the Genesis 1:1 word 7
  `הָ/אָֽרֶץ\:` carries a literal backslash from the source interlinear
  data; it is served as stored.
- Prayer keyword matching occasionally surfaces weak hits (e.g. "he" is not
  in the spec's stopword list); this is the documented spec tradeoff, and
  `matched_keywords` lets the client audit it.
- Public docs updated: docs/public/api-reference.md (new section),
  docs/public/examples.md (new worked example), docs/public/
  sources-and-attribution.md (new "Phos Intensive Verse Study" section),
  docs/public/coverage-and-availability.md (new composite row).
  api/openapi.json regenerated.

## 2026-09-21 — prayer keyword-matching fix (post-build QA)

Jeremiah asked whether the tool had been tested as a user would use it. Live
smoke testing found a real defect: Psalm 23:1 matched the prayer on the
stopwords "is", "my", "i" and returned a Psalm 51 confession, and rubric
direction blocks (section 'opening_rubric', stored as kind 'text') were
eligible matches.

Fixes in api/app.py:
- Expanded `_VERSE_STUDY_PRAYER_STOPWORDS` from 16 words to a full
  function-word set (articles, prepositions, conjunctions, pronouns,
  auxiliaries, common verbs, adverbs/fillers).
- `_verse_study_prayer` now excludes `opening_rubric` and `title` sections
  from matching candidates; they are directions, not prayers.

Verified live: Psalm 23:1 now matches the Venite ("shew our selves glad in
him with Psalms"); Romans 8:28 and John 3:16 prayers unchanged and apt.
New regression tests in tests/test_verse_study.py. Full suite: 220 passed.
