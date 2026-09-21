# RVA1909 ingest report (v3, 2026-09-20)

Fourth non-English translation in Phos: Santa Biblia, Reina Valera 1909 (Spanish).
Completes the v3 multilingual set (LSG1910, LUTHER1912, ALMEIDA, RVA1909: 4/4).

## Rights clearance (gate, verified before ingest)

**Digital edition:** eBible.org "Santa Biblia - Reina Valera 1909" (`spaRV1909`), eBible.org certified.

**Rights page (fetched 2026-09-20, saved in data/raw_v2/rva1909/copyright.htm; identical text bundled as copr.htm in the source zip):**
https://ebible.org/spaRV1909/copyright.htm

The edition's copyright page lists the licensing field as:

> Public Domain

with the title "Santa Biblia - Reina Valera 1909", "The Holy Bible in
Spanish, Reina Valera translation of 1909", "Translation by: Reina y
Valera", "Dominio Público", and the eBible.org certified badge. No
copyright holder, no Creative Commons license, no additional terms.

**Why this edition:** eBible.org carries the certified `spaRV1909` edition
with a clean PD statement, the same provenance chain as the LSG1910 and
LUTHER1912 passes. The underlying work is the 1909 revision of the
Reina-Valera Spanish Bible (original 1602; Casiodoro de Reina died 1594,
Cipriano de Valera died 1602).

**Caveat (kept in public docs):** US clearance is by pre-1931 expiry; that
does not by itself establish non-US status.

**Decision:** cleared for free commercial redistribution. No rights
ambiguity on this edition (unlike the Almeida pass).

## Source files

- `spaRV1909_usfm.zip`: 2,380,143 bytes, SHA-256
  `b5bfac87199a561fcbacb5e32be5d8d280934b1c6830088d9eb8c68ffbfbe711`
- Contains 66 USFM book files (`02-GENspaRV1909.usfm` through
  `96-REVspaRV1909.usfm`), source files dated 2015-08-10 (HTML generated
  2026-08-08), plus `copr.htm`, `keys.asc`, `latin.css`.
- Raw kept byte-identical in `data/raw_v2/rva1909/` with `PROVENANCE.md`
  and `sha256sums.txt` (69 entries: zip + copyright.htm + 66 USFM + PROVENANCE.md).
- Pre-scan: 31,102 `\v` lines, all numeric ids, no ranges, no non-numeric ids.

## Ingest

- Parser: `scripts/ingest_rva1909_v3.py` (Python stdlib + sqlite3 only;
  direct mirror of the LSG1910/LUTHER1912 parser). Stages to
  `data/staging/rva1909.db`, table `verses`, translation = 'RVA1909',
  0-based book_order, canonical book names.
- USFM specifics: Strong's-tagged words `\w word|strong="H7225"\w*`
  (attribute dropped, word kept); `\x`/`\f` spans dropped; `\add` inner
  text kept; structural markers skipped; no parser defects this pass.
- **Staged: 31,084 rows**, 66 books, 0 duplicate (book, chapter, verse)
  keys, 0 empty texts, 0 rows with stray markup.
- Merge into `data/scripture.db`: `DELETE FROM verses WHERE
  translation='RVA1909'` (safety no-op) then `INSERT ... SELECT` from
  staging with `CAST(verse AS TEXT)` (live schema stores verse as TEXT,
  same as KJV; verified by `typeof()` audit: all 'text').
- Backup before any write: `data/scripture.db.bak-rva1909-20260920`
  (131,702,784 bytes).
- Post-merge: `PRAGMA integrity_check` = ok; RVA1909 = 31,084 live rows,
  66 books; total verses 490,353 -> **521,437**; 18 distinct translations.

## Verification

- Deterministic three-way check (seed 20260920), script
  `scripts/verify_rva1909_v3.py`, report `data/staging/rva1909-VERIFY.md`:
  raw USFM `\v` line (independently cleaned) == parser output ==
  staging DB text, 5 mandatory anchors + 50 seeded samples:
  **55/55 pass**.
- Staging audits: 31,084 rows, 66 books, 0 duplicate keys, 0 empty texts,
  0 markup leaks.
- 10 well-known verses spot-checked in the live DB, all correct classic
  RV1909 Spanish: Genesis 1:1, John 3:16, Psalms 23:1, Romans 8:28,
  Matthew 6:33, Philippians 4:13, Proverbs 3:5, Isaiah 40:31,
  Jeremiah 29:11, Romans 10:9.
- API suite: **172 passed, 3 warnings** (run via api/.venv python).

## Row-count note

31,084 text-bearing verses, not 31,102. The 18-verse difference is genuine
Spanish versification, kept exactly as the edition prints it (each offset
confirmed by direct text comparison, not just counts):

**Chapter offsets** (empty end-of-chapter placeholder; text printed at the
next chapter's verse 1):
- Numbers 12:16 -> printed at 13:1 ("Y DESPUES movio el pueblo de Haseroth, y asentaron el campo en el desierto de Paran.")
- Numbers 29:40 -> printed at 30:1 ("Y MOISES dijo a los hijos de Israel, conforme a todo lo que Jehova le habia mandado.")
- 1 Samuel 23:29 -> printed at 24:1 ("ENTONCES David subio de alli, y habito en los parajes fuertes en Engaddi.")
- Hosea 11:12 -> printed at 12:1 ("CERCOME Ephraim con mentira, y la casa de Israel con engano...")
- Jonah 1:17 -> printed at 2:1 ("MAS Jehova habia prevenido un gran pez que tragase a Jonas...")

**Merges** (empty placeholder; text merged into the adjacent verse shown):
- 2 Samuel 20:26 -> merged into 20:25 ("...e Ira Jaireo fue un jefe principal cerca de David.")
- 2 Chronicles 33:25 -> merged into 33:24 ("...puso por rey en su lugar a Josias su hijo.")
- Job 35:16 -> merged into 35:15 ("...por eso Job abrio su boca vanamente, y multiplica palabras sin sabiduria.")
- Job 38:39-41 -> printed as 39:1-3 ("CAZARAS tu la presa para el leon?...")
- Job 40:20-24 -> printed as 40:14-19 ("El es la cabeza de los caminos de Dios...")
- Acts 19:41 -> merged into 19:40 ("...Y habiendo dicho esto, despidio la reunion.")
- 2 Corinthians 13:14 -> printed as 13:13 ("La gracia del Senor Jesucristo, y el amor de Dios, y la participacion del Espiritu Santo sea con vosotros todos. Amen.")

Psalm titles are joined to verse 1 in the edition text (same convention as
Luther1912; e.g. "Salmo de David. JEHOVA es mi pastor..." is all in
Psalms 23:1). Full list also in `data/raw_v2/rva1909/PROVENANCE.md`.

## Files changed

- `api/translations.py`: RVA1909 metadata entry (rights + versification
  notes + territorial caveat).
- `api/openapi.json`: regenerated via `api/gen_openapi.py` (OpenAPI 3.1.0;
  translation example lists now carry all 18 codes).
- `api/app.py`: `/v1/translations` description "seventeen" -> "eighteen".
- `api/tests/test_api.py`: health assertion (18-code list, verse_count
  521437), metadata sets, RVA1909 31084 assertion.
- `docs/public/sources-and-attribution.md` and
  `docs/public/coverage-and-availability.md`: 18 translations, 521,437
  verses, RVA1909 rights bullet and versification note.
- `PLAN.md`: v3 multilingual row updated, set marked complete (4/4).
- `BUILD_LOG.md`: entry for this ingest.
