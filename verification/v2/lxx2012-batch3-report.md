# LXX2012 batch-3 ingest report (2026-09-20)

Ingestion worker batch for Phos (Dexia Bible API). Approved by Jeremiah
2026-09-20. Staging only: `data/scripture.db` and `data/study.db` were
not touched; the coordinator merges later.

## Provenance verdict: PUBLIC DOMAIN, cleared for use

Source: eBible `eng-lxx2012` USFX edition, downloaded 2026-09-20 from
https://ebible.org/Scriptures/eng-lxx2012_usfx.zip
(SHA-256 `6f4018d9cde4e49fa176bb546fd0c52423fd974e46105e50f02e6b6a831cdce4`).

The edition's own copyright page (shipped inside the downloaded file)
states Brenton's 1851 translation "has entered the Public Domain due to
the passage of sufficient time" and that Michael Paul Johnson's language
updates "are dedicated to the Public Domain by the author of those edits
... Therefore this edition may be freely copied, published, etc." The
DBL metadata in the same package repeats the PD dedication. Full quotes
and method: `data/raw_v2/lxx2012/PROVENANCE.md`. Ingest proceeded.

Translation-code check: `LXX2012` does not collide with any existing
code (AKJV, ASV, BBE, BSB, DARBY, DRB, GENEVA, KJV, OEB, WEB, YLT).

## Row counts

**28,352 rows** staged in `data/staging/lxx2012.db`, table `verses`
(schema exactly: translation TEXT, book TEXT, book_order INTEGER,
chapter INTEGER, verse INTEGER, text TEXT; all rows
translation='LXX2012'). 54 books: 39 canonical OT (book_order 0-38) +
15 deuterocanonical (66-80).

Deuterocanon row counts: Tobit 245, Judith 339, Wisdom 436, Sirach 1391,
Baruch 140, 1 Maccabees 924, 2 Maccabees 555, Epistle of Jeremy 73,
Prayer of Azarias 67, Susanna 64, Bel and the Dragon 42, 1 Esdras 448,
Prayer of Manasses 14, 3 Maccabees 228, 4 Maccabees 483.

## Versification caveat (plain terms)

LXX2012 uses **Greek Septuagint numbering, not the Hebrew numbering**
used by KJV/WEB/etc. Verse addresses were kept exactly as the source
gives them, so cross-translation verse lookup by (book, chapter, verse)
will NOT line up 1:1 with Hebrew-based translations. Concretely:

- Psalms has **151 psalms** in Greek numbering. LXX2012 Psalm 23:1 is
  "The earth is the Lord's and the fullness thereof" - that is Hebrew
  Psalm 24:1. Psalm 151 exists.
- Names in the text are transliterated from Greek (Esias, Jeremias,
  Osee, Ambacum); DB book names follow the Phos convention anyway.
- Some verses are merged paragraphs in the source (e.g. 1 Kings 7:1-12
  as one unit); stored under the range's starting verse.
- 1 Kings prints some verses only as `<vp>`-numbered paragraphs in
  Brenton's ordering (3:36-46, 7:1-12, parts of ch 6 and 11); these are
  ingested under their `<vp>` numbers, and 4 colliding keys
  (1KI 6:17, 11:1, 11:3, 11:6) join their texts in document order.
- **Known source gap:** 1 Kings 14:1 (placeholder for vv 1-20) has
  empty text in this edition; the text is not supplied. Row kept, flagged.

API consumers should treat LXX2012 verse addresses as
translation-scoped.

## Deterministic verification (seed 20260920): PASS

`scripts/verify_lxx2012.py` -> `data/staging/lxx2012-VERIFY.md`:

- Schema exact; all rows translation='LXX2012'; 28,352 rows. PASS
- Full-table re-parse compared row-for-row against staging DB:
  0 mismatches, 0 extras. PASS
- 50 seeded verse keys (>=10 deuterocanonical, >=10 Psalms) extracted
  from the raw USFX by an independent extractor and compared
  character-for-character to the DB rows: **50/50 PASS**.

## Test fragment

`api/tests/batch3_frag_lxx2012.py` (not collected until assembled):
row-count constant (28352), 4 seeded spot-checks (incl. Greek-numbered
Psalm 23:1 and Tobit 12:7), deuterocanon presence + book_order check
for all 15 books, no-NT-books check, Psalm 151 existence check.

## Files produced

- Raw + provenance: `data/raw_v2/lxx2012/` (zip, unpacked `usfx/`,
  `PROVENANCE.md`)
- Parser: `scripts/ingest_lxx2012.py`
- Verifier: `scripts/verify_lxx2012.py`
- Staging DB: `data/staging/lxx2012.db` (28,352 rows)
- Book map: `data/staging/lxx2012-BOOKMAP.md`
- Verification log: `data/staging/lxx2012-VERIFY.md` (50/50 per-sample
  pass/fail table)
- Test fragment: `api/tests/batch3_frag_lxx2012.py`

## Proposed log entries (for coordinator; files NOT edited)

PLAN.md - append under batch-3 translations:
`- [x] LXX2012 staged (2026-09-20): 28,352 rows, 54 books, PD cleared
  per edition copr.htm; Greek versification kept as-is (translation-scoped
  numbering); staging DB data/staging/lxx2012.db; verify 50/50 PASS
  (data/staging/lxx2012-VERIFY.md); test fragment
  api/tests/batch3_frag_lxx2012.py ready for assembly. Merge pending.`

BUILD_LOG.md - append:
`2026-09-20 - LXX2012 (Brenton/Johnson 2012 Septuagint, PD) ingested to
 staging: 28,352 verses, 54 books incl. 15 deuterocanonical (orders 66-80).
 Rights verified against edition's own copr.htm (PD dedication quoted in
 PROVENANCE.md). Greek Psalm numbering preserved (151 psalms); 1KI
 <vp>-appendix verses merged; 1KI 14:1 empty-text source gap flagged.
 Deterministic verify seed 20260920: full-table 0 mismatches, 50/50
 char-for-char sample PASS. scripture.db untouched; merge pending
 coordinator.`

## Open items for the coordinator

1. Merge `data/staging/lxx2012.db` into `data/scripture.db` (translation
   code LXX2012; verse column is INTEGER here vs TEXT convention in
   scripture.db - cast on merge or keep INTEGER, decide once for all
   batch-3 translations).
2. Assemble `api/tests/batch3_frag_lxx2012.py` into the API suite and run.
3. Decide how the API surfaces the translation-scoped numbering caveat
   (e.g. a `versification: "greek"` flag on the translation record).
