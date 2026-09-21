# V2 Provenance Manifest

**Retrieval Date:** 2026-09-20

## Gill's Exposition of the Entire Bible (1763)

- **URL:** https://archive.org/stream/john-gills-commentary-on-the-whole-bible/John%20Gill%27s%20Commentary%20on%20the%20Whole%20Bible_djvu.txt
- **File:** `data/raw_v2/gill/gill_commentary.txt`
- **Size:** 49,188,464 bytes
- **SHA-256:** `0bd13225955a61956d826299122e7d8946a7c7b81a17e9e70395576e32c073ea`
- **Title:** John Gill's Exposition of the Entire Bible (England: n.p, 1763)

## Rights Basis (Gill)

John Gill died in 1771. The 1763 edition is public domain. The Internet
Archive OCR text is a mechanical reproduction of the public-domain work
and creates no new copyright. Commercial use allowed, no attribution
required. No copyrighted Bible translations are included in the
commentary text.

## TSK Cross-References

- **URL:** https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/TSK.zip
- **File:** `data/raw_v2/tsk/TSK.zip`
- **SHA-256:** `6784c7099465995a8e66f02ead82b0bca66603c1bdeaf8332949774b7bfd4293`
- **Module Title:** Treasury of Scripture Knowledge
- **Module Version:** 1.4
- **SwordVersionDate:** 2001-12-15
- **DistributionLicense:** Public Domain

## Rights Basis

The module metadata declares `DistributionLicense=Public Domain`. The module
description attributes the material to Canne, Browne, Blayney, Scott, and others,
"about 1880".

## Provenance Qualification

This is a CrossWire public-domain transcription of the historical/original
Treasury of Scripture Knowledge tradition, version 1.4. The transcription itself
does not date to 1836. The module's "about 1880" description is an open
provenance qualification: the exact relationship between this transcription and
the 1836 first edition has not been independently verified.

## Rejected Editions

The following were explicitly rejected and NOT used:

- R.A. Torrey / New Treasury of Scripture Knowledge (1982)
- Timothy S. Morton TSK Enhanced v1.2 (copyright 2010)
- TSKe and TSKe-SR (modern enhanced editions)
- GitHub `yswords` (mixed hand-curated TSK with OpenBible CC-BY)
- BibleStudyTools, StudyLight, BibleHub, and similar web presentations
- Any modern derivative or source with ambiguous provenance

## Module History (from tsk.conf)

- `History_1.4`: minor corrections to scripture references
- `History_1.3`: converted to ThML with formatting corrections
- `History_1.2`: re-compiled to correct module driver problem

## OpenScriptures HebrewLexicon (BDB transcription, CC BY 4.0)

- **URL:** https://github.com/openscriptures/HebrewLexicon
- **Files:** `data/raw_v2/bdb/HebrewStrong.xml` (8674 entries, H1-H8674)
- **Commit:** `21c9add13bc727d3a951361778e97e3ff7afd1ce` (2019-09-02)
- **Retrieval date:** 2026-09-20
- **SHA-256 (HebrewStrong.xml):** `a628f4f89f8bdaf2483fd3faf1abc8653cc6717758dfc9f24beb7571d9bdd0c4`
- **SHA-256 (BrownDriverBriggs.xml):** `2b52658a4323d91674cda4090ab8b3ebddfff640f4f18143c28300e80b2c38f8`
- **SHA-256 (LexicalIndex.xml):** `8f7a605c58899d2f44430149c143c00903976e1e91232476677972a69e5bc85f`
- **License:** CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **Staging DB:** `data/staging/bdb_staging.db` (8674 rows, script `scripts/ingest_bdb.py`)

## Rights Basis (BDB)

The repo readme.md releases the XML transcription files under CC BY 4.0;
the underlying Brown-Driver-Briggs (1906) and Strong's Hebrew dictionary
text remain public domain. CC BY 4.0 was approved for Phos on 2026-09-20;
attribution must appear in the API docs/code.

**Required attribution:** "Brown-Driver-Briggs Hebrew lexicon XML
transcription by the Open Scriptures Hebrew Bible Project, licensed under
CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)."

## STEPBible Lexicon Data (CC BY 4.0)

- **URL:** https://github.com/STEPBible/STEPBible-Data (sparse checkout, Lexicons/ only)
- **Commit:** `b99716b0cddb648ddb95cc786a197180f2f97d48` (2026-09-18)
- **Retrieval date:** 2026-09-20
- **Files** (`data/raw_v2/stepbible/step/Lexicons/`):
  - `TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt` — SHA-256 `464dccadd95fd8620dd05fa0d7a4caba58ec3c4d5db3ebf38e43d046ca25b591`
  - `TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt` — SHA-256 `312f723d7b8ef263bbdfb0451c9b8057125804dfff390b6f8544cff2a84b57f4`
  - `TFLSJ  0-5624 - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt` — SHA-256 `fcc2845412132a7bb91fc3dbb5a544c807daf57e4791c4d9af61efe209e97691`
  - `TFLSJ extra - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt` — SHA-256 `fdb2840067faa11301b208a343a9453fbe40b367e94eac981071261626201bc2`
- **License:** CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **Staging DB:** `data/staging/stepbible_staging.db` (33,751 rows, script `scripts/ingest_stepbible.py`)

## Rights Basis (STEPBible)

Each lexicon file header states: "Data created by www.STEPBible.org based
on work at Tyndale House Cambridge (CC BY 4.0)". TBESH is based on abridged
BDB; TBESG on Abbott-Smith (gaps from Middle Liddell); TFLSJ edited from the
full LSJ by Tyndale House scholars. CC BY 4.0 approved for Phos 2026-09-20;
attribution must appear in the API docs/code.

**Required attribution:** "STEPBible lexicon data (TBESH, TBESG, TFLSJ),
Tyndale House, Cambridge, licensed under CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). Source:
https://github.com/STEPBible/STEPBible-Data, www.STEPBible.org."
