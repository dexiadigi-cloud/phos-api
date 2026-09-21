# K&D targeted defect fix - verification report

Date: 2026-09-20. Scope: Keil & Delitzsch rows in `data/study.db` only.
Script: `scripts/kd_defect_fix.py` (`--dry-run` verified first, then `--apply`).
Backup: `data/study.db.bak-kd-defectfix-20260920` (383,795,200 bytes, taken before any write).
Per-row manifest: `verification/v2/kd-defectfix-manifest.md` (70 entries).

## Results

| Check | Before | After |
|---|---|---|
| K&D live rows | 6,342 | 6,325 |
| Distinct OT books | 39 | 39 |
| Inverted ranges | 16 | 0 |
| Repeated-range extra rows | 37 (36 groups) | 0 |
| Advertisement markers in Exodus 11:4-8 row | present | 0 |
| 2 Kings 6:24-7:20 famine narrative range | 6:24-5:24 (inverted) | 6:24-7:20 |
| DB integrity | ok | ok |
| API suite | 172 passed | 172 passed |

Row math: 6,342 - 32 deleted + 15 recovered = 6,325. Verified by query.

## What was fixed

**Advertisement (id 68552, Exodus 11:4-8).** Text was 38,161 chars; valid
commentary ends at char 4,462 (`go out of his land."`). Everything after was
publisher catalog advertising and Google Book notices. Truncated to 4,462
chars; all four ad markers verified absent from the kept text.

**Sixteen inverted ranges**, each corrected to the range the row's own text
supports (headers and verse discussions read directly):

- 68584 Exodus 15:16-15:5 -> 15:1-15:5 (text ends at v.5)
- 69338 Joshua 24:26-24:13 -> Joshua 23:2-23:13 (text discusses Joshua 23)
- 69885 1 Kings 16:29-16:2 -> 1 Kings 16:29-16:29. The text states its scope
  as the cross-book epoch 1 Kings 16:29 through 2 Kings 10:27, which the
  schema cannot represent in one row. Filed at its anchor verse; the
  limitation is documented here, not hidden.
- 69949 2 Kings 6:24-5:24 -> 6:24-7:20 (famine narrative). Text also
  truncated (13,992 -> 13,764 chars) where the next chapter's section header
  began; the cut lands exactly at the end of the 7:20 discussion.
- 70024 2 Kings 20:12-20:10 -> 20:12-20:19 (header OCR `12-10` of `12-19`,
  confirmed against the clean `12-19` page header in the raw)
- 70387 Nehemiah 12:44-10:44 -> 12:44-13:31 (header `xii.44-xiii.31`)
- 70431 Job 4:17-4:8 -> 4:12-4:21 (Eliphaz vision exposition; distinct from
  the 4:1-4:21 introduction in row 70430)
- 70481 Job 33:13-1:13 -> 33:13-33:14 (header OCR `13-ifc` of `13, 14`)
- 71367 Proverbs 10:5-1:5 -> Proverbs 31:1-31:5 (misfiled ch.31 material)
- 71481 Ecclesiastes 3:10-3:1 -> 3:10-3:11 (head: `Vers. 10, 11`)
- 71652 Isaiah 52:13-51:13 -> 52:12-52:13 (bridge text covering 52:12 and
  introducing 52:13; kept distinct from 71653 below)
- 71653 Isaiah 52:13-50:13 -> 52:13-53:12 (fifth prophecy, full commentary)
- 71659 Isaiah 56:9-50:9 -> 56:9-57:21 (header `lvi.9-lvii.21`)
- 71993 Ezekiel 30:20-30:2 -> 30:20-30:26 (header OCR `30:20-2G`)
- 72457 Zechariah 11:15-11:1 -> 11:15-11:17 (head: `Vers. 15-17`)

Note: 72053 (Daniel, filed 9:2-9:1) is not in this list. Its text is 75%
redundant with the longer, cleaner row 68037 (Daniel 9:24 exposition); it was
deleted as an inferior duplicate scan rather than re-ranged. The ~2,300
unique chars were an OCR variant of the same anointing exposition, not
distinct commentary. This is the one judgment call in the pass that loses
any text, and it is recorded here.

**Thirty-six repeated-range groups (37 extra rows).** Seven rows were
reassigned to their true locations (no text lost):

- 67917, 67923, 67924, 67925, 67927: filed Daniel 3:2/13/14/15/16, actually
  Daniel 4:2/13/14/15/16 (texts say so explicitly)
- 66488: filed Psalms 75:2-4, actually Psalms 76:1 (title + v.1)
- 66492: filed Psalms 75:2-4, actually Psalms 77:2-77:4 (running head
  PSALM LXXVII; no 77:2-4 row existed)

Thirty rows were deleted: true duplicate scans where the kept row is longer
or cleaner, stubs whose text is fully contained in the kept row, and rows
filed under the wrong verse whose content duplicates an existing row at the
right verse (Ezekiel 44:2 row was really 45:2; Isaiah 39:2 row was really
40:2; Jeremiah 14:5 row was really 15:5; Jeremiah 21:5 row was really 22:5;
Proverbs 26:3-5 rows were really 27:3-5). For OCR-variant pairs the cleaner
copy was kept (length alone was not the rule: Ezekiel 25:3 kept the shorter
but cleaner 67648 over 67651).

**Fifteen recovered sections** (parser omissions, all present in the raw
T. & T. Clark OCR; nothing invented):

- 1 Samuel 1:1-1:8 (`Vers. 1-8. Samuel's pedigree`)
- 2 Kings 8:1-8:15 and 8:16-8:24 (section bodies the parser dropped; the
  8:25-29 row already existed, so chapter 8 is now continuous 8:1-29)
- 2 Kings 21:1-21:18 and 21:19-21:26 (reigns of Manasseh and Amon)
- Isaiah 3:1-3:7, 3:8-3:9, 3:10-3:15, 3:16-3:17, 3:18-3:26
- Isaiah 64:1-64:2, 64:4, 64:5, 64:6, 64:9-64:11

## Gaps checked against raw (task requirement)

- Isaiah 3: was a parser miss, now recovered (5 rows).
- Isaiah 57: was never a gap; row 71659 covers 56:9-57:21 once un-inverted.
- Isaiah 64: was a parser miss, now recovered (5 rows).
- 1 Samuel 1:1-8: was a parser miss, now recovered.
- 2 Kings 7: was a misfile, now indexed 6:24-7:20.
- 2 Kings 21: was a parser miss, now recovered (2 rows).
- 2 Kings 8:1-24: unlisted gap found during the work, now recovered.
- Still genuinely absent from the raw parse: Isaiah 6, Isaiah 11-19.
  These remain documented as gaps, not invented.

## Residual notes

- 69885's cross-book epoch (1 Kings 16:29-2 Kings 10:27) cannot be
  represented in the current schema; it is filed at 16:29-16:29 with this
  note. A schema change (e.g. end_book column) would be needed to do better.
- The 1 Samuel chapter-1 introduction tail (raw lines 26220-26229) is a
  mid-sentence fragment cut off by the raw file's start; it was not
  recovered as a row because it has no clean section boundary. Noted, not
  hidden.
- Recovered rows keep the raw's OCR noise (garbled headers like
  `CffAFTEfi m. S, 8.`), consistent with existing rows. No text was
  modernized or corrected beyond whitespace normalization.

## Verification performed

- Pre-apply assertions on all 55 touched rows (id, range, text length,
  text markers): passed on the dry-run copy and again on live before apply.
- Dry-run on a full copy: integrity ok, 0 inverted, 0 dup extras, 39 books,
  ad markers absent, famine range correct.
- Same checks re-run after live apply: all pass.
- API suite: 172 passed, 3 warnings (the K&D count assertion updated
  6342 -> 6325 with a dated comment; no other test touched).
- Manifest of all 70 changes: `verification/v2/kd-defectfix-manifest.md`.

## Addendum: publisher-advertisement cleanup, second pass (2026-09-20)

The first pass had cleaned only the Exodus 11:4 advertisement. Independent
verification found 24 further K&D rows (volume-end sections) still containing
T. & T. Clark advertising catalogs, printer colophons, library stamps, and
Google scan boilerplate swept in from trailing volume matter.

Script: `scripts/kd_ad_cleanup.py` (`--scan`, `--dryrun` on a full copy,
then `--apply`). Backup: `data/study.db.bak-kd-adcleanup-20260920`
(383,819,776 bytes, taken before any second-pass write).

**Method.** Each affected row's commentary-to-trailing-matter transition was
inspected directly and given an explicit, manually verified truncation
boundary. Generic earliest-marker detection was not used, because in most
rows the first detectable marker sits deep inside already-contaminated text
(e.g. 2 Chr 36:22's marker at 2,407 vs true boundary 1,180; Ruth 4:18-20's
at 13,298 vs 3,643).

**Results.** 26 rows truncated, 0 rows deleted:

| Check | Before | After |
|---|---|---|
| K&D live rows | 6,325 | 6,325 |
| DB integrity | ok | ok |
| Catalog-marker sweep (unexpected hits) | 26 rows | 0 |
| API suite | 172 passed | 172 passed, 3 warnings |

Per-row before/after lengths are in the manifest. Notable cases:

- id=68857 (Leviticus 27:30-33): first boundary (13,579) was wrong; it left
  END OF VOLUME II / catalog / Google matter inside the kept text. Caught by
  the post-apply sweep, corrected to 2,645, re-applied, re-verified clean.
- id=66284 (Job 42:17): truncation at 58,849 preserves the genuine T. & T.
  Clark footnote citation at ~41,527 and the INDEX OF TEXTS; only the
  PUBLICATIONS catalog was removed.
- id=69485 (Ruth 4:18-20): commentary ends at "(Brentitu)."; the printer
  colophon ("MURRAT AND GIBB, PRINTERS, EDINBURGH" in garbled OCR) and the
  "Works published by T. & T. Clark" catalog follow.
- id=71578 (Ecclesiastes 12:14): commentary ends at "profound and
  abiding."; the Dorner book advertisements follow.
- Four further rows found only by the post-apply sweep (same defect, missed
  by the original scan): 69202 (Deut 34:9-12), 70049 (2 Kgs 25:22-26),
  72324 (Micah 7:20), 72493 (Mal 4:4-6). All truncated and verified.

**Left intact, by decision:**

- id=71579 (Ecclesiastes 1:1-17, 12,195 chars): the entire row is publisher
  catalog (book blurbs, price lists); no Ecclesiastes commentary exists
  anywhere in it (verified: zero occurrences of Koheleth, Ecclesiastes,
  verse, or Ver.). It is 100% advertisement. It was NOT deleted because the
  assigned constraint requires parent approval for any deletion and the row
  count must stay 6,325. Recommendation: delete it (a proper Ecclesiastes
  1:1 row, id=71460, already exists). Awaiting parent decision.
- id=71524 (Ecclesiastes 8:14): genuine footnote citation to T. and T.
  Clark. Untouched.
- id=70427 (Job 2:4), id=70440 (Job 5:12): genuine footnotes mentioning
  Clark's Foreign Theological Library. Untouched (verified byte-identical
  after apply, along with 71524).

**Verse-0 count.** 151 K&D rows have verse 0 in a range field (chapter
introductions, e.g. Jeremiah 18:0). Counted only; not modified.

**Final catalog-marker sweep** (case-insensitive, all 6,325 K&D rows):
zero unexpected hits. The only matches are id=71579 (pending decision
above) and the three protected genuine-citation rows.

## Addendum 2026-09-20: pure-ad row deleted, scan stamps stripped (parent-approved)

- DELETED id=71579 (Ecclesiastes 1:1-17, 12,195 chars): parent approved
  2026-09-20. Re-verified before deletion: 100% publisher catalog (book
  blurbs, price lists, "Digitized by" stamps), zero Ecclesiastes
  commentary. Proper Ecclesiastes 1:1 row id=71460 (1,172 chars) exists
  separately; no coverage lost. Backup
  data/study.db.bak-kd-delete71579-20260920 taken before the delete.
- STRIPPED 4 inline "Digitized by Google" stamps (parent approved):
  id=68682 (1826->1805 chars), id=69567 (7661->7639), id=70595
  (2004->1957, also removed attached page header "262 PSALM XVIII,
  29-31."), id=71616 (76094->76046, also removed attached header
  fragment "ciiAPTEES xxiv.-xxvn. 419"). Text-only; ranges untouched.
- Post-change: integrity ok, K&D rows 6,324, 39 books. Zero "Digitized
  by Google" occurrences remain in K&D. Catalog-marker sweep still
  clean (only the three protected genuine-citation rows match:
  71524, 70427, 70440).
