# Sources and Attribution

**This page is descriptive, not legal advice.** It lists every translation and study source in the Phos databases, the exact digital edition ingested, the rights basis on which it is served, and the attribution text required where a license demands one. Nothing here has been reviewed by a lawyer.

All rights text below is transcribed from the ingestion records: `api/translations.py` for translations (rights text transcribed from `verification/m1/provenance.md`, verified 2026-09-20), the `sources`, `lexicon_sources`, `dictionary_sources`, and `liturgy_sources` tables in `data/study.db` for study material, and `data/raw_v2/*/PROVENANCE.md` where noted. Verse counts were queried from `data/scripture.db` on 2026-09-20.

## Bible translations

All 17 translation codes in `data/scripture.db` are listed. Counts are verses per translation in the live database, re-queried on 2026-09-21 after the BBE removal.

| Code | Translation | Edition ingested | Verses |
| --- | --- | --- | --- |
| BSB | Berean Standard Bible (default) | v5.2 publisher USFM release (BSB-publishing/bsb2usfm) | 31,086 |
| KJV | King James Version | Text from rennie...@88723a4 (2026-07-30); edition-level 1769 accuracy not established | 31,102 |
| WEB | World English Bible | Distribution 3.1 (2012-01-25), via getBible v2 | 31,095 |
| ASV | American Standard Version (1901) | Distribution 2.0 (2021-02-18), via getBible v2 | 31,086 |
| YLT | Young's Literal Translation | eBible engylt (source files dated 2025-12-12) | 31,102 |
| DARBY | Darby Translation | eBible engDBY (source files dated 2019-11-16) | 31,099 |
| DRB | Douay-Rheims Bible (1899 American Edition) | eBible engDRA (source files dated 2022-11-03); 73 books incl. deuterocanon | 35,811 |
| GENEVA | Geneva Bible (1599) | eBible enggnv (source files dated 2024-03-16); original spelling preserved | 31,090 |
| AKJV | American King James Version | BibleCorps ENG-B-AKJV2018-pd-PSFM (2023.1223) | 31,102 |
| OEB | Open English Bible (US spelling) | eBible engoebus (source files dated 2026-08-08); 44 books, OT unfinished | 13,894 |
| WEBSTER | Webster Bible (1833) | eBible engwebster_usfm (source files dated 2025-12-12) | 31,102 |
| WEYMOUTH | Weymouth New Testament | 3rd edition (1913) transcription via Project Gutenberg; NT only | 7,957 |
| LXX2012 | Septuagint in English 2012 | Michael Paul Johnson's 2012 language update of Brenton's 1851 English translation | 28,351 |
| LSG1910 | Louis Segond 1910 (French) | eBible fraLSG USFM (source files dated 2026-08-08); first non-English translation | 31,170 |
| LUTHER1912 | Luther Bible 1912 (German) | eBible deu1912 USFM (source files dated 2025-12-29); second non-English translation | 31,102 |
| ALMEIDA | Almeida Recebida (Portuguese) | Biblia Almeida Recebida v1.7 (source dump dated 2017-03-17); third non-English translation | 31,102 |
| RVA1909 | Reina-Valera 1909 (Spanish) | eBible spaRV1909 USFM (source files dated 2015-08-10); fourth non-English translation | 31,084 |

**Rights basis (translations).** All 17 translations are served as public domain or public-domain-dedicated text. No attribution is required for any of them. (The Bible in Basic English was removed 2026-09-21: its public-domain determination was US-only.)

- **BSB:** Public domain by dedication. The Berean Bible texts were officially dedicated to the public domain on April 30, 2023 (berean.bible/terms.htm). Attribution is appreciated but not required. Courtesy request (not a license condition): altered derivatives should not use the "Berean" name.
- **KJV:** Public domain (first published 1611). Caveat: within the UK only, the Authorized Version is under perpetual Crown copyright; this has no impact on US serving.
- **WEB:** Public domain per ebible.org ("copy, publish... sell, give away... as much as you want"). "World English Bible" is an eBible.org trademark: do not label altered text with the name.
- **ASV:** Public domain (1901, US copyright long expired). No limits.
- **YLT:** Public domain (Robert Young, 1862). No limits.
- **DARBY:** Public domain (J. N. Darby, 1890). No limits.
- **DRB:** Public domain (Douay-Rheims American Edition of 1899, translated from the Latin Vulgate). Includes the 7 deuterocanonical books; Psalms follow Vulgate numbering (e.g. DRB Psalm 118 = KJV Psalm 119).
- **GENEVA:** Public domain. Original 1599 spelling preserved.
- **AKJV:** Public domain by author dedication (Michael Peter (Stone) Engelbrite, November 8, 1999: "You may use it in any manner you wish: copy it, sell it, modify it"). Rights caveat on record: getBible v2's aggregator metadata for its own akjv distribution labels it "Copyrighted; Free non-commercial distribution", which conflicts with the author's dedication. Phos ingests the BibleCorps PD edition directly, not the getBible distribution; the conflict is recorded here so the final call stays with the project owner.
- **OEB:** Public domain (CC0 by OpenEnglishBible.org). Partial translation; NT complete, OT unfinished.
- **WEBSTER:** Public domain per eBible.org. Noah Webster's 1833 revision of the KJV.
- **WEYMOUTH:** Public domain in the USA (Project Gutenberg catalog, 1903 first edition). NT only (27 books).
- **LXX2012:** Public domain: Brenton's 1851 translation is PD by age; Michael Paul Johnson's language updates are dedicated to the public domain by the author of those edits. Septuagint versification is kept as in the source (Greek Psalm numbering, 151 psalms), so references do not align 1:1 with Hebrew-based Bibles. Includes 15 deuterocanonical books; 1 Kings 14:1 has no text in this edition and is absent.
- **LSG1910:** Public domain per eBible.org ("Cette Bible est dans le domaine public. Il n'est pas protégé par copyright." / "This Bible is in the Public Domain. It is not copyrighted."). Louis Segond's 1910 French translation (translator d. 1909). First non-English translation in the API. Traditional French versification is kept exactly as in the source (translation-scoped): psalm titles are numbered as verse 1 (e.g. LSG Psalm 3:9 = KJV Psalm 3:8), Exodus 7:26-29 = KJV 8:1-4, Revelation 12:18 = KJV 13:1, and similar offsets (full list in the project provenance notes). Territorial caveat: US clearance is by pre-1931 expiry; non-US status rests on the translator's 1909 death (life-plus-70 expired 1980).
- **LUTHER1912:** Public domain per eBible.org (the edition's copyright file lists the licensing field as Public Domain: "The Holy Bible in German, Luther 1912", translation by Martin Luther). The 1912 revision of Luther's Bible, first published 1912 (pre-1931, US public domain by expiry). Second non-English translation in the API. 31,102 verse keys, matching KJV numbering exactly; psalm titles are joined to verse 1 in the edition text. Territorial caveat: US clearance is by pre-1931 expiry; that does not by itself establish non-US status.
- **ALMEIDA:** Public domain per the publisher (almeidarecebida.org): the download page states "This Bible (PorAR) is in the Public Domain." The same page carries a generic BY-NC-SA site notice (WordPress plugin footer); the specific statement about the Bible text is Public Domain. Almeida Recebida is a Textus Receptus-based revision of Almeida with updated Portuguese (v1.7, March 2017). Third non-English translation in the API. 31,102 verse keys, matching KJV numbering exactly. Territorial caveat: clearance rests on the publisher's public-domain declaration, which does not by itself establish status in every jurisdiction.
- **RVA1909:** Public domain per eBible.org (the edition's copyright page lists the licensing field as Public Domain: "The Holy Bible in Spanish, Reina Valera translation of 1909", translation by Reina y Valera; "Dominio Publico"; eBible.org certified). First published 1909 (pre-1931, US public domain by expiry). Fourth non-English translation in the API; completes the v3 multilingual set. 31,084 text-bearing verses: Spanish versification is kept exactly as in the source (translation-scoped), with 18 empty placeholder verse markers dropped (chapter offsets: Numbers 12:16 printed at 13:1, Numbers 29:40 at 30:1, 1 Samuel 23:29 at 24:1, Hosea 11:12 at 12:1, Jonah 1:17 at 2:1; merges: 2 Samuel 20:26 into 20:25, 2 Chronicles 33:25 into 33:24, Job 35:16 into 35:15, Job 38:39-41 printed as 39:1-3, Job 40:20-24 printed as 40:14-19, Acts 19:41 into 19:40, 2 Corinthians 13:14 printed as 13:13). Territorial caveat: US clearance is by pre-1931 expiry; that does not by itself establish non-US status.

## Commentaries

All are public domain; no attribution is required for any of them. Counts are commentary entries per source in the live database.

| Source | What it is | Edition ingested | Entries |
| --- | --- | --- | --- |
| Matthew Henry, Complete Commentary on the Whole Bible | Verse commentary, 1706-1721 (author d. 1714) | HelloAO CC0 transcription (1,166 chapters) plus CCEL gap-fill for 23 chapters (CCEL: "Public domain. May be copied and distributed freely") | 5,387 |
| Jamieson, Fausset & Brown, Commentary Critical and Explanatory | Verse commentary, 1871 (authors d. 1870-1910) | CCEL 1871 proofed transcription (CCEL rights: Public Domain; status: Proofed) | 2,046 |
| Albert Barnes, Barnes' New Testament Notes | NT commentary (27 books only; no faithful full-Bible PD transcription located) | CCEL transcription of the 1949 Baker reprint (CCEL rights: Public Domain) | 7,354 |
| John Gill's Exposition of the Entire Bible (1763) | Verse commentary (author d. 1771) | Internet Archive djvu.txt OCR of the 1763 edition; mechanical reproduction of a PD work creates no new copyright | 32,036 |
| Adam Clarke, Commentary on the Whole Bible | Verse commentary, 1810-1825 (author d. 1832) | HelloAO adam-clarke; commentary metadata declares CC Public Domain Mark 1.0 | 14,206 |
| John Calvin, Commentaries (Calvin Translation Society English translation, 1843-1855) | Commentary (author d. 1564) | CCEL calcom01-calcom45; translators King, Bingham, Beveridge, Anderson, Pringle, Owen, Myers, and Pringle, all PD by age; each CCEL file header states Rights: Public Domain | 4,972 |
| Keil & Delitzsch, Commentary on the Old Testament | OT commentary; 1864-1892 T. & T. Clark English translation of the German original (all volumes pre-1931, US PD by expiry); 39 OT books represented with documented missing passages and OCR defects | Internet Archive item BiblicalCommentaryOldTestament.KeilAndDelitzsch.6 (item carries no license field; clearance is PD-by-expiry, not an IA license declaration); OCR is a faithful transcription of a PD text and carries no new copyright | 6,324 |
| C. H. Spurgeon, The Treasury of David (Psalms) | Psalm-by-psalm commentary (author d. 1892) | Internet Archive item ch-spurgeon-the-treasury-of-david-in-one-volume_202011, carrying Creative Commons Public Domain Mark 1.0 | 150 |

## Cross-references

- **Treasury of Scripture Knowledge (TSK).** CrossWire SWORD module v1.4 declares DistributionLicense=Public Domain; attributed to Canne, Browne, Blayney, Scott et al., "about 1880". 573,192 cross-reference rows in the live database. Caveat: the exact relation of this digital text to the 1836 first edition has not been independently verified.

## Dictionaries

All are public domain; no attribution is required for any of them. Counts are dictionary entries in the live database.

| Source | What it is | Edition ingested | Entries |
| --- | --- | --- | --- |
| M. G. Easton, Illustrated Bible Dictionary (1897) | Bible dictionary | CrossWire SWORD Easton module v2.0.1 (conf declares DistributionLicense=Public Domain) | 3,961 |
| International Standard Bible Encyclopaedia (1915), ed. James Orr | Bible encyclopaedia | CrossWire SWORD ISBE module v2.2 (conf declares DistributionLicense=Public Domain); the 1939 Eerdmans reissue is a verbatim reprint of the 1915 Orr text | 9,349 |
| Orville J. Nave, Nave's Topical Bible (1896) | Topical index | Internet Archive item navestopicalbibl0000orvi_h3u8 (faithful scan/OCR, no new rights claimed) | 4,726 |
| R. A. Torrey, The New Topical Text Book (1897) | Topical text book | ACU mirror of Ernie Stefanik's electronic edition, produced from the 1897 Revell edition with no new copyright claim | 628 |

## Devotionals

All are public domain; no attribution is required for any of them. Counts are devotional entries in the live database.

| Source | What it is | Edition ingested | Entries |
| --- | --- | --- | --- |
| C. H. Spurgeon, Morning and Evening (1866) | Daily devotional (author d. 1892) | Transcription: russianryebread/morning-and-evening @ 6caf938 (claims no copyright on the transcription) | 732 |
| Samuel Bagster, Daily Light on the Daily Path (1875) | Daily all-scripture devotional | Transcription: gm5dna/daily-light @ c36a7bf (MIT repo asserting the text is public domain). Caveat: 529 of 5,656 item references were reconstructed from verse text against the KJV; the reconstruction is fully documented in the ingestion record | 732 |
| Oswald Chambers, My Utmost for His Highest | Daily devotional; original 1927 text (Simpkin & Marshall, England; 1935 Dodd, Mead, US; author d. 1917) | Transcribed from utmost.org's official-publisher "classic" post type (WP REST API). US public domain since 2023-01-01. Edition verified as the original text, not the 1992 Reimann updated edition (see `data/raw_v2/my_utmost/PROVENANCE.md`) | 366 |
| Brother Lawrence, The Practice of the Presence of God | Spiritual letters/conversations (author d. 1691) | Project Gutenberg eBook No. 13871, cataloged "Public domain in the USA" | 20 |
| Thomas a Kempis, The Imitation of Christ | Devotional classic (author d. 1471); William Benham English translation (1831-1910) | Project Gutenberg eBook #1653, cataloged "Public domain in the USA" | 114 |

## Liturgy

Both are public domain; no attribution is required. Counts are liturgy entries in the live database.

| Source | What it is | Edition ingested | Entries |
| --- | --- | --- | --- |
| Book of Common Prayer (1662), Morning and Evening Prayer | Anglican liturgy | Wikisource transcription of the 1892 Pickering verbatim reprint (per-page pinned revisions) | 332 |
| Book of Common Prayer (1928, US), Morning and Evening Prayer | Anglican liturgy | Justus Anglican transcription via Wayback, corrected against the Internet Archive scan of the 1928 Standard Book; US copyright expired 2024-01-01 (95-year term) | 371 |

## Lexicons

One source is public domain; four are licensed CC BY 4.0 and carry required attribution (see the next section). Counts are lexicon entries in the live database.

| Source | What it is | Edition ingested | Rights | Entries |
| --- | --- | --- | --- | --- |
| Strong's Hebrew and Greek Dictionaries (1890) | James Strong's Greek (G5624 range) and Hebrew dictionaries | Internet Archive item StrongsGreekAndHebrewDictionaries1890 (item declares CC0 1.0); IA djvu.txt OCR is a mechanical reproduction of PD works and creates no new copyright | Public domain (CC0) | 13,260 |
| OpenScriptures HebrewLexicon (BDB transcription) | Brown-Driver-Briggs Hebrew lexicon XML transcription (HebrewStrong.xml) | Open Scriptures Hebrew Bible Project, commit 21c9add (2019-09-02); the XML transcription is CC BY 4.0 per the repo readme | CC BY 4.0 | 8,674 |
| STEPBible TBESH (Translators Brief lexicon of Extended Strongs for Hebrew) | Hebrew lexicon based on abridged BDB | STEPBible-Data, commit b99716b (2026-09-18); data created by www.STEPBible.org based on work at Tyndale House, Cambridge | CC BY 4.0 | 11,682 |
| STEPBible TBESG (Translators Brief lexicon of Extended Strongs for Greek) | Greek lexicon based on Abbott-Smith (+ Middle Liddell gaps) | STEPBible-Data, commit b99716b (2026-09-18) | CC BY 4.0 | 11,035 |
| STEPBible TFLSJ (Translators Formatted full LSJ Bible lexicon) | Greek lexicon edited from the full Liddell-Scott-Jones | STEPBible-Data, commit b99716b (2026-09-18) | CC BY 4.0 | 5,709 |
| STEPBible TFLSJ-extra | Additional entries from the same TFLSJ source set | STEPBible-Data, commit b99716b (2026-09-18) | CC BY 4.0 | 5,325 |

Caveat on Strong's: the ingestion is an OCR transcription of the 1890 text and is known to be incomplete in places, especially in the Greek dictionary entries. This is a data-quality note, not a rights issue: the text is public domain.

## Interlinear

Word-by-word Hebrew (Old Testament) and Greek (New Testament) for every KJV verse, behind `GET /v1/interlinear/{book}/{chapter}/{verse}`. Each word carries the original text, transliteration, English gloss, Strong's number, morphology, and lemma, in reading order. Both sources are licensed CC BY 4.0 and carry required attribution (see the next section). Counts are word rows in the live database.

| Source | What it is | Edition ingested | Rights | Word rows |
| --- | --- | --- | --- | --- |
| STEPBible TAGNT (Translators Amalgamated Greek NT) | Greek NT: transliteration, gloss, Strong's, morphology, lemma per word | STEPBible-Data TAGNT files, retrieved 2026-09-20; data created by www.STEPBible.org based on work at Tyndale House, Cambridge | CC BY 4.0 | 142,096 |
| STEPBible TAHOT (Translators Amalgamated Hebrew OT) | Hebrew OT: transliteration, gloss, Strong's, morphology, lemma per word | STEPBible-Data TAHOT files, retrieved 2026-09-20; data created by www.STEPBible.org based on work at Tyndale House, Cambridge | CC BY 4.0 | 305,652 |

Reading selection: the Greek returns the Nestle-Aland/SBL-compatible reading (every word attested in those editions); the Hebrew follows the Leningrad Codex with the translators' Qere choices. Variant readings from other manuscript traditions are returned grouped by tradition. The 42 KJV verses absent from the critical text (e.g. Mark 16:9-20, John 7:53-8:11) return variant-tradition readings only, flagged as such.

Phos modifications to the source files: verse references remapped from the files' NRSV versification to KJV versification using the files' own bracket markers; source verses split by versification differences concatenated in source order within each KJV verse with positions renumbered 1..N; Psalm titles mapped to verse 1 and ordered before the verse text; Strong's numbers normalized to base form (sub-entry letters stripped) so they work directly with `/v1/word`; Spanish and sub-meaning columns excluded.

## Required attribution text (CC BY 4.0 sources)

The five lexicon sources above and the two interlinear sources above marked CC BY 4.0 are licensed under the Creative Commons Attribution 4.0 International license (https://creativecommons.org/licenses/by/4.0/). Their licenses require attribution, which must appear in the API docs and code. The attribution text is reproduced verbatim from the `lexicon_sources` and `sources` tables:

- **OpenScriptures BDB:** "Brown-Driver-Briggs Hebrew lexicon XML transcription by the Open Scriptures Hebrew Bible Project, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)."
- **STEPBible (TBESH, TBESG, TFLSJ, TFLSJ-extra):** "STEPBible lexicon data (TBESH, TBESG, TFLSJ), Tyndale House, Cambridge, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Source: https://github.com/STEPBible/STEPBible-Data, www.STEPBible.org."
- **STEPBible (TAGNT, TAHOT interlinear):** "STEPBible interlinear data (TAGNT, TAHOT), Tyndale House, Cambridge, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Source: https://www.STEPBible.org."

The underlying works these transcriptions draw on (BDB 1906, Strong's Hebrew dictionary, Abbott-Smith, Middle Liddell, Liddell-Scott-Jones) are themselves public domain; the CC BY 4.0 obligation attaches to the digital transcriptions.

## Phos Intensive Verse Study

`GET /v1/verse-study/{book}/{chapter}/{verse}` is a composite endpoint: it reads the verse texts, interlinear words, lexicon definitions, cross-references, commentaries, devotionals, and prayers described in the sections above and returns them as one response. It adds no new sources, so no new rights obligations arise beyond those already documented for each section. The CC BY 4.0 duties for the interlinear words (STEPBible TAGNT/TAHOT) and any key-word definition drawn from BDB or a STEPBible lexicon are satisfied per response by the `sources` array (every contributing source with its rights status) and the `rights_note`, which carries the credit text, the CC BY 4.0 deed link (https://creativecommons.org/licenses/by/4.0/), and the Phos modification record (selection of the Nestle-Aland/SBL critical-text reading for Greek and the Leningrad Codex with Qere choices for Hebrew, mapped to KJV versification). The same credit text appears in the endpoint's OpenAPI description.

## Caveats summary

For quick reference, the sources with territorial, editorial, or verification caveats:

1. **KJV:** perpetual Crown copyright applies only within the UK; no impact on US serving.
2. **Weymouth:** public domain in the USA per Project Gutenberg's catalog.
3. **My Utmost for His Highest:** US public domain since 2023-01-01; the ingested edition is the original 1927 text, not the 1992 Reimann updated edition.
4. **TSK:** the exact relation of the ingested SWORD module text to the 1836 first edition has not been independently verified.
5. **Daily Light:** 529 of 5,656 item references were reconstructed from verse text against the KJV (documented in the ingestion record).
6. **Strong's dictionaries:** OCR-based transcription with known incompleteness, especially in the Greek entries; data-quality note only.
7. **AKJV:** conflicting metadata on record (author's 1999 PD dedication and BibleCorps [PD] marking versus getBible v2's "Copyrighted; Free non-commercial distribution" label); Phos ingests the BibleCorps PD edition directly.
