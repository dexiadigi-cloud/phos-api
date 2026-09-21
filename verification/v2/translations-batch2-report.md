# Phos v2 — Translations batch 2 verification report

Date: 2026-09-20. Backup: `data/scripture.db.bak-translations-batch2-20260920`
(35,127,296 bytes, taken before any writes).

## Rights gate (read before ingest)

| Code | Name | License page / evidence | Finding |
|------|------|------------------------|---------|
| YLT | Young's Literal Translation | https://ebible.org/engylt/copyright.htm + `engylt/copr.htm` in zip | Public Domain ("This public domain Bible translation is brought to you courtesy of eBible.org.") |
| DARBY | Darby Translation 1890 | https://ebible.org/engDBY/copyright.htm + `engDBY/copr.htm` | Public Domain (eBible marks this edition Public Domain) |
| DRB | Douay-Rheims 1899 American Edition | https://ebible.org/engDRA/copyright.htm + `engDRA/copr.htm` | Public Domain ("This Public Domain Bible text is brought to you courtesy of eBible.org.") |
| BBE | Bible in Basic English | https://ebible.org/engBBE/copyright.htm + `engBBE/copr.htm` | Public Domain **in the United States** ("fell immediately and irretrievably into the Public Domain in the United States according to the UCC convention"). Non-US rights not verified; recorded as a caveat in `api/translations.py`. |
| GENEVA | Geneva Bible 1599 | https://ebible.org/bible/details.php?id=enggnv (Public Domain listing) + `enggnv/copr.htm` | Public Domain ("freely available world-wide, with no copyright restrictions, courtesy of eBible.org and many others"). Original 1599 spelling. |
| AKJV | American King James Version | eBible does NOT carry AKJV (engAKJV 404). Source: BibleCorps/ENG-B-AKJV2018-pd-PSFM on GitHub (repo filenames carry `[PD]`; `\id` lines read "Public Domain on November 8, 1999"). Author dedication (Engelbrite, 1999-11-08), quoted verbatim in the getBible akjv `distribution_about` and independently on biblesupport.com / bibliatodo.com: "I am hereby putting the American King James version of the Bible into the public domain on November 8, 1999. You may use it in any manner you wish: copy it, sell it, modify it, etc. You can't copyright it or prevent others from using it." | Public Domain by author dedication. **Documented conflict:** getBible v2's aggregator metadata for its akjv distribution (2.1, 2023-12-27, sourced from the same BibleCorps repo) labels it "Copyrighted; Free non-commercial distribution". Phos ingests the BibleCorps PD edition directly, not the getBible distribution; the conflict is recorded in `api/translations.py` so the final call stays with the project owner. |
| OEB | Open English Bible (US spelling) | https://ebible.org/engoebus/copyright.htm + `engoebus/copr.htm` | Public Domain (eBible marks Public Domain; OEB is CC0 per OpenEnglishBible.org). |

No translation skipped. All seven passed the gate on primary-source evidence
(eBible copyright pages / bundled copr.htm, author's own dedication).

## Sources and provenance

- 6 translations: eBible USFX zips, `https://ebible.org/Scriptures/<code>_usfx.zip`,
  retrieved 2026-09-20, stored under `data/raw_v2/translations_batch2/`.
  - engylt (2,842,597→ zip 1,479,383 bytes), engDBY (2,761,760),
    engDRA (2,946,666), engBBE (2,842,597), enggnv (1,500,054),
    engoebus (1,281,694).
- AKJV: `https://github.com/BibleCorps/ENG-B-AKJV2018-pd-PSFM`, `p.sfm/`
  directory, 69 files (66 books + FRT/INT/GLO peripherals, skipped),
  retrieved 2026-09-20, stored under
  `data/raw_v2/translations_batch2/akjv_psfm/`. Edition: Version 2023.1223.

## Ingest

Script: `scripts/ingest_translations_batch2.py`.
USFX: verses extracted from `<v bcv="BOOK.CH.V"/>...<ve/>` spans; footnotes
(`<f>`) and section heads (`<s>`) dropped, all other inline markup
(`<w>`, `<wj>`, `<nd>`, `<q>`, `<bd>`, ...) unwrapped with inner text kept,
whitespace normalized. AKJV: p.sfm `\v N` lines parsed, USFM markers
stripped, same normalization. 0-based `book_order` matching existing
convention (Genesis=0 .. Revelation=65). No duplicate (book, chapter, verse)
keys in any translation.

## Row counts

| Code | Rows | Books | Notes |
|------|------|-------|-------|
| YLT | 31,102 | 66 | matches raw `<v>` count exactly |
| DARBY | 31,099 | 66 | 3 fewer than KJV versification (raw `<v>` count matches) |
| DRB | 35,811 | 73 | 7 deuterocanonical books included |
| BBE | 31,102 | 66 | matches raw `<v>` count exactly |
| GENEVA | 31,090 | 66 | raw `<v>` count matches |
| AKJV | 31,102 | 66 | matches raw `\v` count exactly |
| OEB | 13,894 | 44 | partial OT (full NT + Genesis, Joshua, Ruth, Esther, Psalms, Hosea-Malachi); 19 raw verses dropped as empty after markup strip |

Total verses table: 329,569 rows (was 124,369).

## Deuterocanon book_order mapping (DRB)

Appended after the 66-book ordering; no collision with existing 0-65 values:

| book_order | Book |
|------------|------|
| 66 | Tobit |
| 67 | Judith |
| 68 | Wisdom |
| 69 | Sirach |
| 70 | Baruch |
| 71 | 1 Maccabees |
| 72 | 2 Maccabees |

`api/parser.py` `CANONICAL_BOOKS` and abbreviation map extended so
`/v1/passage?ref=Tobit+1:1` etc. resolve. DRB Psalms follow Vulgate
numbering (DRB Psalm 118 = KJV Psalm 119); documented in the translation
notes surfaced by `/v1/translations`.

## Seeded raw-to-database verification

Script: `verification/v2/verify_translations_batch2.py`, seed `20260920`.
Independent minimal re-extraction from the raw source files (string search,
not the ingest regex) compared exactly against DB text.

Result: **98/98 passed** (10 famous passages per translation: Gen 1:1,
John 3:16, Ps 23:1, Rom 8:28, Ps 119:105, Phil 4:13, Prov 3:5, Matt 5:3,
Isa 40:31, 1 Cor 13:4; +2 DRB deuterocanon passages; +4 seeded random
verses per translation; OEB list trimmed to books it contains; DRB Psalm
refs use Vulgate numbering).

## Integrity and FTS

- `PRAGMA integrity_check` on `data/scripture.db`: **ok**.
- FTS: `INSERT INTO verses_fts(verses_fts) VALUES('rebuild')` executed;
  `verses_fts` now holds 329,569 rows, equal to the verses table. Spot
  check: `/v1/search?q=grace&translation=GENEVA` returns hits (covered by
  test).

## API / tests / OpenAPI

- `api/translations.py`: 7 new entries (code, name, edition, source URL,
  retrieved date, rights block, notes incl. BBE territorial caveat, AKJV
  license conflict, OEB partial coverage, DRB numbering).
- `api/app.py`: `TranslationInfo` gains optional `notes`; `/v1/translations`
  description updated ("All eleven translations are public domain").
- Full pytest suite (`api/tests/`, venv at `api/../.venv` since the system
  python has no pytest/fastapi): **115 passed** (106 pre-existing + 9 new),
  3 pre-existing Pydantic/starlette deprecation warnings.
- New tests (`api/tests/test_translations_batch2.py`): per-translation
  counts, DB-verified John 3:16 markers (incl. Geneva original spelling),
  DRB 73-book list + deuterocanon orders + Tobit verse + parser aliases,
  OEB 44-book partial coverage, FTS search on GENEVA, `/v1/passage` on
  DRB Tobit 1:1-3, `/v1/books` DRB count. Updated `test_health_no_auth`
  (11 codes, 329,569 verses) and `test_translations_metadata` (11 codes,
  per-code counts).
- `api/openapi.json` regenerated (OpenAPI 3.1.0); spec diff reflects the
  new `notes` field and updated descriptions.

## Known limitations

- Darby has 31,099 verses vs KJV's 31,102 (source versification; raw count matches).
- Geneva has 31,090 (raw count matches).
- OEB covers 44 books only; reading plans referencing missing books will
  behave as they do for any absent verse (pre-existing behavior, not redesigned).
- BBE public-domain status is US-specific per eBible; worldwide commercial
  use outside the US is not verified.
- AKJV: see the documented getBible metadata conflict above.
- DRB Psalm numbering is Vulgate; cross-translation Psalm comparisons need
  the offset.
