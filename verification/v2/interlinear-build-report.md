# Interlinear build report (v3) - 2026-09-20

## Source

STEPBible TAGNT (Translators Amalgamated Greek NT) + TAHOT (Translators
Amalgamated Hebrew OT), Tyndale House Cambridge, CC BY 4.0. Six files in
`data/staging/interlinear/`. License header in the files: "Data created by
www.STEPBible.org based on work at Tyndale House Cambridge (CC BY 4.0)".
Spanish and sub-meaning columns excluded (unverified provenance).

## Parse (scripts/parse_interlinear_v3.py)

- TAGNT: 142,096 / 142,096 source word rows recognized (0 skipped).
- TAHOT: 305,652 / 305,652 source word rows recognized (0 skipped).
- Full type alphabet accepted, including `N(k)O`, `L(b+p)`, `L(a+bh)`,
  `L(AH+B)`, `LBH(a+C)` (12 rows with `+` in the type).
- 0 true (src_ref, position) duplicates.
- 166 KJV verses fed by split source verses (e.g. `1Ki.18.33` +
  `1Ki.18.33(18.34)`; NRSV `2:10` + `2:11[2.10]` -> KJV `2:10`).
- Psalm titles (478 verse-0 rows) mapped to verse 1, ordered before
  verse-1 words; `src_verse=0` retained.

## Reading selection (documented edition rule)

- Greek: every word attested in the Nestle-Aland/SBL critical text, i.e.
  word type contains `N` or `n` (NKO, N(k)O, NO, no, n, ...). K-only /
  O-only types are variants (Byzantine/Majority/TR-only readings).
- Hebrew: Leningrad main text (`L...`) including the translators' Qere
  choice (`Q...`). `X`/`R` rows are variants.
- Mid-build correction: the first implementation selected only
  NKO/NK(O)/NK(o), which dropped 4,051 NA-attested Greek words and left
  holes in 2,633 verses. Verified against NA28 (Mat 1:18#06 γένεσις;
  1Co 3:5#01/#05/#07) that `N(k)O` and `no` words belong in the critical
  reading; the rule was widened to N/n-class and the merge re-run.
- Strong's numbers normalized to base form (`H7225G` -> `H7225`) so every
  number works directly in `/v1/word`; comma-separated multiples preserved.

## Merge (scripts/merge_interlinear_v3.py)

- Backup `data/study.db.bak-interlinear-20260920` (383,852,544 bytes) taken
  before any write.
- New table `interlinear_words` in `data/study.db` (+ indexes on
  (book, chapter, verse) and strongs).
- Selected reading: 443,119 rows (137,646 Greek + 305,473 Hebrew);
  positions renumbered 1..N per KJV verse, split verses concatenated in
  source order.
- Variants: 4,629 rows (4,450 Greek + 179 Hebrew), sequenced per
  (verse, manuscript tradition).
- `sources` table: `step_tagnt` + `step_tahot`, kind='interlinear',
  rights='CC BY 4.0', full rights basis with attribution and a record of
  Phos modifications.
- Post-merge checks: staging/inserted/db counts agree; 0 position
  collisions; `PRAGMA integrity_check` ok.

## Coverage

- 31,060 / 31,102 KJV verses (99.86%) have the selected reading.
- The remaining 42 have variant-tradition readings only; all are the known
  textually disputed verses: Mark 16:9-20 (12), John 7:53-8:11 (12),
  Acts 8:37, 15:34, 24:7, 28:29; John 5:4; Luke 17:36, 23:17;
  Matthew 17:21, 18:11, 23:14; Mark 7:16, 9:44, 9:46, 11:26, 15:28;
  Romans 16:24; Joshua 21:36-37.
- Every KJV verse key returns interlinear data (selected or variant).

## API

- `GET /v1/interlinear/{book}/{chapter}/{verse}` (auth required).
  Returns ordered words (original, transliteration, gloss, Strong's,
  morphology, lemma), variant groups by manuscript tradition, testament,
  reading flag (`main`/`variant`), and source attribution.
- Book aliases resolve (`jn`, `1jn`, `ps`); 400 for unknown books and
  out-of-range refs; 404 only if a valid ref has no data (does not occur).
- `api/openapi.json` regenerated; endpoint description carries the
  CC BY 4.0 attribution note.

## Docs

- `docs/public/sources-and-attribution.md`: new Interlinear section with
  per-source table + required attribution text.
- `docs/public/coverage-and-availability.md`: new Interlinear row with
  counts.
- `PLAN.md` decisions log, `BUILD_LOG.md` updated.

## Verification

- Full API suite run independently via `api/.venv/bin/python -m pytest
  tests/ -q`: **185 passed, 3 warnings** (172 pre-existing + 13 new
  interlinear tests in `api/tests/test_interlinear.py`: Genesis 1:1,
  John 1:1, ordering, gloss presence, split-verse concatenation, disputed
  verse, attribution, auth, bad/missing refs, psalm title).
- Spot-checked: Genesis 1:1 (7 Hebrew words, prefixes preserved),
  John 1:1 (17 Greek words), 1 Kings 18:33 (19 words, split concatenated),
  Psalm 3:1 (title first), Mark 16:9 (variant-only, KO/(k)O groups).

## Known limitations

- The 42 disputed verses return only variant-tradition readings by design.
- Strong's sub-entry letters are normalized away (`H1254A` -> `H1254`);
  `/v1/word` addresses base numbers only.
- Interlinear follows KJV versification; translations with different
  versification (e.g. LSG1910's +68 verses) address their own keys.
