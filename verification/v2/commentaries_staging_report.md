# V2 Commentaries Staging Report

Date: 2026-09-20. Revised after invalidation of the provisional database.
Staging only. No application code was changed. `data/study.db` was never
created (verified absent). `data/scripture.db` was opened read-only via
`api/db.py` / `api/parser.py` for reference validation; it was not written to.
No pre-run hash or timestamp baseline was captured for `scripture.db`;
its mtime (Sep 20 15:36) predates this staging work, and no write operations
were performed against it.

## Status: BLOCKED on schema

No valid staging database exists. The earlier `staging/commentaries.db`
(14,824 rows) was built with an invented schema, not a recovered
specification, and has been quarantined as
`staging/INVALID_PROVISIONAL_commentaries.db`. It must not be used.

A full search for the required exact staging schema and index definitions
found nothing: PLAN.md names a future `commentary` table but gives no schema;
BUILD_LOG.md, `api/`, the goal workspace
(`goals/scripture-desk-connector/`, including `briefs/`, `references/`,
`agent_notes/`), the daily memory log, and a full-workspace grep contain no
commentary table definition. The only schema ever written down is the
invented one. No database may be created until the exact required schema
and indexes are supplied.

## Raw sources preserved (verified)

Retrieval date for all sources: 2026-09-20.

**Matthew Henry, Complete Commentary.** 65 HelloAO API files (1,166
chapters; metadata SHA-256
`ad2850450a1e5c0546c275f4bd09b9325ae47424d83311120ca7ced5724c4bc8`) plus
CCEL gap-fill: `mhc2_ccel.txt` (7,814,959 bytes, SHA-256
`b53ca73cf69947ab4f815a54998811167d412253b4595340a057d5b87766acb7`) and
21 CCEL HTML pages under `data/raw_v2/matthew_henry/ccel_gap_html/`
(each with SHA-256 in `MANIFEST.json`). Parsed: `CCEL_GAPS.json`
(23 chapters: SNG 1-8, JON 2-4, MAT 19-28, 2SA 23-24).
Independent re-extraction from the saved HTML bytes matches
`CCEL_GAPS.json` exactly for all 21 HTML chapters (intro text, section
count, titles, text heads). 2SA 23/24 line boundaries verified against
`mhc2_ccel.txt` (CHAP. XXIII at line 48305, CHAP. XXIV at 48793,
1 Kings begins at 49348). Known cleanup defect: the 2SA sections retain
TXT page-footers (`___...___` separators, repeated `S E C O N D  S A M U E L`
title lines); must be stripped on re-parse.

**JFB, Commentary Critical and Explanatory (1871).** CCEL
`jfb_ccel_1871.txt` (22,558,402 bytes, SHA-256
`de2727aab8a63273a5a0826e1e17ac9270c7bf27976f3317e9be9a7542342a33`;
Rights: Public Domain; CCEL Subjects: All; Bible; Proofed).
Parsed: `CCEL_JFB.json` (66 books, 1,189 chapters, 2,026 sections after
the 2026-09-20 parser fixes described below).

**Barnes, New Testament Notes (NT only).** CCEL `barnes_ccel_nt.txt`
(23,042,791 bytes, SHA-256
`ad54acfce1c2bd3b2a981d550a07928449b503a3014371e327b364a81ed90a38`;
Rights: Public Domain; Print Basis 1949 Baker reprint).
Parsed: `CCEL_BARNES_NT.json` (27 books, 260 chapters, 7,334 verses).

## Parser fixes applied 2026-09-20

**JFB (`scripts/parse_v2_jfb_ccel.py`).** Four defect classes found by
auditing the parse against the raw 1871 text, all fixed and the JSON
regenerated (previous JSON kept at `/tmp/CCEL_JFB_before_fix.json`):

1. 74 false-positive section headers: wrapped cross-reference lines
   (e.g. `Isa 7:4, 15, 22.` inside Isaiah 8's intro paragraph,
   `Eze 48:8-13.`, `Mr 6:50.)`) matched the header regex. All 74 verified
   as cross-references, none genuine. Now rejected when the header's
   explicit chapter differs from the enclosing chapter. This also fixed
   Mark 14, where the false positive `Joh 13:21-30.` had absorbed the real
   header `Mr 14:27-31.` into its title and misranged the section as
   (21,30); it is now (27,31).
2. 3 English-word false positives (`become 31,583.`, `of 10,777.` in
   Ezra 2; `and 3:8.` in Jonah 2). Headers now require the abbreviation to
   resolve via `parser.resolve_book()` plus manual aliases
   (1Jo/2Jo/3Jo, Joe, Lu, Mr, So).
3. 12 cross-chapter headers (`Isa 8:1-9:7.`, `Ac 13:1-14:28.`, etc.)
   previously unparseable; now stored under the start chapter with the
   original ref kept in a `ref` field.
4. Discontinuous references previously merged by min-max
   (`Mr 4:3,14` became 3-14; `Lu 23:32-38,44-46` became 32-46); now split
   into contiguous groups sharing the body text.
5. Title capture changed from `\s*` to `[ \t]*`: 63 untitled sections
   had swallowed their first body line as the title (e.g. Job 24:1-25
   titled `1. Why is it that...`). Zero verse-like titles remain.

Reconciliation: 2,088 sections before, 2,026 after
(-74 false positives, -3 English words, +10 cross-chapter, +2+2 splits,
+1 corrected range). Total text preserved; the small char increase is the
shared bodies of the 2 split sections plus title lines relocated into
bodies.

**Barnes checker (`scripts/ingest_v2_commentaries.py`, `check_zero_hit`).**
The USFM-marker heuristic fired only on double-backslash sequences, which
are CCEL transcription artifacts, never real USFM (real USFM uses single
backslash). It caused Luke 6:40 to be silently dropped: the CCEL source
contains `"that is perfect" \\or shall be perfected` (two literal
backslashes, line 40595 of the raw TXT), which the checker misread as a
USFM marker. The earlier report's claim that the row was "retained" was
wrong; the row was absent from the DB. The heuristic now ignores
backslash pairs and still flags genuine single-backslash markers;
verified: artifact passes, `\v 40` flagged, HTML flagged, clean text passes.
The verse text itself is source-faithful and unchanged.

**Provenance fixes.** Both parsers previously read `/tmp/jfb.txt` and
`/tmp/mhc2.txt` (ephemeral, since deleted); they now read the preserved
files under `data/raw_v2/`.

## Rights basis and rejected editions

**Matthew Henry, Complete Commentary on the Whole Bible** (original
1706-1721, author d. 1714). Public domain. Transcriptions: HelloAO
(`matthew-henry`, CC0) for 1,166 chapters; CCEL (Print Basis 1706-1721,
"Public domain. May be copied and distributed freely") for 23 gap
chapters. REJECTED: CrossWire `MHCC` (Concise, not Complete); Razzula
GitHub repo (generator scrapes BibleGateway, stores HTML).

**JFB, Commentary Critical and Explanatory on the Whole Bible**
(Print Basis 1871; authors d. 1870-1910). Public domain. Transcription:
CCEL 1871 Proofed text. REJECTED: HelloAO JFB (systematic mapping
defects: Psalm intros shifted by chapter, Psalms 100-144 largely empty,
Psalm 119 zero entries, Genesis 1:1 material in intro).

**Barnes.** Only *Barnes' New Testament Notes* (27 books) is available as
a faithful PD transcription (CCEL, Public Domain). The requested full
"Barnes' Notes on the Bible" (66 books) was NOT found: Sacred Texts is
Cloudflare-blocked (Wayback served mislabeled Keil and Delitzsch content);
CrossWire Barnes is NT-only. Staged source id must remain `barnes_nt`
unless a full-Bible transcription is located. Barnes OT (39 books)
is unstaged.

**Gill, Exposition of the Entire Bible.** REJECTED, not staged. HelloAO
strips Hebrew/Greek words and mislabels at least one verse (1 Tim 5:13
content under 5:12). CCEL has only the Song of Solomon exposition;
Internet Archive copies are raw OCR; BibleHub is excluded by task
constraints.

## QA performed (against raw sources, not the invalid DB)

- Reference validation: all parsed (book, chapter) pairs resolve via
  `parser.resolve_book()` plus the documented manual aliases; chapters
  and verse ranges checked against `db.get_bounds('KJV')` (read-only).
- Zero-hit scans: no HTML tags or entities remain in parsed output.
- JFB: 72+3 false-positive headers removed (each verified against raw
  text); 10 cross-chapter headers and 2 discontinuous splits verified
  against raw header lines; added/removed section reconciliation done
  (see Parser fixes).
- MH gaps: 21/21 HTML chapters independently re-extracted from saved
  raw bytes match the parsed JSON.
- Barnes: 7,334 verses parsed; the single `\\` artifact (Luke 6:40)
  confirmed present in the raw CCEL text.
- `PRAGMA integrity_check` on the quarantined provisional DB: `ok`
  (integrity of an invalid-schema artifact only).

NOT yet done (blocked on schema): seeded independent raw-to-DB spot
checks (the earlier 30/30 read derived JSONs, not raw bytes; those pairs
are superseded, moved to
`verification/v2/raw/commentaries_SUPERSEDED_20260920/`), a saved
skipped/unresolved-records log, MH HelloAO-vs-CCEL passage comparison,
and historical-edition comparison for JFB/Barnes.

## Open issues and decisions needed

1. **Exact staging schema and index definitions are missing.** Nothing
   in the project docs defines them. Supply them before any database is
   created.
2. **Barnes full-Bible source not found.** Accept `barnes_nt` as a
   partial source, or keep `barnes` rejected pending a full transcription.
3. **Gill rejected.** No faithful PD transcription located.
4. **MH mixed provenance.** HelloAO (CC0, edition unpinned) + CCEL
   (Proofed). Overlapping passages not yet diffed.
5. **Historical-edition comparison** for JFB and Barnes not done.
6. **2SA TXT page-footers** need stripping on re-parse.
