# V2 TSK Cross-References - Staging Report

**Date:** 2026-09-20  
**Database:** `staging/crossrefs.db`  
**Source:** CrossWire TSK v1.4 (Public Domain)

## Final Counts

- **Total rows:** 563,760
- **Distinct heads:** 22,116
- **Phrases extracted:** 64,322
- **Ref-lists parsed:** 76,915
- **Valid refs (expanded):** 575,235

## Skip Counts

- **Invalid refs:** 14 (failed KJV bounds validation)
- **Unresolved:** 807 (parse failures, orphan refs, skipped chapters)
- **Chapter-only:** 0 (chapter-only refs skipped during parsing)
- **Phrases with zero KJV match:** 7,525 (11.7%)

## Schema

Exact schema as required:

```sql
CREATE TABLE sources (
  source_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  retrieved TEXT NOT NULL,
  license TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE crossrefs (
  head_book TEXT NOT NULL,
  head_chapter INTEGER NOT NULL,
  head_verse INTEGER NOT NULL,
  ref_book TEXT NOT NULL,
  ref_chapter INTEGER NOT NULL,
  ref_verse INTEGER NOT NULL
);

CREATE UNIQUE INDEX ux_crossrefs ON crossrefs (
  head_book, head_chapter, head_verse,
  ref_book, ref_chapter, ref_verse
);

CREATE INDEX ix_crossrefs_head ON crossrefs (
  head_book, head_chapter, head_verse
);
```

## Verification

- **PRAGMA integrity_check:** OK
- **Canonical book names:** All 66 books use names from `api/parser.py` (including "Song of Songs")
- **Uniqueness:** Enforced by unique index
- **Leak check:** No HTML tags (`<`, `>`) or entities (`&...;`) found in data

## Spot Checks (Seed 20260920)

10 heads selected deterministically using seed 20260920. Independent raw-source
verification performed by manually reading the TSK raw text and comparing
reference sets.

### PASS (Exact Match)

1. **Genesis 27:37** - 23 refs. Manually verified all phrases ("I have.", "with.",
   "sustained.", "Behold.") and refs match exactly. Includes Ge 27:28 (bare
   number ref after phrase, correctly parsed after bug fix).

2. **Psalms 130:6** - 5 refs. "waiteth." → Ps 63:6, Ps 119:147, Ac 27:29.
   "I say more than they that watch for the morning." → Ps 134:1, Isa 21:8.
   Exact match.

3. **Leviticus 2:13** - 8 refs. "with salt." → Ezr 7:22, Eze 43:24, Mt 5:13,
   Mr 9:49,50, Col 4:6. "the salt." → Nu 18:19, 2Ch 13:5. Exact match.

4. **Judges 6:26** - 3 refs. "build." → 2Sa 24:18. "the ordered place." →
   1Co 14:33,40. Exact match.

### PASS (Plausibility)

5. **Jeremiah 4:27** - 20 refs. Thematically coherent (remnant, "not make a
   full end"): Am 9:8-9, Jer 5:10,18, Ro 9:27-29, Ro 11:1-7.

6. **Jeremiah 5:5** - 34 refs. Plausible for "great men" who broke the yoke:
   Ac 4:26-27, Am 4:1, Eze 22:6-8.

7. **Ezekiel 24:3** - 17 refs. Date references (Eze 1:2, 8:1, 20:1, 26:1, 29:1)
   plausible for parable introduction.

8. **John 11:31** - 6 refs. Mourning/weeping refs (2Sa 12:16-18, Ge 37:35)
   plausible for Mary going to weep.

### AMBIGUOUS

9. **Psalms 19:14** - 12 refs. The phrase "Let." appears in both v13 ("let them
   not have dominion") and v14 ("Let the words of my mouth"). The TSK has a
   single "Let." phrase with refs about acceptable prayer. Aligner assigned to
   v13; v14 arguably more correct based on ref content. Cannot determine
   definitively from raw.

### FAIL

10. **2 Samuel 24:25** - 65 refs (over-assigned). Verse 24 has 0 refs but
    should have phrases ("Nay.", "So David."). The aligner skipped v24 entirely,
    assigning its phrases to v25. Root cause: short generic phrases ("Nay.",
    "So David.") did not match KJV strongly enough to anchor correctly.

## Known Limitations

1. **Short/generic phrases:** The KJV greedy alignment fails for very short
   phrases (1-2 words) that lack distinctive content. This affects ~11.7% of
   phrases (lp=0) and causes verse-skipping as seen in 2Sa 24:24.

2. **Grouped chapters skipped:** Proverbs 10-24 and Isaiah 24-27 are grouped in
   the TSK without verse markers. KJV alignment drifts unreliably across the
   range (e.g., Pr 24 absorbed 3,288 rows). These 19 chapters are EXCLUDED from
   staging.

3. **Chapter coverage:** 1,170 of 1,189 chapters have data. Missing: Pr 10-24
   (15 chaps), Isa 24-27 (4 chaps) - intentionally skipped as above.

## Rejected Sources

- R.A. Torrey/New Treasury 1982: Rejected
- TSK Enhanced (Morton) v1.2: Rejected
- TSKe/TSKe-SR: Rejected
- BibleHub/StudyLight/BibleStudyTools: Not scraped (prohibited)
- GitHub yswords: Rejected (mixed provenance)

## Files

- Database: `staging/crossrefs.db` (563,760 rows)
- Ingest script: `scripts/ingest_v2_crossrefs.py`
- Provenance: `verification/v2/provenance.md`
- Ingest log: `verification/v2/ingest.log`
- This report: `verification/v2/crossrefs_staging_report.md`
