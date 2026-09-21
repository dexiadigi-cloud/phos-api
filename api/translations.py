"""Per-translation metadata for the Phos API.

Rights text is transcribed from
``verification/m1/provenance.md`` (verified 2026-09-20). This satisfies the
getBible condition that applications preserve and honor each translation's
own copyright metadata. Nothing here is legal advice; the notes describe
what the publishers state about their texts.
"""

TRANSLATIONS: dict[str, dict] = {
    "BSB": {
        "code": "BSB",
        "name": "Berean Standard Bible",
        "edition": "v5.2 (publisher USFM release)",
        "source": "BSB-publishing/bsb2usfm v5.2 "
                  "(https://github.com/BSB-publishing/bsb2usfm/releases/tag/v5.2)",
        "retrieved": "2026-09-20",
        "default": True,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain. The Berean Bible texts were officially "
                         "dedicated to the public domain as of April 30, 2023 "
                         "(berean.bible/terms.htm). All uses are freely permitted, "
                         "including commercial reproduction and sale.",
            "attribution": "Attribution appreciated but not required. Courtesy "
                           "request (not a license condition): altered derivatives "
                           "should not use the 'Berean' name; verbatim text served "
                           "as 'BSB' is within the grant.",
        },
    },
    "KJV": {
        "code": "KJV",
        "name": "King James Version",
        "edition": "Text from rennie...@88723a4 (2026-07-30); "
                   "edition-level 1769 accuracy not established",
        "source": "https://github.com/renniemaharaj/kjv-bible "
                  "(commit 88723a44bb3e3f229a34f9cf11ce1b7acf971eee)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain (first published 1611). The source repo "
                         "README asserts MIT licensing at the ingested commit.",
            "attribution": "No attribution required. Caveat: within the UK only, "
                           "the Authorized (King James) Version is under perpetual "
                           "Crown copyright; no impact on US serving.",
        },
    },
    "WEB": {
        "code": "WEB",
        "name": "World English Bible",
        "edition": "distribution 3.1 (2012-01-25), via getBible v2",
        "source": "getBible v2 whole-translation JSON "
                  "(distribution_source: http://ebible.org/web/)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per ebible.org: 'You may copy, publish, "
                         "proclaim, distribute, redistribute, sell, give away... "
                         "and use the World English Bible as much as you want.'",
            "attribution": "No attribution required. 'World English Bible' is an "
                           "eBible.org trademark: do not label altered text with "
                           "the name; verbatim text served as 'WEB' is fine.",
        },
    },
    "ASV": {
        "code": "ASV",
        "name": "American Standard Version",
        "edition": "1901; distribution 2.0 (2021-02-18), via getBible v2",
        "source": "getBible v2 whole-translation JSON "
                  "(distribution_source: http://www.ebible.org/bible/asv/)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain (first published 1901; US copyright long "
                         "expired). ebible.org: 'The American Standard Version of "
                         "the Holy Bible is in the Public Domain. Copy freely.'",
            "attribution": "No attribution required; no limits.",
        },
    },
    "YLT": {
        "code": "YLT",
        "name": "Young's Literal Translation",
        "edition": "eBible engylt (source files dated 2025-12-12)",
        "source": "https://ebible.org/Scriptures/engylt_usfx.zip "
                  "(license: https://ebible.org/engylt/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain (Robert Young, 1862). eBible.org: 'This "
                         "public domain Bible translation is brought to you "
                         "courtesy of eBible.org.'",
            "attribution": "No attribution required; no limits.",
        },
    },
    "DARBY": {
        "code": "DARBY",
        "name": "Darby Translation",
        "edition": "eBible engDBY (source files dated 2019-11-16)",
        "source": "https://ebible.org/Scriptures/engDBY_usfx.zip "
                  "(license: https://ebible.org/engDBY/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain (J. N. Darby, 1890). eBible.org marks "
                         "this edition Public Domain.",
            "attribution": "No attribution required; no limits.",
        },
    },
    "DRB": {
        "code": "DRB",
        "name": "Douay-Rheims Bible (1899 American Edition)",
        "edition": "eBible engDRA (source files dated 2022-11-03); 73 books",
        "source": "https://ebible.org/Scriptures/engDRA_usfx.zip "
                  "(license: https://ebible.org/engDRA/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain (Douay-Rheims American Edition of 1899, "
                         "translated from the Latin Vulgate). eBible.org: 'This "
                         "Public Domain Bible text is brought to you courtesy "
                         "of eBible.org.'",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Includes the 7 deuterocanonical books (Tobit, Judith, "
                 "Wisdom, Sirach, Baruch, 1-2 Maccabees) as book_order 66-72. "
                 "Psalms follow Vulgate numbering (e.g. DRB Psalm 118 = "
                 "KJV Psalm 119).",
    },
    "BBE": {
        "code": "BBE",
        "name": "Bible in Basic English",
        "edition": "eBible engBBE (source files dated 2018-08-30)",
        "source": "https://ebible.org/Scriptures/engBBE_usfx.zip "
                  "(license: https://ebible.org/engBBE/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain in the United States. eBible.org: "
                         "'printed in 1965 by Cambridge Press in England. "
                         "Published without any copyright notice and "
                         "distributed in America, this work fell immediately "
                         "and irretrievably into the Public Domain in the "
                         "United States according to the UCC convention of "
                         "that time.'",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Territorial caveat: eBible's public-domain statement is "
                 "US-specific (UCC convention). Non-US rights not verified.",
    },
    "GENEVA": {
        "code": "GENEVA",
        "name": "Geneva Bible (1599)",
        "edition": "eBible enggnv (source files dated 2024-03-16)",
        "source": "https://ebible.org/Scriptures/enggnv_usfx.zip "
                  "(license: https://ebible.org/enggnv/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain. eBible.org: 'This digital copy is "
                         "freely available world-wide, with no copyright "
                         "restrictions, courtesy of eBible.org and many "
                         "others.'",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Original 1599 spelling preserved (e.g. 'loued', 'hee', "
                 "'worlde'); not modernized.",
    },
    "AKJV": {
        "code": "AKJV",
        "name": "American King James Version",
        "edition": "BibleCorps ENG-B-AKJV2018-pd-PSFM (Version 2023.1223)",
        "source": "https://github.com/BibleCorps/ENG-B-AKJV2018-pd-PSFM "
                  "(p.sfm files; repo filenames carry [PD])",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain by author dedication: 'I am hereby "
                         "putting the American King James version of the "
                         "Bible into the public domain on November 8, 1999. "
                         "You may use it in any manner you wish: copy it, "
                         "sell it, modify it, etc. You can't copyright it or "
                         "prevent others from using it.' - Michael Peter "
                         "(Stone) Engelbrite. The source \\id lines read "
                         "'Public Domain on November 8, 1999.'",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Rights caveat (documented, not hidden): getBible v2's "
                 "aggregator metadata for its akjv distribution "
                 "(distribution 2.1, 2023-12-27, sourced from this same "
                 "BibleCorps repo) labels it 'Copyrighted; Free "
                 "non-commercial distribution'. That conflicts with the "
                 "author's 1999 dedication and the repo's own [PD] marking. "
                 "Phos ingests the BibleCorps PD edition directly, not the "
                 "getBible distribution; the conflict is recorded here so "
                 "the final call stays with the project owner.",
    },
    "OEB": {
        "code": "OEB",
        "name": "Open English Bible (US spelling)",
        "edition": "eBible engoebus (source files dated 2026-08-08)",
        "source": "https://ebible.org/Scriptures/engoebus_usfx.zip "
                  "(license: https://ebible.org/engoebus/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per eBible.org (marked Public Domain; "
                         "the Open English Bible is released CC0 by "
                         "OpenEnglishBible.org).",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Partial translation: 44 books (complete New Testament plus "
                 "Genesis, Joshua, Ruth, Esther, Psalms, and Hosea-Malachi). "
                 "The OEB Old Testament was never finished.",
    },
    "WEBSTER": {
        "code": "WEBSTER",
        "name": "Webster Bible",
        "edition": "Noah Webster's 1833 revision of the KJV (source files "
                   "dated 12 Dec 2025)",
        "source": "https://ebible.org/Scriptures/engwebster_usfm.zip "
                  "(license: https://ebible.org/engwebster/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per eBible.org (licensing field: "
                         "'Public Domain'). First published 1833; Noah "
                         "Webster died 1843.",
            "attribution": "No attribution required; no limits.",
        },
    },
    "WEYMOUTH": {
        "code": "WEYMOUTH",
        "name": "Weymouth New Testament",
        "edition": "The New Testament in Modern Speech, 3rd edition (1913) "
                   "transcription; first published 1903",
        "source": "Project Gutenberg ebooks 8828-8854 "
                  "(catalog: 'Public domain in the USA')",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain in the USA (first published 1903; "
                         "Richard Francis Weymouth died 1902). Project "
                         "Gutenberg catalog lists each book 'Public domain "
                         "in the USA.'",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Partial translation: New Testament only (27 books). "
                 "Source anomaly corrected: Gutenberg's Luke file mislabeled "
                 "Luke 8:23 as 2:23; remapped at ingest with the raw file "
                 "kept byte-identical.",
    },
    "LXX2012": {
        "code": "LXX2012",
        "name": "LXX2012: Septuagint in English 2012",
        "edition": "Michael Paul Johnson's 2012 language update of Brenton's "
                   "1851 English translation of the Septuagint",
        "source": "https://ebible.org/eng-lxx2012/ "
                  "(license: https://ebible.org/eng-lxx2012/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per eBible.org: Brenton's 1851 "
                         "translation 'has entered the Public Domain due to "
                         "the passage of sufficient time'; Michael Paul "
                         "Johnson's language updates 'are dedicated to the "
                         "Public Domain by the author of those edits. "
                         "Therefore this edition may be freely copied, "
                         "published, etc.'",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Septuagint versification is kept exactly as in the source "
                 "(translation-scoped): Greek Psalm numbering (151 psalms), "
                 "so references do not align 1:1 with Hebrew-based Bibles. "
                 "Includes 15 deuterocanonical books (Tobit, Judith, Wisdom, "
                 "Sirach, Baruch, 1-2 Maccabees, Epistle of Jeremy, Prayer of "
                 "Azarias, Susanna, Bel and the Dragon, 1 Esdras, Prayer of "
                 "Manasses, 3-4 Maccabees); 7 of these match the DRB's "
                 "deuterocanon names. Known source gap: 1 Kings 14:1 has no "
                 "text in the edition and is absent.",
    },
    "LSG1910": {
        "code": "LSG1910",
        "name": "Louis Segond 1910",
        "edition": "eBible fraLSG (source files dated 2026-08-08)",
        "source": "https://ebible.org/Scriptures/fraLSG_usfm.zip "
                  "(license: https://ebible.org/fraLSG/copyright.htm)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per eBible.org: 'Cette Bible est "
                         "dans le domaine public. Il n'est pas protégé par "
                         "copyright.' / 'This Bible is in the Public Domain. "
                         "It is not copyrighted.' First published 1910; "
                         "Louis Segond died 1909.",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "First non-English translation in Phos (French). "
                 "Traditional French versification is kept exactly as in the "
                 "source (translation-scoped): psalm titles numbered as "
                 "verse 1, Exodus 7:26-29 = KJV 8:1-4, Revelation 12:18 = "
                 "KJV 13:1, and similar offsets; full list in "
                 "data/raw_v2/lsg1910/PROVENANCE.md. Territorial caveat: US "
                 "clearance is by pre-1931 expiry; non-US status rests on "
                 "the translator's 1909 death (life-plus-70 expired 1980).",
    },
    "LUTHER1912": {
        "code": "LUTHER1912",
        "name": "Luther Bible 1912",
        "edition": "eBible deu1912 (source files dated 2025-12-29)",
        "source": "https://ebible.org/Scriptures/deu1912_usfm.zip "
                  "(rights statement in the edition's copr.htm: Public Domain)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per eBible.org: the edition's "
                         "copyright file lists the licensing field as "
                         "Public Domain ('The Holy Bible in German, Luther "
                         "1912', translation by Martin Luther). First "
                         "published 1912 (pre-1931, US PD by expiry); "
                         "Martin Luther died 1546; the 1912 revision was a "
                         "church-committee revision published 1912.",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Second non-English translation in Phos (German). "
                 "31,102 verse keys, matching KJV numbering exactly; no "
                 "versification deltas. Psalm titles are joined to verse 1 "
                 "in the edition text (translation-scoped). Territorial "
                 "caveat: US clearance is by pre-1931 expiry; that does not "
                 "by itself establish non-US status.",
    },
    "ALMEIDA": {
        "code": "ALMEIDA",
        "name": "Almeida Recebida",
        "edition": "Biblia Almeida Recebida v1.7 (source dump dated 2017-03-17)",
        "source": "https://www.almeidarecebida.org/download-portuguese-bible-almeida-recebida-xml/ "
                  "(publisher states: 'This Bible (PorAR) is in the Public Domain')",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per the publisher (almeidarecebida.org): "
                         "the download page states 'This Bible (PorAR) is in the "
                         "Public Domain.' The same page carries a generic "
                         "BY-NC-SA site notice (WordPress plugin footer); the "
                         "specific statement about the Bible text is Public "
                         "Domain. Almeida Recebida is a Textus Receptus-based "
                         "revision of Almeida with updated Portuguese "
                         "(v1.7, March 2017).",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Third non-English translation in Phos (Portuguese). "
                 "31,102 verse keys, matching KJV numbering exactly; no "
                 "versification deltas. Territorial caveat: clearance rests on "
                 "the publisher's public-domain declaration, which does not by "
                 "itself establish status in every jurisdiction.",
    },
    "RVA1909": {
        "code": "RVA1909",
        "name": "Reina-Valera 1909",
        "edition": "eBible spaRV1909 (source files dated 2015-08-10; HTML generated 2026-08-08)",
        "source": "https://ebible.org/Scriptures/spaRV1909_usfm.zip "
                  "(rights statement in the edition's copr.htm: Public Domain)",
        "retrieved": "2026-09-20",
        "default": False,
        "rights": {
            "status": "public_domain",
            "copyright": "Public domain per eBible.org: the edition's "
                         "copyright page lists the licensing field as "
                         "Public Domain ('The Holy Bible in Spanish, Reina "
                         "Valera translation of 1909', translation by Reina "
                         "y Valera; 'Dominio Publico'). First published "
                         "1909 (pre-1931, US PD by expiry); Casiodoro de "
                         "Reina died 1594, Cipriano de Valera died 1602.",
            "attribution": "No attribution required; no limits.",
        },
        "notes": "Fourth non-English translation in Phos (Spanish); "
                 "completes the v3 multilingual set. 31,084 text-bearing "
                 "verses: Spanish versification is kept exactly as in the "
                 "source (translation-scoped), with 18 empty placeholder "
                 "verse markers dropped. Chapter offsets: Numbers 12:16 = "
                 "KJV numbering printed at 13:1, Numbers 29:40 at 30:1, "
                 "1 Samuel 23:29 at 24:1, Hosea 11:12 at 12:1, Jonah 1:17 "
                 "at 2:1. Merges: 2 Samuel 20:26 into 20:25, 2 Chronicles "
                 "33:25 into 33:24, Job 35:16 into 35:15, Job 38:39-41 "
                 "printed as 39:1-3, Job 40:20-24 printed as 40:14-19, "
                 "Acts 19:41 into 19:40, 2 Corinthians 13:14 printed as "
                 "13:13. Full list in data/raw_v2/rva1909/PROVENANCE.md. "
                 "Territorial caveat: US clearance is by pre-1931 expiry; "
                 "that does not by itself establish non-US status.",
    },
}

TRANSLATION_CODES = list(TRANSLATIONS)
DEFAULT_TRANSLATION = "BSB"
