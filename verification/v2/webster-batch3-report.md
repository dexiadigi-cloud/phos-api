# Webster Bible 1833 ingest report (batch 3) - 2026-09-20

## Provenance verdict: RIGHTS OK

- Source: eBible.org "Noah Webster Bible" (`engwebster`), the exact digital
  edition Jeremiah approved for this batch.
- Edition page: https://ebible.org/engwebster/
- Rights statement page: https://ebible.org/engwebster/copyright.htm
  (retrieved 2026-09-20). The licensing field is quoted verbatim as
  **"Public Domain"**. No copyright holder, no CC license, no additional
  terms; the eBible.org certification badge is displayed on the edition page.
- Underlying work: Noah Webster's 1833 revision of the KJV ("The Holy Bible,
  Containing the Old and New Testaments, in the Common Version, with
  Amendments of the language by Noah Webster, LL.D."), PD by age; the
  digital edition's own declaration agrees.
- Downloaded: https://ebible.org/Scriptures/engwebster_usfm.zip
  (1,419,962 bytes, 2026-09-20). eBible source files dated 12 Dec 2025;
  generated 8 Aug 2026; zip internal file dates 2026-08-08.
- SHA-256 (zip):
  `fb12085e48a2a4ada77d6b12497411c9bd321aae929d58afe74861d450009db8`
- Full provenance + per-file hashes: [data/raw_v2/webster/PROVENANCE.md](sandbox:///workspace/scripture-desk/data/raw_v2/webster/PROVENANCE.md)
  (hashes also in `data/raw_v2/webster/sha256sums.txt`).

## Row counts

- **31,102 rows staged** in `data/staging/webster.db`, table `verses`,
  all `translation='WEBSTER'`.
- **66 books**, canonical names and 0-based `book_order` from the shared
  book table (`scripts/ingest_translations_batch2.py`): Genesis=0 ...
  Revelation=65. Book names match the other translations exactly
  ("1 Chronicles", "Song of Songs", etc.).
- 31,102 matches the KJV-family total (YLT/BBE/AKJV are 31,102 in Phos).
- Duplicate (book, chapter, verse) keys: 0. Empty verse texts: 0.
- Translation code `WEBSTER` verified distinct from existing codes
  (AKJV, ASV, BBE, BSB, DARBY, DRB, GENEVA, KJV, OEB, WEB, YLT).
- `data/scripture.db` and `data/study.db` were NOT touched (per task).

## Deterministic verification (seed 20260920)

Script: `scripts/verify_webster_batch3.py`. Full report:
[data/staging/webster-VERIFY.md](sandbox:///workspace/scripture-desk/data/staging/webster-VERIFY.md).

- Three-way character-for-character comparison per verse key:
  raw USFM `\v` line (cleaned with an independent re-implementation)
  vs parser output vs staging DB text.
- 5 mandatory anchors: Genesis 1:1, John 3:16, Psalms 23:1, Malachi 4:6,
  Revelation 22:21 - all PASS.
- 50 seeded random samples - all PASS.
- **Result: 55/55 passed. ALL PASS.**
- Structural audits in the same run: 31,102 rows / 31,102 distinct keys,
  66 books, book_order matches canonical table, all rows WEBSTER.

## Test fragment

- Path: [api/tests/batch3_frag_webster.py](sandbox:///workspace/scripture-desk/api/tests/batch3_frag_webster.py)
  (fragment only; not collected by pytest until assembled).
- Contents: `WEBSTER_COUNT = 31102` asserted via `db.translation_counts()`;
  3 seeded spot-checks (Jer 10:14, Ezek 13:15, Matt 5:25); 3 anchor checks
  (Gen 1:1, John 3:16 "only-begotten Son", Rev 22:21); all-66-books check
  with book_order spot assertions (Genesis=0, Song of Songs=21,
  Revelation=65).
- Every marker and count in the fragment was validated against the staging
  DB (syntax OK, all markers found).

## Source fidelity notes (kept as-is, not normalized)

- Psalm titles ride on the `\v 1` line in this edition (e.g. Ps 23:1 begins
  "A Psalm of David. The LORD is my shepherd; ..."). Faithful to source.
- Some `\add` closings precede punctuation with a space in the source
  (e.g. Ezek 13:15 `\add mortar\add* ,` -> "mortar ,"). Faithful to source.
- Inline markup in this edition is only `\add ...\add*` (Webster's inserted
  words, kept as plain words, same convention as batch 2 USFX cleaning).

## Proposed log entries (for coordinator; files NOT edited)

### BUILD_LOG.md

```
## 2026-09-20 - Webster Bible 1833 staged (WEBSTER, batch 3)

- Source: eBible engwebster USFM (Public Domain per
  https://ebible.org/engwebster/copyright.htm), zip SHA-256
  fb12085e48a2a4ada77d6b12497411c9bd321aae929d58afe74861d450009db8.
  Provenance: data/raw_v2/webster/PROVENANCE.md.
- Parsed with scripts/ingest_webster_batch3.py to data/staging/webster.db:
  31,102 rows / 66 books, translation='WEBSTER', 0 dupes, canonical
  book_order (Genesis=0..Revelation=65).
- Verification: scripts/verify_webster_batch3.py, seed 20260920, 55/55
  three-way checks passed (raw USFM -> parser -> staging DB);
  data/staging/webster-VERIFY.md.
- Test fragment: api/tests/batch3_frag_webster.py (count + 3 seeded
  spot-checks + anchors + 66-book check); validated against staging.
- Fidelity notes: psalm titles inline on verse 1; source keeps "word ,"
  spacing from \add* closings.
- NOT merged to data/scripture.db (coordinator merges).
```

### PLAN.md

Add under the batch-3 translations section (or as a completed item):

```
- [x] Webster Bible 1833 (WEBSTER): staged 2026-09-20 - 31,102 rows /
  66 books in data/staging/webster.db; provenance PD-verified
  (data/raw_v2/webster/PROVENANCE.md); deterministic verification 55/55
  (data/staging/webster-VERIFY.md); test fragment
  api/tests/batch3_frag_webster.py. Awaiting coordinator merge into
  data/scripture.db.
```

## Files produced

- `data/raw_v2/webster/engwebster_usfm.zip` + 66 extracted `.usfm` files
- `data/raw_v2/webster/sha256sums.txt`
- `data/raw_v2/webster/PROVENANCE.md`
- `scripts/ingest_webster_batch3.py`
- `scripts/verify_webster_batch3.py`
- `data/staging/webster.db` (31,102 rows)
- `data/staging/webster-VERIFY.md`
- `api/tests/batch3_frag_webster.py`
- `verification/v2/webster-batch3-report.md` (this file)

## Ready for merge

Staging DB is complete and verified. The coordinator can merge
`data/staging/webster.db` into `data/scripture.db` (translation='WEBSTER')
and assemble `api/tests/batch3_frag_webster.py` into the pytest suite.
