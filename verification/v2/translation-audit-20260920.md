# Unified translation audit — 2026-09-20 (pre-release requirement)

Run against `data/scripture.db` (`verses` table) vs `api/translations.py`
metadata. All 18 translations verified present with verse counts, book
counts, empty-text check, and rights status.

## Results

| code      | verses | books | empty | rights         | status |
|-----------|-------:|------:|------:|---------------:|--------|
| BSB       | 31,086 | 66 | 0 | public_domain | OK |
| KJV       | 31,102 | 66 | 0 | public_domain | OK |
| WEB       | 31,095 | 66 | 0 | public_domain | OK |
| ASV       | 31,086 | 66 | 0 | public_domain | OK |
| YLT       | 31,102 | 66 | 0 | public_domain | OK |
| DARBY     | 31,099 | 66 | 0 | public_domain | OK |
| DRB       | 35,811 | 73 | 0 | public_domain | OK (73 books: includes deuterocanon) |
| BBE       | 31,102 | 66 | 0 | public_domain | OK |
| GENEVA    | 31,090 | 66 | 0 | public_domain | OK |
| AKJV      | 31,102 | 66 | 0 | public_domain | OK |
| OEB       | 13,894 | 44 | 0 | public_domain | PARTIAL, documented |
| WEBSTER   | 31,102 | 66 | 0 | public_domain | OK |
| WEYMOUTH  |  7,957 | 27 | 0 | public_domain | PARTIAL, documented |
| LXX2012   | 28,351 | 54 | 0 | public_domain | OK (Septuagint canon) |
| LSG1910   | 31,170 | 66 | 0 | public_domain | OK |
| LUTHER1912| 31,102 | 66 | 0 | public_domain | OK |
| ALMEIDA   | 31,102 | 66 | 0 | public_domain | OK |
| RVA1909   | 31,084 | 66 | 0 | public_domain | OK |

Total verse rows: 521,437. Zero empty-text rows across all translations.

## Partial translations (intentional, documented in metadata notes)

- **OEB**: 44 books. The Open English Bible OT was never finished; complete
  NT plus Genesis, Joshua, Ruth, Esther, Psalms, Hosea-Malachi. The
  `notes` field on `GET /v1/translations` discloses this.
- **WEYMOUTH**: 27 books, New Testament only. Disclosed in `notes`.
- **LXX2012**: 54 books, Septuagint canon (no NT; 15 deuterocanonical
  books). Greek Psalm numbering (151 psalms); references do not align 1:1
  with Hebrew-based Bibles. Known source gap: 1 Kings 14:1 has no text in
  the edition. Disclosed in `notes`.

LXX2012 book list verified: full OT + Tobit, Judith, Wisdom, Sirach,
Baruch, 1-2 Maccabees, Epistle of Jeremy, Prayer of Azarias, Susanna,
Bel and the Dragon, 1 Esdras, Prayer of Manasses, 3-4 Maccabees.

## Spot checks

- John 3:16 (BSB/KJV/WEB/ASV): correct distinct translation wordings.
- Psalm 23:1 (LSG1910/LUTHER1912/ALMEIDA/RVA1909): correct non-English text.

## Verdict

All 18 translations are public domain with per-translation rights metadata
preserved per the getBible distribution terms. Partial canons are
disclosed to API consumers via the `notes` field. No blockers found.
Audit requirement satisfied.
