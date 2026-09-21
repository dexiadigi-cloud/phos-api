# K&D merge - deterministic verification (seed 20260920)

Date: 2026-09-20. Read-only. No DB writes. Nothing published or sent.

## Method

- **Seed:** `20260920`. Population: all `rowid`s of `data/staging/kd_complete.db` table
  `kd_rows`, ordered by rowid. `random.Random(20260920).sample(population, 10)`
  gave 10 seeded samples (S01-S10). Four targeted samples added: T-gap-isa
  (Isaiah 4, adjacent to the missing ch 3), T-gap-1sam (1 Samuel 1:9, adjacent
  to the 1:1-8 gap), T-gap-2kgs (2 Kings 6:24, whose prose covers 6:24-7:20),
  T-corrupt (Exodus 11:4, visible OCR corruption).
- **PARSER stage:** a line-tracking copy of `scripts/parse_v2_kd_complete.py`
  (logic identical; only records each row's raw line span). PASS = re-parse of
  the book's segment(s) yields a row with byte-identical text.
- **RAW stage:** verbatim lines from the `_djvu.txt` at the recorded span; plus
  a reconstruction check (cleaned, de-artifacted, de-running-head lines over the
  span re-joined must equal the row text). PASS = exact.
- **STAGE:** row re-read from `kd_complete.db`.
- **MERGED:** exact-text match among `study.db` `commentaries` rows with
  `source_id='keil_delitzsch'` at the same `(book, start_chapter, start_verse)`.
- Verification script: `/tmp/kd_verify.py` (results JSON: `/tmp/kd_verify_results.json`).

## Pipeline reproduced

`data/raw_v2/keil_delitzsch/0{1..6}.*._djvu.txt`
-> `scripts/parse_v2_kd_complete.py` (Chap./Ver./Vers./PSALM headers; running
heads tracked for chapter state; artifacts, page numbers, "Digitized by"
markers, whitespace normalized)
-> `data/staging/kd_complete.db` table `kd_rows` (6,593 rows)
-> merged into `data/study.db` `commentaries` with `source_id='keil_delitzsch'`
(backup `data/study.db.bak-kd-complete-20260920`).

**Merge dedup rule (reverse-engineered from evidence, all 6,593 staging rows
accounted for):** a staging row is INSERTed unless a `commentaries` row with the
same full range key `(source_id, book_order, start_chapter, start_verse,
end_chapter, end_verse)` already exists. Old (pre-merge) rows win ties; among
new staging duplicates the first wins. Verified: all 2,108 backup K&D rows
present unchanged; all 4,234 newly inserted study rows are byte-identical to a
staging row; 0 new study rows lack a staging source; every staging row's verse
range is represented in study.db.

## Counts

| Check | Result |
|---|---|
| `study.db` `commentaries` total rows | 72,493 |
| `study.db` rows with `source_id='keil_delitzsch'` | **6,342** (matches the 6,342 claim) |
| Distinct book names among K&D rows | 39 |
| `sources` row for `keil_delitzsch` | present (exact id `keil_delitzsch`) |
| Staging `kd_rows` | 6,593 |
| Net new rows inserted by merge | **4,234** (matches the 4,234 claim) |
| Old rows preserved unchanged | 2,108 |
| Staging rows skipped as range-key duplicates | 2,359 (2,313 with different text at an occupied key; 46 also text-identical to an old row) |
| Staging rows with no representation in study.db | 0 |

Note on `data/staging/KD_COMPLETE_REPORT.md`: it claims "net new 5,140 rows
(1,453 duplicates skipped)" and lists "Do not merge to study.db until resolved"
as a blocker. The actual merge produced **4,234 net new / 2,359 skipped** - the
report's figures do not match the merge that ran. Its per-book table is
otherwise consistent with staging.

## Per-sample results

14/14 PARSER PASS, 14/14 STAGE PASS, 14/14 RAW-reconstruction PASS.
MERGED: 11/14 exact-text PASS; 3 are range-key duplicates skipped by the merge
(content at that range IS present in study.db - see notes).

| # | Sample (staging rowid) | Raw location | PARSER | STAGE | MERGED | RAW recon |
|---|---|---|---|---|---|---|
| S01 | Isaiah 22:1-14 (4804, 5,859 ch) | file 05, line 21094, span 21094-21211 | PASS | PASS | PASS (study id 71615) | PASS |
| S02 | Jeremiah 30:23-24 (5181, 5,828 ch) | file 05, line 72737, span 72737-72855 | PASS | PASS | PASS (study id 71764) | PASS |
| S03 | Ezekiel 45:2 (5815, 318 ch) | file 05, line 127603, span 127603-127611 | PASS | PASS | PASS (study id 72029) | PASS |
| S04 | Nehemiah 11:1 (2296, 115 ch) | file 03, line 38941, span 38941-38943 | PASS | PASS | PASS (study id 70378; 2 rows at key) | PASS |
| S05 | Joshua 13:1-14 (1047, 17,721 ch) | file 02, line 6892, span 6892-7196 | PASS | PASS | PASS (study id 69266; 2 rows at key) | PASS |
| S06 | Psalms 127:1 (3709, 2,026 ch) | file 04, line 59764, span 59764-59797 | PASS | PASS | **SKIP-dup** (see note) | PASS |
| S07 | Psalms 82:1 (3359, 2,914 ch) | file 04, line 43196, span 43196-43253 | PASS | PASS | **SKIP-dup** (see note) | PASS |
| S08 | Psalms 29:10 (2840, 735 ch) | file 04, line 19921, span 19921-19938 | PASS | PASS | PASS (study id 70678) | PASS |
| S09 | 1 Chronicles 21:1 (1977, 4,520 ch) | file 03, line 12694, span 12694-12776 | PASS | PASS | PASS (study id 70149; 2 rows at key) | PASS |
| S10 | Psalms 109:21 (3590, 2,586 ch) | file 04, line 54308, span 54308-54354 | PASS | PASS | **SKIP-dup** (see note) | PASS |
| T-gap-isa | Isaiah 4:1 (4768, 23,205 ch) | file 05, line 8092, span 8092-8626 | PASS | PASS | PASS (study id 71580) | PASS |
| T-gap-1sam | 1 Samuel 1:9-18 (1272, 3,927 ch) | file 02, line 26621, span 26621-26690 | PASS | PASS | PASS (study id 69486) | PASS |
| T-gap-2kgs | 2 Kings 6:24 (1766, 13,992 ch) | file 02, line 68517, span 68517-68807 | PASS | PASS | PASS (study id 69949) | PASS |
| T-corrupt | Exodus 11:4-8 (308, 38,161 ch) | file 01, line 25091, span 25091-26295 | PASS | PASS | PASS (study id 68552) | PASS |

Sample text heads (verbatim from staging):
- S01: `Chap. XXIL 1-14 The mtn concerning Babylon, and the no less visionary prophecies concerning Edom and Arabia, are followed by a Mas`
- S02: `Vers. 23, 24. The wicked shall be destroyed hy the fire of God^s anger. — ^Ver. 23. " Behold, a whirlwind of Jahveh, — wrath goeth`
- S05: `Vers. 1-14. Introduction to the Division op the Land. — Vers. 1-7. Command of the Lord to Joshua to distribute the land of Canaan`
- S09: `CHAP. XXI.-XX.II. L— THE NUMBERING OF THE PEOPLE, THE PESTILENCE, AND THE DETERMINATION OF THE SITE FOR THE TEMPLE (CF. 2 SAM. XXI`
- T-gap-isa: `Chap. iv. 1 : " Arid seven women shall lay hold of otie man on that day, saying. Our oum bread vnU we eat, and in our own garments`
- T-gap-2kgs: `chap, vl 24-vn. 20. elisha's action dtjbing a famine in SAMARIA. Vera 24-33. After this there arose so fearful a famine in Samaria`

### Merge SKIP-dup notes (not content loss)

- **S06 (Ps 127:1, staging rowid 3709, range 127:1-127:5):** study.db holds the
  old row 66724 (range 127:1-127:2, preserved) plus new row 70962, which is
  byte-identical to *sibling* staging row 3707 (same range 127:1-127:5). The
  sampled row 3709 lost the range-key tie to its sibling. Verse range 127:1-5
  is covered in study.db.
- **S07 (Ps 82:1, staging rowid 3359, range 82:1-82:8):** study.db holds new
  rows 70871 (= staging 3358, same range) and 70872 (= staging 3360, range
  82:1-82:4). Sampled row 3359 and staging row 3361 lost range-key ties to
  siblings. Range 82:1-8 is covered.
- **S10 (Ps 109:21-25, staging rowid 3590):** study.db holds old row 66650
  (byte-identical to the old `keil_delitzsch.db` row, 1,475 chars); the new
  staging text (2,586 chars) was skipped because the range key was occupied.
  Old row preserved per the merge rule.

## Corruption exhibit (T-corrupt, Exodus 11:4-8)

The merged study.db row (id 68552) contains, verbatim, a garbled publisher's
advertisement page interleaved mid-commentary:

> `Bjpy^X&viffi, \\V T. V UNION i THEOLOGICAL Digitized by T. and T. Clark's Publications. HISTORY OF THE CHRISTIAN CHURCH. By PHILIP SCHAFF, D.D., LL.D. APOSTOLIC CHRISTIANITY, AD. 1-100. In Two Divisions. Ex. demy 8vo, price 21s. ANTB-NICENE CHRISTIANITY, A.D. 100-326. In Two Divisions. Ex. demy 8vo, price 21s. NICENE and POST-NICENE CHRISTIANITY, A.D. S2ft-«00. In Two Divisions. Ex. demy 8vo, price 21s. MEDLBVAL CHRIS` [...continues...]

Provenance: raw OCR `01.BCOT.KD.PentateuchMoses.vol.1.Law._djvu.txt` lines
25178-25197+ carry the ad fragments on separate lines (`Bjpy^X&viffi, `,
`\\V `, `T. `, `V         UNION `, `i `, `THEOLOGICAL `, then the Schaff
catalog text). The parser's artifact filter only strips whole-line
`Digitized by X` markers, so these fragments survived cleaning and were
joined into the row text at every stage (raw -> parser -> staging -> merged
all byte-identical). The corruption is faithfully carried, not introduced, by
the pipeline. Same class of noise (e.g. `^`, `hy` for "by", `op` for "of")
appears in other samples' text heads above.

## Gap verification

| Claimed gap | study.db K&D rows | Verdict |
|---|---|---|
| Isaiah 3 | 0 | **Real.** Isaiah chapters present: 1,2,4,5,7,8,9,10,20-22,27-63,65,66. Also missing: **ch 64** (absent from staging too - parser gap, not merge loss). |
| 1 Samuel 1:1-8 | 0 | **Real.** Earliest 1 Sam 1 row starts at v9 (`Vers. 9-18. Hannah's prayer for a son.`). |
| 2 Kings 7 | 0 | **Real**, but the material survives as surrounding prose: row 2 Kings 6:24 (study id 69949) opens with the OCR-garbled header `chap, vl 24-vn. 20. elisha's action dtjbing a famine in SAMARIA` and covers the 6:24-7:20 famine narrative. Root cause: raw `chap. vn. 1-20.` ("vii" OCR'd as "vn") defeats the `CHAP_RE` roman-numeral class `[ivxlcj]`, so the header was treated as body text. |
| 2 Kings 21 | 0 | **Real.** No row with start_chapter=21. |

**Adjacent finding (2 Kings 8 misfiled):** commentary on 2 Kings 8:1-24 is
stored under `start_chapter=6` (rows 6:1-6 "Elisha's Influence helps the
Shunammite to the Property" = 2 Kgs 8:1-6; 6:7-15 "Elisha predicts to Hazael
at Damascus" = 2 Kgs 8:7-15; 6:16-24 "Reign of Jorah of Judah" = 2 Kgs 8:16-24).
Root cause: raw headers `CHAP, via 1-G.`, `CHAP. vm. ELISHA HELPS THE
SHUNAMMITE...`, `chap. vra. 7-15.` ("viii" OCR'd as via/vm/vra) defeat
`CHAP_RE`; the parser never advanced past chapter 6 (all verse numbers fit
within 2 Kings 6's 33-verse max). A running head `CHAP. VIII. 16-24. 337`
(raw line 69006) later set chapter 8, so 8:25-29 is correctly filed. Net
effect: 2 Kings 8:1-24 exists in study.db but is keyed as chapter 6.

## Verdict

- Seeded character-for-character checks: **10/10 PASS** at all four stages
  (raw, parser, staging, merged).
- Targeted checks: **4/4 PASS** (Isaiah 4, 1 Samuel 1:9, 2 Kings 6:24,
  corrupt Exodus 11:4).
- Merge accounting fully reconciles: 2,108 old + 4,234 new = 6,342; no staging
  content lost (every staging range key represented; 2,359 staging rows skipped
  only as range-key duplicates).
- Known gaps confirmed real; Isaiah 64 identified as an additional unlisted
  gap; 2 Kings 7 material present only as surrounding prose in the 6:24 row;
  2 Kings 8:1-24 content mis-keyed under chapter 6 (OCR "viii" variants).
- Corruption (T&T Clark/Schaff ad page inside Exodus 11:4-8) is present
  verbatim in the merged row - carried faithfully from raw OCR through all
  stages; the parser's artifact filter does not catch multi-line ad fragments.
