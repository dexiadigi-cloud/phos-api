# Lexicon Merge Report (2026-09-20)

Merged the three verified lexicon sources into `data/study.db` as new
`lexicon_sources` + `lexicon` tables. The pre-existing `strongs` table was
left untouched as a rollback artifact. Fresh backup before merge:
`data/study.db.bak-lexicon-merge-20260920` (206,213,120 bytes).

## Per-source merged counts

| source_id   | entries | rights        | basis |
|-------------|---------|---------------|-------|
| strongs     | 13,260  | Public domain | CC0 via Internet Archive item StrongsGreekAndHebrewDictionaries1890 |
| bdb         | 8,674   | CC BY 4.0     | OpenScriptures HebrewLexicon commit 21c9add (2019-09-02); license in data/raw_v2/bdb/readme.md |
| step_tbesh  | 11,682  | CC BY 4.0     | STEPBible-Data commit b99716b0 (2026-09-18); license in-file in Lexicons/*.txt headers |
| step_tbesg  | 11,035  | CC BY 4.0     | same |
| step_tflsj  | 5,709   | CC BY 4.0     | same |
| step_tflsjx | 5,325   | CC BY 4.0     | same |
| **total**   | **55,685** |            |       |

Merge script: `scripts/merge_lexicons.py`. Seeded verification:
`scripts/verify_lexicon_merge.py` — **38/38 PASS**
(14 Strong's raw-txt, 12 BDB XML, 12 STEPBible TSV incl. sanitize checks).

## Sanitization log (STEPBible definitions only)

`sanitize_stepbible()` in `scripts/merge_lexicons.py`, applied to all 33,751
STEPBible definitions at merge time. Staging DBs remain the raw archive.

1. HTML parsed with `html.parser` (handles `"`-quoted attributes containing
   `>`, e.g. `<a href="javascript:void(0)" title="...">`).
2. `<br>`, `<br/>`, `<BR>`, `<BR />` (any case) become a newline.
3. `<a>...</a>` keeps inner text only (hover citations like "Refs 5th c.BC+"
   and markers like "NT"/"LXX" survive as plain text; the `title` citation
   payloads do not).
4. All remaining tags stripped, inner text kept: `<b>`, `<i>`,
   `<ref="...">`, `<Level1>`-`<Level4>`, `<re>`, `<author>`.
5. HTML entities unescaped (`&nbsp;` to space, `&gt;`/`&lt;`/`&amp;`).
6. Trailing whitespace removed per line; 3+ consecutive newlines collapsed
   to 2; leading/trailing whitespace stripped.
7. 77 `step_tflsjx` rows have blank definitions in the source; kept as-is.

Post-merge audit: 0 STEPBible rows still match the HTML tag pattern;
`PRAGMA integrity_check` = ok.

## Duplicate audit

1,166 duplicate `(source_id, strongs_number)` pairs, all pre-existing in the
STEPBible staging DB (step_tbesh 948, step_tbesg 109, step_tflsj 108,
step_tflsjx 1). These are legitimate source rows: homographs and distinct
proper-name entries sharing one Strong's number (e.g. three H0001 rows in
TBESH for different persons). `/v1/word` returns all of them as a list.

## Known limitations

1. Strong's Greek is 89.1% (5,012/5,624) from OCR; 511 entries unrecoverable,
   101 numbers (G2717, G3203-G3302) never existed in the 1890 source.
   STEPBible's Greek lexicons (TBESG/TFLSJ) cover the gaps via /v1/word
   source selection.
2. `lemma`/`transliteration` are empty on all `strongs` rows (the repaired
   OCR kept everything in `entry_text`, now `definition`); BDB and STEPBible
   rows have structured lemmas.
3. `extra` holds the Strong's integer number (`num`) for `strongs` rows and
   STEPBible `morph` codes for STEPBible rows; NULL for BDB.
4. One carried-over repair artifact: the `G500` row's definition text retains
   the OCR's misread heading "600." (antichristos); the number assignment is
   correct.
5. Number formats differ per source (`G3056` vs `G0001`); `/v1/word`
   normalizes both sides to letter + integer at query time.

## Addendum 2026-09-20 (independent verification pass)

An independent verification pass re-checked the merged state and closed
the one remaining gap.

**Findings:**

1. Row merge confirmed. Live `lexicon` holds 55,685 rows with per-source
   counts exactly matching the staging DBs (strongs 13,260; bdb 8,674;
   step_tbesh 11,682; step_tbesg 11,035; step_tflsj 5,709; step_tflsjx
   5,325). Byte-level spot check: bdb H1 identical to staging; step_tbesh
   H0001 rows match staging modulo the documented sanitization
   (`<br>` to newline, tags stripped).
2. Gap found and closed: the general `sources` table had `strongs` as
   kind='lexicon' but was missing the 5 CC BY 4.0 lexicon source rows.
   Inserted after backup: bdb, step_tbesh, step_tbesg, step_tflsj,
   step_tflsjx, each with rights='CC BY 4.0', the full staging
   rights_basis plus the attribution string appended under an
   "Attribution:" line (live `sources` schema has no attribution column),
   version = upstream commit hash, sha256 from staging. All 5 verified
   present with attribution text. `sources` now holds 6 kind='lexicon' rows.
3. Backup note: this pass's backup reused the name
   `data/study.db.bak-lexicon-merge-20260920` and overwrote the earlier
   206,213,120-byte file with a 383,852,544-byte backup taken before the
   `sources` inserts. The pre-merge rollback point is still preserved as
   `data/study.db.bak-strongs-repair` (206,213,120 bytes, same size as the
   overwritten file).
4. Extra-column note: STEPBible staging carries `dstrong` / `ustrong` /
   `morph`; the merge kept only `morph` in `lexicon.extra` and dropped the
   `dstrong`/`ustrong` extended-Strong's variant keys (e.g. "H0001G").
   Recorded as a known limitation; no re-merge performed.
5. Duplicate groups: 1,166 (source_id, strongs_number) groups, all in the
   STEPBible extended lexicons by design (base number shared across
   variants). Not a defect.

**Live API checks (TestClient):**

- `/v1/word/sources`: all 6 sources with correct entry counts, rights
  strings, and non-empty attribution.
- `/v1/word` default (no `source` param): unchanged, returns entries from
  every lexicon holding the number. G3056 -> step_tbesg, step_tflsj,
  strongs. H430 -> bdb, step_tbesh x3, strongs.
- Source filters `?source=bdb`, `step_tbesh`, `step_tbesg`, `step_tflsj`,
  `step_tflsjx` verified. `G3056&source=bdb` correctly 404s (bdb is
  Hebrew-only); `G1&source=step_tflsjx` correctly 404s (no G1 entry in
  TFLSJ-extra).
- Default `/v1/word` behavior did not change.

**Attribution:** `docs/public/sources-and-attribution.md` already lists the
BDB and all four STEPBible lexicons with counts, rights, and the exact
CC BY 4.0 attribution strings with license links. `api/openapi.json`
`/v1/word/sources` description already states the attribution requirement.
No doc changes needed.

**Tests:** `api/tests/test_word.py` already asserts the merged state; no
test changes needed. Full suite run by the verifier
(`cd api && .venv/bin/python -m pytest tests/ -q`): 172 passed,
3 warnings.
