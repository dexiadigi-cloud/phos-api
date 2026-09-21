# ALMEIDA ingest report (v3, 2026-09-20)

Third non-English translation in Phos: Biblia Almeida Recebida (Portuguese).

## Rights clearance (gate, verified before ingest)

**Digital edition:** Biblia Almeida Recebida v1.7, almeidarecebida.org
("A Traducao do Texto Recebido (Textus Receptus)"). A revision of Joao
Ferreira de Almeida's Portuguese Bible based on the Textus Receptus, with
updated Portuguese language. Source dump generated March 17, 2017.

**Download page:** https://www.almeidarecebida.org/download-portuguese-bible-almeida-recebida-xml/
(retrieved 2026-09-20; saved in data/raw_v2/almeida/download-page-2017-statement.html)

**Download URL:** https://www.almeidarecebida.org/files/Almeida-Recebida-(version-1.7).mysql.zip
(retrieved 2026-09-20)

The publisher's download page states: **"This Bible (PorAR) is in the
Public Domain."** The same page also carries a generic "Notice: This work
is licensed under a BY-NC-SA" line. That line reads as the site's
WordPress CC-plugin footer (it sits among "Categories: Uncategorized" and
"Permalink:" post metadata) rather than a statement about the Bible text;
the specific statement about the Bible text is Public Domain. A third
party (bible-discovery.com, "Bíblia Almeida Recebida (AR) (PorAR)") 
independently lists "Distribution license: Public Domain" with TextSource
http://www.almeidarecebida.org/. No CC BY-SA or other encumbered license
is asserted against the Bible text itself.

**Why this edition:** eBible.org hosts no Almeida edition (Scriptures
index checked 2026-09-20; Portuguese editions are porblt, porbr2018,
porbrbsl, poronbv, portft, none Almeida). The 1848/1850 Almeida PDFs on
almeidarecebida.org are clearly PD by age but exist only as OCR'd scans
(ABBYY FineReader text layer with typical hyphenation/column defects); no
clean digital edition of those exists. Wikisource's 1819 transcription is
incomplete (86 pages, 6 books partial, some chapters missing). Almeida
Recebida is the clean digital edition with a public-domain declaration
from its publisher.

**Caveat (kept in public docs):** clearance rests on the publisher's
public-domain declaration, which does not by itself establish status in
every jurisdiction.

**Decision:** cleared for free commercial redistribution, with the
dual-statement ambiguity documented here and in PROVENANCE.md.

## Source files

- `Almeida-Recebida-(version-1.7).mysql.zip`: 1,478,663 bytes, SHA-256
  `e6c2b73a9b692e72a179df6b70735f2a7c9c60792e7fe6ad29be2664deaf615c`
- Contains `pt_nar.sql` (4,643,189 bytes, SHA-256
  `9de5dfed4583bf3906be85177541fed70af85cda1ee0a5d44eb7c49712e1ebdc`),
  phpMyAdmin dump of table `pt_nar(id, book_id, chapter, verse, pt_nar)`,
  AUTO_INCREMENT=31103, source files dated 2017-03-17.
- Raw kept byte-identical in `data/raw_v2/almeida/` with `PROVENANCE.md`
  and `sha256sums.txt`.

## Ingest

- Parser: `scripts/ingest_almeida_v3.py` (Python stdlib + sqlite3 only).
  Stages to `data/staging/almeida.db`, table `verses`, translation =
  'ALMEIDA', 0-based book_order, canonical book-name table shared with
  the LSG1910/LUTHER1912 parsers.
- Source specifics: book_id 1-66 maps to Genesis-Revelation (verified:
  book_id 43 / chapter 3 / verse 16 reads John 3:16 in Portuguese).
  Verse text uses doubled single-quotes (`d''agua`) and backslash
  escapes; both are unescaped (19 rows use the doubled-quote form; a
  first-pass regex missed them and was fixed before staging). No markup
  in this edition (plain text).
- Merge into `data/scripture.db`: `DELETE FROM verses WHERE
  translation='ALMEIDA'` (safety no-op) then `INSERT ... SELECT` from
  staging with `CAST(verse AS TEXT)` (live schema stores verse as TEXT,
  same as KJV; verified by `typeof()` audit: all 'text').
- Backup before any write: `data/scripture.db.bak-almeida-20260920`
  (124,993,536 bytes).

## Verification

- Deterministic three-way check (seed 20260920), script
  `scripts/verify_almeida_v3.py`, report
  `data/staging/almeida-VERIFY.md`: raw SQL literal (independently
  extracted and unescaped) == parser output == staging DB, 5 mandatory
  anchors + 50 seeded samples: **55/55 pass**.
- Staging audits: **31,102 rows**, 66 books, 0 duplicate (book, chapter,
  verse) keys, 0 empty texts, 0 rows with stray markup.
- Post-merge: `PRAGMA integrity_check` = ok; ALMEIDA = 31,102 live
  rows; verse column all TEXT; total verses 459,251 -> **490,353**;
  17 distinct translations.
- 10 well-known verses spot-checked in the live DB, all correct classic
  Almeida Portuguese: Genesis 1:1, John 3:16, Psalms 23:1, Romans 8:28,
  Matthew 6:33, Philippians 4:13, Proverbs 3:5, Isaiah 40:31,
  Jeremiah 29:11, Romans 10:9.

## Row-count note

31,102 verse keys, exactly matching KJV. No versification deltas: Almeida
Recebida follows KJV numbering throughout.

## Files changed

- `api/translations.py`: ALMEIDA metadata entry (rights + versification
  notes + territorial caveat).
- `api/openapi.json`: regenerated via `api/gen_openapi.py` (OpenAPI 3.1.0;
  translation example lists now carry all 17 codes).
- `api/app.py`: `/v1/translations` description "sixteen" -> "seventeen".
- `api/tests/test_api.py`: health assertion (17-code list, verse_count
  490353) and translations-metadata assertion (17-code set, ALMEIDA
  verse_count 31102).
- `docs/public/sources-and-attribution.md`: ALMEIDA table row + rights
  bullet (including the dual-statement note); "All 16 translations" ->
  "All 17 translations".
- `docs/public/coverage-and-availability.md`: "17 translations, 490,353
  verses total"; ALMEIDA table row; versification coverage note.
- `PLAN.md`: v3 multilingual row updated (ALMEIDA done; RVA1909 still
  open).
- `BUILD_LOG.md`: entry appended.
- New: `scripts/ingest_almeida_v3.py`,
  `scripts/verify_almeida_v3.py`, `data/raw_v2/almeida/` (zip, SQL,
  PROVENANCE.md, sha256sums.txt, download-page statement),
  `data/staging/almeida.db`, `data/staging/almeida-VERIFY.md`.

## API suite

Run directly 2026-09-20 (`cd api && .venv/bin/python -m pytest tests/ -q`):
**172 passed, 3 warnings.** (System python3 lacks pytest/fastapi, so the
api/.venv python was used; `gen_openapi.py` needs `PHOS_API_KEY` set,
same as the test conftest.)
