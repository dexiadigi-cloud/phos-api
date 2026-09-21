# Post-BBE-removal corpus verification

Date: 2026-09-21. Commit: `3d728b5` (local; not yet pushed at time of writing).
Reason: BBE is public domain in the United States only; it was removed from the
served corpus. AKJV was kept after the rights review.

## Corpus state (data/scripture.db)

- 17 distinct translations, 490,335 verse rows.
- BBE rows: 0.
- Per-translation row counts:

| Code | Rows |
|------|------|
| AKJV | 31,102 |
| ALMEIDA | 31,102 |
| ASV | 31,086 |
| BSB | 31,086 |
| DARBY | 31,099 |
| DRB | 35,811 |
| GENEVA | 31,090 |
| KJV | 31,102 |
| LSG1910 | 31,170 |
| LUTHER1912 | 31,102 |
| LXX2012 | 28,351 |
| OEB | 13,894 |
| RVA1909 | 31,084 |
| WEB | 31,095 |
| WEBSTER | 31,102 |
| WEYMOUTH | 7,957 |
| YLT | 31,102 |

## Artifact integrity

- `sha256(data/scripture.db)` = `7b462b2b181ac7b38a68670fdfe958931b69eabfe1d4ae89effcb45fb0c8f929`
- Concatenated `data/dist/scripture.db.part-*` reassembles to the same
  SHA-256, confirming the split chunks match the database byte for byte.
- FTS rebuilt after row deletion.

## Docs and registry alignment

- `api/translations.py`: BBE entry removed.
- `api/app.py`, `api/openapi.json`: BBE references removed; the
  `/v1/translations` description now says "seventeen translations".
- `docs/public/api-reference.md`, `coverage-and-availability.md`,
  `sources-and-attribution.md`, `terms-of-service.md`: BBE entries removed.
- README and deploy-guide corrected from 18 to 17 translations.

## Tests

- Full API suite: 222 passed, 3 warnings (run 2026-09-21 after removal).
- Translation-specific tests updated to expect the 17-translation set.

## Note on the live service

The live deployment at `https://phos-api-xpok.onrender.com/` still serves the
pre-removal corpus (18 translations, 521,437 verses) until the bundled push is
deployed and Render rebuilds. Post-deploy, verify `/health` reports 17
translations and 490,335 verses, and that `?translations=BBE` returns a 400.
