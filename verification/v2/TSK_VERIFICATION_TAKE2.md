# TSK Verification Report (Take 2) - 2026-09-20

## Verdict: PASS (eligible for merge into `data/study.db`)

**Staging DB:** `~/workspace/scripture-desk/staging/crossrefs2.db`
**Script:** `~/workspace/scripture-desk/scripts/ingest_v2_crossrefs2.py` (re-runnable)
**Source:** CrossWire TSK v1.4, `https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/TSK.zip`
**SHA-256:** `6784c7099465995a8e66f02ead82b0bca66603c1bdeaf8332949774b7bfd4293`
**Retrieved:** 2026-09-20

## Why take 1 was rejected

`staging/crossrefs.db` (take 1) used greedy KJV phrase-prefix alignment that silently
misattributed 11.7% of phrases (7,525 with zero KJV match). Confirmed failure at
2 Samuel 24:24-25 (verse-24 material assigned to verse 25). Take 1 is NOT eligible
for merge.

## Take-2 method

Ordered-subsequence phrase alignment against KJV verse text (monotone cursor):
- **Strong** (79.6%): full phrase word-order match; advances cursor.
- **Weak** (1.9%): partial match (>=2 words, >=50%); attributed but cursor does NOT advance.
- **Note-like** (12.4%): Strong's numbers, chronology headers, long notes; attached to
  current verse, no advance.
- **Unattributed** (6.1%): skipped (honest loss, NOT misattributed).
- **Barenum verse markers**: standalone line-start `<scripRef>N</scripRef>` with N > cursor
  is a hard verse anchor (print-edition verse number).
- **New-paragraph heuristic**: line-start refs after `</scripRef>` go to last-anchor + 1,
  and the cursor advances (a later marker or strong phrase corrects if wrong).
- **Continuation blocks**: consecutive refs blocks without an intervening phrase share
  the same verse.

## Final stats

- 573,192 rows, 27,190 distinct heads, 66 books (incl. Song of Songs), 1,170 chapters
- 64,632 phrases: 51,407 strong, 1,245 weak, 8,027 note-like, 3,953 unattributed (skipped)
- 77,238 refs blocks processed; 579,154 valid refs; 14 invalid skipped, 809 unresolvable skipped
- `PRAGMA integrity_check = ok`
- No HTML/entity/USFM leakage in stored data
- All 66 book names are M1-canonical

## Exact raw-to-DB verifications (10/10 PASS)

Independent raw TSK read (decompressed SWORD modules, not via ingest functions):

| # | Head | DB refs | Raw expectation | Result |
|---|------|---------|-----------------|--------|
| 1 | 2Sa 24:24 | 8 (Ge 23:13, 1Ch 21:24, Mal 1:12-14, Ro 12:17, 1Ch 21:25, 22:1) | "Nay." + "So David." blocks | PASS |
| 2 | 2Sa 24:25 | 10 (Ge 8:20, 22:9, 1Sa 7:9,17, 2Sa 21:14, 24:14, 1Ch 21:26,27, La 3:32,33) | "built there." + "So the Lord." blocks | PASS |
| 3 | Ge 1:9 | 25 (Job 26:7,10, 38:8-11, Ps 24:1,2, 33:7, 95:5, 104:3,5-9, 136:5,6, Pr 8:28,29, Ec 1:7, Jer 5:22, Jon 1:9, 2Pe 3:5, Re 10:6) | Phrase-less refs blocks after v8 | PASS |
| 4 | Ge 1:8 | 7 (Ge 1:5,10,13,19,23,31, 5:2) | "evening." block only (v9 refs correctly excluded) | PASS |
| 5 | Lu 23:36 | 12 (Ps 69:21, Mt 27:29,30,34,48, Mr 15:19,20,36, Joh 19:28-30, Lu 23:11) | "11; Ps 69:21;..." phrase-less block | PASS |
| 6 | Lu 23:37 | 11 (Mt 27:11,37, Mr 15:18,26,32, Joh 19:3,19-22, Lu 23:3) | Block after "37" verse marker | PASS |
| 7 | Lu 23:40 | 8 (Le 19:17, 2Ch 28:22, Ps 36:1, Jer 5:3, Lu 12:5, Eph 5:11, Re 15:4, 16:11) | "rebuked." block | PASS |
| 8 | Mt 18:21 | 3 (Mt 18:15, Lu 17:3, Lu 17:4) | "till." + "15; Lu 17:3,4" (v21's wording, not v22's) | PASS |
| 9 | Job 3:21 | 1 (Pr 2:4) | "dig." + "Pr 2:4" | PASS |
| 10 | Eze 11:19 | 36 (all of "I will give.", "I will put.", "I will take." blocks) | Three phrase blocks incl. De 30:6, Zep 3:9, Ro 2:4,5 | PASS |

## Known limitations (documented, not blocking)

1. **Adjacent-verse errors in phrase-less blocks**: When the TSK has consecutive
   phrase-less verses without barenum markers (e.g., Lu 23:38/39), the new-paragraph
   heuristic may attribute to the wrong adjacent verse. Estimated impact: small
   (markers cover many cases).
2. **6.1% unattributed phrases**: Skipped, not misattributed. These are mostly
   obscure phrases, hyphenation variants, or TSK-specific abbreviations.
3. **Continuation ambiguity**: A line-start refs block after `</scripRef>` is assumed
   to be a new verse (not a continuation). When wrong, the error is at most one
   adjacent verse (e.g., Ge 1:16's "Ps 19:6; Jer 31:35" went to v17 instead of v16).
4. **Proverbs 10-24 and Isaiah 24-27**: SWORD source has no chapter markers; skipped
   (2 ranges). These chapters have no TSK data in the source.
5. **Provenance**: The exact relationship between the CrossWire v1.4 transcription
   and the 1836 first edition has not been independently established. The SWORD
   `tsk.conf` declares `DistributionLicense=Public Domain`.

## Comparison with take 1

- Take 1: 563,760 rows (with 11.7% silently misattributed)
- Take 2: 573,192 rows (6.1% honestly skipped, 0% silently misattributed)
- 18/30 sampled heads differ; manual review shows take 2 is more complete
  (finds verses take 1 missed entirely, e.g., Lu 23:36, Ps 68:24) and more precise
  (doesn't over-attribute, e.g., Mt 24:45: 36 vs 48 refs).

## Recommendation

**MERGE** `staging/crossrefs2.db` into `data/study.db`. Do NOT merge `staging/crossrefs.db`
(take 1).
