# V2 Liturgy Staging Report: BCP 1662 and BCP 1928 Morning/Evening Prayer

**Date:** 2026-09-20
**Status:** Staged. `staging/liturgy.db` built deterministically from raw sources.
**Scope:** Fixed text of Morning Prayer and Evening Prayer only. 30-day Psalter and lectionary tables excluded (see Gaps).

## Outputs

| Artifact | Path |
|---|---|
| Staging DB | `~/workspace/scripture-desk/staging/liturgy.db` |
| Ingestion script | `~/workspace/scripture-desk/scripts/ingest_v2_liturgy.py` |
| 1662 raw pages | `~/workspace/scripture-desk/data/raw_v2/bcp1662/ws1662_page057.txt` through `ws1662_page081.txt` |
| 1662 provenance | `~/workspace/scripture-desk/data/raw_v2/bcp1662/ws1662_provenance.json` |
| 1928 raw files | `~/workspace/scripture-desk/data/raw_v2/bcp1928/mp.htm`, `ep.htm` |
| 1928 provenance | `~/workspace/scripture-desk/data/raw_v2/bcp1928/provenance.json` |

## Row counts

| Edition | Office | Rows |
|---|---|---|
| bcp1662 | morning_prayer | 198 |
| bcp1662 | evening_prayer | 134 |
| bcp1928 | morning_prayer | 217 |
| bcp1928 | evening_prayer | 154 |
| **Total** | | **703** |

## Schema

```sql
CREATE TABLE sources (
  id INTEGER PRIMARY KEY,
  edition TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  source_url TEXT NOT NULL,
  retrieved_utc TEXT NOT NULL,
  rights_basis TEXT NOT NULL
);
CREATE TABLE liturgy (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  office TEXT NOT NULL,          -- morning_prayer | evening_prayer
  section TEXT NOT NULL,         -- controlled vocabulary (below)
  label TEXT,                    -- e.g. canticle name, collect name
  seq INTEGER NOT NULL,          -- 1-based order within (source, office)
  speaker TEXT,                  -- minister | priest | people | null
  kind TEXT NOT NULL,            -- text | rubric | cue | heading | gap
  text TEXT NOT NULL,
  sidenote TEXT,                 -- 1662 marginal scripture references
  UNIQUE (source_id, office, seq)
);
```

### Controlled section vocabulary (15 values)

`title`, `opening_rubric`, `sentence`, `exhortation`, `confession`, `absolution`,
`lords_prayer`, `versicle`, `canticle`, `creed`, `suffrage`, `collect`, `prayer`,
`grace`, `closing`

## Provenance and rights basis

### BCP 1662
- **Source:** Wikisource, "Book of Common Prayer (1892)" - described as an 1892
  Pickering reproduction of the manuscript annexed to the Act of Uniformity 1662,
  reproduced "verbatim et literatim."
- **URL:** https://en.wikisource.org/wiki/Book_of_Common_Prayer_(1892)
- **Pages:** 57 (common introductory rubrics) through 81. Morning Prayer: 58-71.
  Evening Prayer: 72-81.
- **Revision pinning:** Each page file has a pinned Wikisource revision ID recorded
  in `ws1662_provenance.json`, with per-file SHA-256 hashes.
- **Rights:** Public domain. First published 1662; the 1892 reprint is long out
  of copyright worldwide.

### BCP 1928
- **Source:** Justus Anglican transcription
  (http://justus.anglican.org/resources/bcp/1928/MP.htm and EP.htm),
  retrieved via Internet Archive Wayback Machine snapshots (direct live access
  returned HTTP 403).
- **Correction authority:** Every Justus transcription defect was corrected
  against the Internet Archive 1928 Standard Book scan OCR
  (`isbn_9781537520742_djvu.txt`, a scan of the book "printed for the Commission
  in 1928 and certified as conforming to the Standard Book accepted in
  October 1928"). No correction was made silently; the full list is below.
- **Rights:** Public domain in the US. First published 1928; the 95-year
  copyright term expired 2024-01-01.

## Explicit corrections

### 1928 (Justus transcription -> verified reading)
1. `acknOwledge` -> `acknowledge`
2. `Advocate arid Mediator` -> `Advocate and Mediator`
3. `according to. their` -> `according to their`
4. `hearts may he unfeignedly` -> `hearts may be unfeignedly`
5. `tile light of his countenance` -> `the light of his countenance`
6. `third day lie rose` -> `third day he rose`
7. `was .crucified` -> `was crucified`

### 1662 (scan-adjudicated transcription decisions)
- Royal Family prayer blanks (page 70, manuscript gaps in the 1662 source):
  represented as `[...]` in a `gap` row. The King's name itself ("Charles")
  is present in the source and retained inline. No names were filled from
  later editions.
- Apparent original print anomalies preserved as in the source transcription
  (e.g. "hls eternall ioy", "throug"), not normalized.

## Rejected sources
- `thestrategicdisciple/book-of-common-prayer-concordentary`: repository
  curation/schema (c) 2026 All Rights Reserved; office frontmatter CC BY-NC-SA 4.0;
  Wohlers terms impose redistribution conditions. Comparison only, never ingested.
- 1979 ECUSA BCP: copyrighted, outside scope.
- Modernized reenactments, current-use documents, commercial editions: rejected.
- Concordentary corrections were never imported into staged text.

## Verification
- `PRAGMA integrity_check`: ok.
- Unique index `(source_id, office, seq)`: enforced, no violations.
- HTML tag leak check: 0 rows.
- HTML entity leak check (`&nbsp;`, `&amp;`, `&lt;`, `&gt;`, `&quot;`): 0 rows.
- Wikitext remnant check (`{{`, `[[`): 0 rows.
- Controlled vocabulary: all `section` values are within the 15-value list.
- **Seeded spot checks:** seed `20260920`, 10 per edition (5 Morning Prayer +
  5 Evening Prayer each), independently re-read from raw sources and
  exact-compared on section, label, kind, speaker, and text. **20 passed,
  0 failed.**

## Unresolved issues
1. **Page 57 scope:** Page 57 contains the common introductory rubrics ("The Order
   for Morning and Evening Prayer daily to be said..."). It is currently staged
   at the head of Morning Prayer (seq 1-3). Whether these belong in fixed-office
   scope or should be split out needs a decision.
2. **1662 rubric vs text classification:** heuristic; a small number of
   instructional sentences are staged as `text` rather than `rubric`
   (e.g. "Let vs pray.", "Christ haue mercy vpon vs."). Content is exact;
   only the `kind` tag is debatable.
3. **1928 Wayback snapshot timestamps:** exact snapshot datetimes were not
   recorded at retrieval; only the retrieval date (2026-09-20) and file hashes
   are on record.

## Gaps (follow-up work, explicitly excluded from this stage)
1. **The 30-day Psalter:** not staged. The Psalter is a separate large text
   requiring its own sourcing and verification pass.
2. **Lectionary tables:** not staged. The calendar/lectionary tables are
   tabular data, not office fixed text, and need a separate schema.

## Reproducibility
Run `python3 ~/workspace/scripture-desk/scripts/ingest_v2_liturgy.py`.
Stdlib only. Deletes and rebuilds `staging/liturgy.db` deterministically.
No `data/study.db` was created.
