# Phos API: Coverage and Availability

Honest statements of what the API contains. Every count below was read
directly from the live databases (`data/scripture.db`, `data/study.db`)
on 2026-09-20. Verse addresses and book numbering follow each source
edition; they do not line up 1:1 across translations.

## Bible translations (data/scripture.db)

18 translations, 521,437 verses total.

| Code | Translation | Edition note | Verses |
|------|-------------|--------------|--------|
| BSB | Berean Standard Bible | v5.2 (publisher USFM release) | 31,086 |
| KJV | King James Version | Text from the named source commit; edition-level 1769 accuracy **not established** | 31,102 |
| WEB | World English Bible | Distribution 3.1 (2012-01-25) | 31,095 |
| ASV | American Standard Version | 1901 | 31,086 |
| YLT | Young's Literal Translation | eBible engylt | 31,102 |
| DARBY | Darby Translation | eBible engDBY | 31,099 |
| DRB | Douay-Rheims Bible (1899 American Edition) | 73 books; Challoner's edition | 35,811 |
| BBE | Bible in Basic English | eBible engBBE | 31,102 |
| GENEVA | Geneva Bible (1599) | eBible enggnv | 31,090 |
| AKJV | American King James Version | 2018 revision | 31,102 |
| OEB | Open English Bible (US spelling) | Unfinished/partial edition | 13,894 |
| WEBSTER | Webster Bible | Noah Webster's 1833 revision of the KJV | 31,102 |
| WEYMOUTH | Weymouth New Testament | 3rd edition (1913); NT only | 7,957 |
| LXX2012 | LXX2012: Septuagint in English 2012 | Brenton 1851 with Johnson's 2012 language update | 28,351 |
| LSG1910 | Louis Segond 1910 | eBible fraLSG (French; first non-English translation) | 31,170 |
| LUTHER1912 | Luther Bible 1912 | eBible deu1912 (German; second non-English translation) | 31,102 |
| ALMEIDA | Almeida Recebida | Biblia Almeida Recebida v1.7 (Portuguese; third non-English translation) | 31,102 |
| RVA1909 | Reina-Valera 1909 | eBible spaRV1909 (Spanish; fourth non-English translation) | 31,084 |

### Translation coverage notes

- **WEYMOUTH is New Testament only** (27 books). It has no Old Testament.
- **OEB is unfinished/partial** (44 books, 13,894 verses). It covers the
  full New Testament but only Genesis, Joshua, Ruth, Esther, Psalms, and
  the twelve Minor Prophets (Hosea-Malachi) from the Old Testament.
- **LXX2012 has 54 books**: the 39 Old Testament books plus 15
  deuterocanonical books (Tobit, Judith, Wisdom, Sirach, Baruch,
  1-2 Maccabees, 1 Esdras, Prayer of Manasses, 3-4 Maccabees, Epistle of
  Jeremy, Prayer of Azarias, Susanna, Bel and the Dragon). It contains no
  New Testament. Versification is LXX, not Hebrew: Psalms follow Greek
  numbering (151 psalms; LXX2012 Psalm 23:1 is Hebrew Psalm 24:1), and some
  verse ranges are merged or numbered differently. Treat its verse
  addresses as translation-scoped.
- **LXX2012 source gap:** the source edition supplies no text for
  1 Kings 14:1 (a placeholder for vv 1-20); the verse is absent from the
  served data (the chapter begins at v 21).
- **LSG1910 is French and follows French versification** (translation-scoped):
  psalm titles are numbered as verse 1 (LSG Psalm 3:1 is the title; LSG
  Psalm 3:9 = KJV Psalm 3:8), Exodus 7:26-29 = KJV 8:1-4, Leviticus
  5:20-26 = KJV 6:1-7, Jonah 2:1 = KJV 1:17, Revelation 12:18 = KJV 13:1,
  Mark 9:51 = KJV 9:50b, and similar offsets. Cross-translation verse
  lookups will not match 1:1 in these passages.
- **LUTHER1912 is German and matches KJV numbering exactly:** 31,102 verse
  keys, no versification deltas. Psalm titles are joined to verse 1 in the
  edition text (e.g. "Ein Psalm Davids. Der HERR ist mein Hirte..." is all
  in Psalms 23:1).
- **ALMEIDA is Portuguese and matches KJV numbering exactly:** 31,102 verse
  keys, no versification deltas.
- **RVA1909 is Spanish and follows Spanish versification** (translation-scoped):
  31,084 text-bearing verses; the source carries 18 empty placeholder verse
  markers (dropped), with the text printed at offset keys. Chapter offsets:
  Numbers 12:16 is printed at 13:1, Numbers 29:40 at 30:1, 1 Samuel 23:29
  at 24:1, Hosea 11:12 at 12:1, Jonah 1:17 at 2:1. Merges: 2 Samuel 20:26
  into 20:25, 2 Chronicles 33:25 into 33:24, Job 35:16 into 35:15,
  Job 38:39-41 printed as 39:1-3, Job 40:20-24 printed as 40:14-19,
  Acts 19:41 into 19:40, 2 Corinthians 13:14 printed as 13:13.
  Cross-translation verse lookups will not match 1:1 in these passages.
- **DRB is the 73-book Challoner edition** (66 canonical books plus Tobit,
  Judith, Wisdom, Sirach, Baruch, 1-2 Maccabees). Its Psalms use Vulgate
  numbering (DRB Psalm 118 = KJV Psalm 119), so cross-translation Psalm
  lookups will not match 1:1.
- **KJV accuracy caveat:** the ingested KJV text comes from the named
  source commit, but edition-level 1769 accuracy has not been established.
  Do not treat it as a verified 1769 edition.

## Study resources (data/study.db)

### Commentaries: 72,493 entries

| Source | Entries | Coverage |
|--------|---------|----------|
| John Gill's Exposition (1763) | 32,036 | Whole Bible |
| Adam Clarke's Commentary | 14,206 | Whole Bible |
| Barnes' Notes | 7,354 | New Testament only (no faithful PD full-Bible transcription was found) |
| Keil & Delitzsch, Commentary on the Old Testament | 6,324 | Old Testament; partial (see known gaps below) |
| Matthew Henry's Complete Commentary | 5,387 | Whole Bible |
| Calvin's Commentaries (Calvin Translation Society translation) | 4,972 | Partial (Calvin never covered the whole Bible) |
| Jamieson, Fausset & Brown | 2,046 | Whole Bible |
| Spurgeon's Treasury of David | 150 | Psalms only |

### Dictionaries: 18,664 entries (15,499 distinct terms)

| Source | Entries |
|--------|---------|
| International Standard Bible Encyclopaedia (1915) | 9,349 |
| Nave's Topical Bible (1896) | 4,726 |
| Easton's Illustrated Bible Dictionary (1897) | 3,961 |
| Torrey's New Topical Text Book (1897) | 628 |

### Lexicon: 55,685 rows (27,081 Greek, 28,604 Hebrew)

| Source | Rows |
|--------|------|
| Strong's Greek and Hebrew Dictionaries (1890) | 13,260 (5,012 Greek, 8,248 Hebrew) |
| STEPBible TBESH (Hebrew) | 11,682 |
| STEPBible TBESG (Greek) | 11,035 |
| BDB via OpenScriptures HebrewLexicon (Hebrew) | 8,674 |
| STEPBible TFLSJ (Greek) | 5,709 |
| STEPBible TFLSJ extra (Greek) | 5,325 |

### Interlinear: 447,748 word rows (142,096 Greek, 305,652 Hebrew)

Word-by-word Hebrew (OT) and Greek (NT) behind
`GET /v1/interlinear/{book}/{chapter}/{verse}`, covering all 31,102 KJV
verses: 31,060 with the selected critical-text reading, 42 with
variant-tradition readings only (verses absent from the critical text,
e.g. Mark 16:9-20).

| Source | Word rows |
|--------|-----------|
| STEPBible TAGNT (Greek NT) | 142,096 (137,646 selected reading, 4,450 variants) |
| STEPBible TAHOT (Hebrew OT) | 305,652 (305,473 selected reading, 179 variants) |

### Phos Intensive Verse Study

`GET /v1/verse-study/{book}/{chapter}/{verse}` is a composite endpoint over
the sections above: it reads the verse texts, interlinear words, lexicon
definitions, cross-references, commentaries, devotionals, and prayers and
returns them as one response. It holds no data of its own and adds no new
sources; coverage follows the source sections. The 42 KJV verses absent
from the critical text return an empty `key_words` list with a note
pointing to `GET /v1/interlinear` for the variant-tradition readings.

### Cross-references: 573,192 rows

From the Treasury of Scripture Knowledge (CrossWire SWORD module v1.4,
declared Public Domain).

### Devotionals: 1,964 entries

| Source | Entries | Structure |
|--------|---------|-----------|
| Bagster, Daily Light on the Daily Path (1875) | 732 | 366 days, morning and evening |
| Spurgeon, Morning and Evening (1866) | 732 | 366 days, morning and evening |
| Chambers, My Utmost for His Highest (original 1927 text) | 366 | One entry per day |
| a Kempis, The Imitation of Christ (Benham translation) | 114 | One entry per day |
| Brother Lawrence, The Practice of the Presence of God | 20 | One entry per day |

### Liturgy: 703 rows

Morning and Evening Prayer from two Books of Common Prayer: 1662 edition
(332 rows) and 1928 US edition (371 rows).

## Known data-quality limitations

- **Keil & Delitzsch has documented missing passages:** Isaiah ch 6 and
  11-19 are missing (ch 3 and 64 recovered 2026-09-20, along with
  1 Samuel 1:1-8, 2 Kings 8:1-24, 2 Kings 21, and the 2 Kings 6:24-7:20
  famine narrative); Joshua 12, 1 Samuel 14, and 1 Kings 13 are prose-only.
  Some entries derive from OCR of the 1864-1892
  T. & T. Clark English translation and carry visible OCR noise. Details:
  `data/raw_v2/keil_delitzsch/PROVENANCE.md`.
- **Strong's Greek has known OCR incompleteness:** only 89.1%
  (5,012/5,624) of Greek entries could be recovered from the 1890 source
  scan; 511 entries were unrecoverable. 101 numbers (G2717, G3203-G3302)
  never existed in the 1890 source at all. The STEPBible Greek lexicons
  (TBESG, TFLSJ) cover these gaps through the lexicon source selection.
  Strong's Hebrew recovered 95.1% (8,248/8,867). Strong's rows carry no
  structured lemma/transliteration; the full entry text is in the
  definition field.
- **Barnes' Notes covers the New Testament only.** No faithful public
  domain full-Bible transcription was located.
- OCR-derived rows may contain misread headings or noise that deterministic
  parsing could not fix; fixes are applied as they are found, not
  retroactively guaranteed.

## Jurisdiction caveat

All content served by this API was cleared as **public domain under US
law**, either by age, by public-domain dedication (e.g. BSB, OEB, AKJV),
or by CC0-marked source editions. Two lexicon sources (the OpenScriptures
BDB transcription and the STEPBible lexicons) are **CC BY 4.0**, which
requires attribution; that attribution lives in the API docs and code.

Copyright status can differ in other countries. US public domain status
does not establish public domain status elsewhere. You are responsible for
complying with your own jurisdiction's copyright rules before using this
content outside the United States.

**KJV note:** within the United Kingdom, the Authorized (King James)
Version is under perpetual Crown copyright. This API serves the KJV from a
US-based service under its US public domain status.
