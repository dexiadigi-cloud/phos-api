# Phos Intensive Verse Study: design spec

Date: 2026-09-20. Status: design only, not built.
Concept owner: Jeremiah. Locked name: "Phos Intensive Verse Study".

## 1. What it is

A single composite endpoint that returns everything a reader needs for one
verse in one call:

- the verse in up to four translations,
- the most important original-language words with their meanings,
- the top cross-references,
- one commentary excerpt,
- up to three devotionals anchored to the verse,
- one related prayer.

It is verse-scoped and curated. The existing `GET /v1/study` endpoint stays
as is: it is passage-scoped (spans), single-translation, and returns
commentary excerpts from all eight commentary sources with no key words,
devotionals, or prayer. The two endpoints are complementary, not
overlapping.

## 2. Endpoint

```
GET /v1/verse-study/{book}/{chapter}/{verse}
```

Path style matches `GET /v1/interlinear/{book}/{chapter}/{verse}`, its
closest cousin. Book names resolve through the existing reference parser,
so aliases (`jn`, `1jn`, `ps`) work the same as everywhere else.

Query parameters:

| Param | Default | Rule |
|---|---|---|
| `translations` | `BSB,KJV,WEB` | Comma-separated translation codes. Each validated against the translation registry; unknown code is a 400. Maximum 4; more is a 400. |
| `commentary` | `keil_delitzsch` (OT) / `barnes_nt` (NT) | Any of the eight commentary sources. Unknown source is a 400. |
| `office` | `morning` | `morning` or `evening`. Selects which prayer office the prayer is drawn from. Anything else is a 400. |

Auth: API key required, same as every other endpoint.

## 3. Response schema

Pydantic-style models. Field names follow existing API conventions.

```
PhosInterlinearResponse
  ref: str                    # "John 3:16" (parsed display form)
  book: str                   # "John"
  chapter: int
  verse: int
  testament: str              # "OT" | "NT"
  translations: list[VerseTranslation]
  key_words: list[KeyWord]
  key_words_note: str | null  # set only for variant-only verses (see 5.2)
  cross_refs: CrossRefs
  commentary: CommentaryExcerpt | null
  commentary_source: str       # source_id actually used
  devotionals: list[DevotionalMatch]
  prayer: PrayerMatch | null
  sources: list[SourceRef]    # every contributing source
  rights_note: str            # CC BY 4.0 attribution text (see 7)

VerseTranslation
  code: str                   # "BSB"
  present: bool               # false if this translation lacks the verse key
  text: str | null

KeyWord
  position: int               # word position in the verse (1-based)
  word: str                   # original-language word, e.g. "ἠγάπησεν"
  transliteration: str | null
  strongs: str                # "G25" (base form, works in /v1/word)
  gloss: str                  # short interlinear gloss, e.g. "to love"
  morphology: str              # e.g. "V-AAI-3S"
  lemma: str | null
  definition: str             # one short lexicon definition (see 5.2)
  definition_source: str      # source_id that supplied the definition

CrossRefs
  total: int
  refs: list[CrossRefItem]    # top 8, canonical order

CrossRefItem
  ref: str                    # "Romans 5:8"
  text: str                   # verse text in the first requested translation

CommentaryExcerpt
  source: str
  source_title: str
  ref_range: str               # "John 3:16", reuse existing range display
  text: str                   # excerpt, 600 chars max, word-boundary cut
  truncated: bool
  full_length: int

DevotionalMatch
  source: str                 # "daily_light"
  source_title: str
  part: str                   # "morning" | "evening"
  title: str | null
  anchor_ref: str
  text: str                   # excerpt, 600 chars max, word-boundary cut
  truncated: bool
  full_length: int
  match_kind: str             # "exact" | "nearby"

PrayerMatch
  office: str                 # "morning_prayer"
  edition: str                # "bcp1662" | "bcp1928"
  label: str | null           # e.g. "A Collect for Peace"
  speaker: str | null
  text: str                   # full block (average 130 chars, max ~950)
  match_kind: str             # "keyword" | "office_opening"
  matched_keywords: list[str] # empty when match_kind is "office_opening"

SourceRef
  id: str
  title: str
  rights: str                 # "Public Domain" | "CC BY 4.0"
```

## 4. Translations section

Look up `book/chapter/verse` in each requested translation independently.
Each translation keeps its own versification, so a verse present in KJV
may be absent in LSG1910; that translation returns `present: false,
text: null` instead of failing the whole request. If the verse is absent
from every requested translation, return 404.

## 5. Key words section

### 5.1 Selection rule (verified against the data)

Content words only: nouns, verbs, adjectives. Articles, prepositions,
conjunctions, particles, pronouns, adverbs, and interjections are
excluded. The rule reads the morphology codes already stored in
`interlinear_words`:

- Greek (`testament = 'NT'`): take the morphology string up to the first
  `-` (for `+`-compounds such as `CONJ + G1565=D`, take the text before
  the first `+`). If that part-of-speech tag is exactly `N`, `V`, or `A`,
  the word is a key word. This correctly excludes `ADV` (adverb) while
  keeping `A` (adjective).
- Hebrew (`testament = 'OT'`): split the morphology string on `/`. For
  each segment, strip one leading `H` if present. If the first letter of
  any segment is `N`, `V`, or `A`, the word is a key word. This correctly
  keeps `HTd/Ncmpa` (article + noun) and excludes `HC/To` (conjunction +
  object marker).

Key words are returned in verse position order, capped at 12. John 3:16
yields exactly 12 under this rule; Genesis 1:1 yields 5.

### 5.2 Definition rule

Each key word carries one short lexicon definition:

1. First non-empty `lexicon.gloss` for the word's Strong's number from
   the CC BY 4.0 sources, in order `bdb`, `step_tbesh`, `step_tbesg`,
   `step_tflsj`, `step_tflsjx`.
2. Fallback: the `strongs` definition (public domain), truncated to 250
   characters at a word boundary.
3. `definition_source` records the `source_id` used, so every CC BY 4.0
   definition is traceable to its source.

Known limitation: Strong's definitions are served as stored and some
carry OCR artifacts at the head of the entry. Cleaning them is a
separate data-quality task, not part of this build.

### 5.3 Variant-only verses

The 42 textually disputed verses (Mark 16:9-20, John 7:53-8:11, Acts
8:37, and the rest) have interlinear data in variant manuscript
traditions only. For these, `key_words` is empty and `key_words_note`
is set:

"Interlinear data for this verse exists in variant manuscript
traditions only; see GET /v1/interlinear/{book}/{chapter}/{verse}."

All other sections behave normally.

## 6. Cross-references, commentary, devotionals, prayer

### 6.1 Cross-references

Top 8 in canonical order (`ref_book_order`, `ref_chapter`, `ref_verse`),
with the total count. Each item includes the verse text in the first
requested translation. John 3:16 has 19 cross-references; the response
returns the first 8 and `total: 19`.

### 6.2 Commentary

One excerpt, not all eight sources. Default source is `keil_delitzsch`
for Old Testament verses and `barnes_nt` for New Testament verses; the
`commentary` query parameter overrides with any of the eight commentary
sources. If the chosen source has no row covering the verse, fall back
through the remaining sources in this order: `matthew_henry`,
`clarke`, `gill`, `jfb`, `calvin`, `keil_delitzsch`, `barnes_nt`,
`treasury_of_david`. If nothing covers the verse, `commentary` is null
and `commentary_source` is `"none"`.

The excerpt follows the existing 600-character convention: cut at a
word boundary, append an ellipsis, set `truncated: true`, and report
`full_length`. The full text remains available at `GET /v1/commentary`.

### 6.3 Devotionals

Devotionals are matched by verse anchor, not by date. Each devotional's
`anchor_ref` is split on `;`, each part is parsed with the existing
reference parser, and the verse matches when the book is an exact match
("1 John" never matches "John") and the chapter:verse falls inside the
part's range. Substring matching is explicitly forbidden: the naive
`LIKE '%John 3:16%'` also matches the 1 John 3:16-anchored devotional,
which is wrong.

Ordering: fewest anchors in `anchor_ref` first (a devotional anchored
only to this verse outranks one where it is one of eleven), then source
priority `spurgeon`, `daily_light`, `my_utmost`, `imitation_christ`,
`practice_presence`. Cap 3. Bodies are excerpted at 600 characters with
`truncated` and `full_length`, same as commentary.

Fallback: if no devotional is anchored to the verse, look for
devotionals anchored to other verses in the same chapter within 3
verses, labeled `match_kind: "nearby"`. If none, the list is empty.

### 6.4 Prayer

The liturgy table is keyed by prayer office, not by verse, so prayer
matching is keyword-based and the spec is honest about that: it is
keyword relevance, not semantic understanding.

1. Build a keyword set from the key words' English glosses: lowercase,
   split on non-letters, drop English stopwords (the, to, and, of, a,
   in, on, who, that, with, for, be, as, by, or).
2. Candidate pool: `liturgy` rows in the requested office with
   `kind = 'text'` (actual prayers and collects; rubrics, cues, and
   headings are excluded).
3. Score each candidate by the number of distinct keywords that appear
   as case-insensitive substrings of its text. Substring (not
   whole-word) matching is deliberate: the 1662 text uses archaic
   spellings and inflections ("eternall", "trusting") that whole-word
   matching would miss. The tradeoff is occasional weak hits ("all"
   matching "all assaults"); `matched_keywords` is returned so the
   client can show or audit why a prayer was chosen. Return the top
   scorer; break ties by lowest `seq`.
   Search the 1662 Book of Common Prayer first, then the 1928 US book;
   the first hit wins and `edition` records which one supplied it. (The
   1662 text is public domain worldwide; the 1928 US text is public
   domain in the US with a documented territorial caveat.)
4. If no candidate scores a hit, fall back to the first `kind = 'text'`
   block of the office (the office opening), with
   `match_kind: "office_opening"` and an empty `matched_keywords` list.

Prayer text is served in full (average 130 characters, maximum about
950). `matched_keywords` is returned so the client can show or audit
why a prayer was chosen.

## 7. Attribution

CC BY 4.0 duties attach to three inputs:

- `interlinear_words` rows, sources `step_tahot` and `step_tagnt`
  (Tyndale House, Cambridge, via STEPBible).
- Any key-word `definition` whose `definition_source` is `bdb`,
  `step_tbesh`, `step_tbesg`, `step_tflsj`, or `step_tflsjx`.

The endpoint satisfies attribution by:

- a `sources` array on every response listing each contributing source
  with `id`, `title`, and `rights` (following the `GET /v1/study`
  pattern),
- a `rights_note` carrying the CC BY 4.0 credit text with links to the
  STEPBible data and the CC BY 4.0 deed, plus a record of Phos
  modifications (selection of the critical-text reading, KJV
  versification mapping),
- the CC BY 4.0 note in the endpoint's OpenAPI description,
- a new "Phos Intensive Verse Study" section in
  `docs/public/sources-and-attribution.md`.

Verse texts, cross-references, commentaries, devotionals, and liturgy
are public domain and carry no attribution duty; they appear in
`sources` with their rights status for transparency.

## 8. Error behavior

| Situation | Result |
|---|---|
| Unknown book or unparseable reference | 400 (existing parser convention) |
| Unknown translation code | 400 |
| More than 4 translations | 400 |
| Unknown commentary source | 400 |
| Unknown office | 400 |
| Verse absent from one requested translation | That translation returns `present: false, text: null`; the rest of the response is normal |
| Verse absent from every requested translation | 404 |
| Variant-only interlinear verse | 200 with empty `key_words` and `key_words_note` set (see 5.3) |
| No commentary covers the verse | `commentary: null`, `commentary_source: "none"` |
| No devotional anchored nearby | `devotionals: []` |
| No prayer keyword hit | Office-opening fallback (see 6.4); `prayer` is never null when the office exists |

## 9. Worked example: John 3:16

`GET /v1/verse-study/John/3/16` (default parameters):

```json
{
  "ref": "John 3:16",
  "book": "John",
  "chapter": 3,
  "verse": 16,
  "testament": "NT",
  "translations": [
    {"code": "BSB", "present": true, "text": "For God so loved the world that He gave His one and only Son, that everyone who believes in Him shall not perish but have eternal life."},
    {"code": "KJV", "present": true, "text": "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."},
    {"code": "WEB", "present": true, "text": "For God so loved the world, that he gave his one and only Son, that whoever believes in him should not perish, but have eternal life."}
  ],
  "key_words": [
    {"position": 3, "word": "ἠγάπησεν", "transliteration": "ēgapēsen", "strongs": "G25", "gloss": "to love", "morphology": "V-AAI-3S", "lemma": "ἀγαπάω", "definition": "to love (in a social or moral sense)", "definition_source": "strongs"},
    {"position": 5, "word": "θεὸς", "transliteration": "theos", "strongs": "G2316", "gloss": "God", "morphology": "N-NSM-T", "lemma": "θεός", "definition": "God", "definition_source": "step_tbesg"},
    {"position": 7, "word": "κόσμον,", "transliteration": "kosmon", "strongs": "G2889", "gloss": "world", "morphology": "N-ASM", "lemma": "κόσμος", "definition": "world", "definition_source": "step_tbesg"},
    {"position": 10, "word": "υἱὸν", "transliteration": "huion", "strongs": "G5207", "gloss": "son", "morphology": "N-ASM", "lemma": "υἱός", "definition": "son", "definition_source": "step_tbesg"},
    {"position": 12, "word": "μονογενῆ", "transliteration": "monogenē", "strongs": "G3439", "gloss": "unique", "morphology": "A-ASM", "lemma": "μονογενής", "definition": "unique", "definition_source": "step_tbesg"},
    {"position": 13, "word": "ἔδωκεν,", "transliteration": "edōken", "strongs": "G1325", "gloss": "to give", "morphology": "V-AAI-3S", "lemma": "δίδωμι", "definition": "to give", "definition_source": "step_tbesg"},
    {"position": 15, "word": "πᾶς", "transliteration": "pas", "strongs": "G3956", "gloss": "all", "morphology": "A-NSM", "lemma": "πᾶς", "definition": "all", "definition_source": "step_tbesg"},
    {"position": 17, "word": "πιστεύων", "transliteration": "pisteuōn", "strongs": "G4100", "gloss": "to trust (in)", "morphology": "V-PAP-NSM", "lemma": "πιστεύω", "definition": "to trust (in)", "definition_source": "step_tbesg"},
    {"position": 21, "word": "ἀπόληται", "transliteration": "apolētai", "strongs": "G622", "gloss": "to destroy", "morphology": "V-2AMS-3S", "lemma": "ἀπόλλυμι", "definition": "to destroy", "definition_source": "step_tbesg"},
    {"position": 23, "word": "ἔχῃ", "transliteration": "echē", "strongs": "G2192", "gloss": "to have/be", "morphology": "V-PAS-3S", "lemma": "ἔχω", "definition": "to have/be", "definition_source": "step_tbesg"},
    {"position": 24, "word": "ζωὴν", "transliteration": "zōēn", "strongs": "G2222", "gloss": "life", "morphology": "N-ASF", "lemma": "ζωή", "definition": "life", "definition_source": "step_tbesg"},
    {"position": 25, "word": "αἰώνιον.", "transliteration": "aiōnion", "strongs": "G166", "gloss": "eternal", "morphology": "A-ASF", "lemma": "αἰώνιος", "definition": "eternal", "definition_source": "step_tbesg"}
  ],
  "key_words_note": null,
  "cross_refs": {
    "total": 19,
    "refs": [
      {"ref": "Genesis 22:12", "text": "..."},
      {"ref": "Matthew 9:13", "text": "..."},
      {"ref": "Mark 12:6", "text": "..."},
      {"ref": "Luke 2:14", "text": "..."},
      {"ref": "John 1:14", "text": "..."},
      {"ref": "John 1:18", "text": "..."},
      {"ref": "John 3:15", "text": "..."},
      {"ref": "Romans 5:8", "text": "..."}
    ]
  },
  "commentary": {
    "source": "barnes_nt",
    "source_title": "Barnes' Notes on the New Testament",
    "ref_range": "John 3:16",
    "text": "For God so loved the world ...",
    "truncated": true,
    "full_length": 2176
  },
  "commentary_source": "barnes_nt",
  "devotionals": [
    {
      "source": "my_utmost",
      "source_title": "My Utmost for His Highest",
      "part": "morning",
      "title": "The Abandonment Of God",
      "anchor_ref": "John 3:16",
      "text": "...",
      "truncated": true,
      "full_length": 1234,
      "match_kind": "exact"
    },
    {
      "source": "daily_light",
      "source_title": "Daily Light on the Daily Path",
      "part": "morning",
      "title": "God so loved the world, that he gave his only begotten Son ...",
      "anchor_ref": "John 3:16; 2 Corinthians 5:18-21; 1 John 4:8-11",
      "text": "...",
      "truncated": true,
      "full_length": 1876,
      "match_kind": "exact"
    }
  ],
  "prayer": {
    "office": "morning_prayer",
    "edition": "bcp1662",
    "label": "The second Collect for Peace",
    "speaker": null,
    "text": "The second Collect for Peace. O God who art the Author of peace, and lover of Concord, in knowledge of whom standeth our eternall life, whose service is perfect freedom : defend vs thy humble servants in all assaults of our enemies, that we surely trusting in thy defence, may not fear the power of any Adversaries through the might of Iesus Christ our Lord. Amen.",
    "match_kind": "keyword",
    "matched_keywords": ["love", "god", "all", "trust", "life", "eternal"]
  },
  "sources": [
    {"id": "bsb", "title": "Berean Standard Bible", "rights": "Public Domain"},
    {"id": "kjv", "title": "King James Version", "rights": "Public Domain"},
    {"id": "web", "title": "World English Bible", "rights": "Public Domain"},
    {"id": "step_tagnt", "title": "STEPBible Translators Amalgamated Greek NT", "rights": "CC BY 4.0"},
    {"id": "step_tbesg", "title": "STEPBible Translators Brief Greek Lexicon", "rights": "CC BY 4.0"},
    {"id": "strongs", "title": "Strong's Lexicon", "rights": "Public Domain"},
    {"id": "tsk", "title": "Treasury of Scripture Knowledge", "rights": "Public Domain"},
    {"id": "barnes_nt", "title": "Barnes' Notes on the New Testament", "rights": "Public Domain"},
    {"id": "my_utmost", "title": "My Utmost for His Highest", "rights": "Public Domain"},
    {"id": "daily_light", "title": "Daily Light on the Daily Path", "rights": "Public Domain"},
    {"id": "bcp1662", "title": "Book of Common Prayer, 1662", "rights": "Public Domain"}
  ],
  "rights_note": "Interlinear word data: STEPBible Translators Amalgamated Greek New Testament (https://www.stepbible.org), data created by STEPBible.org based on work at Tyndale House, Cambridge, used under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Key-word definitions: STEPBible Translators Brief Greek Lexicon, same license. Phos modifications: selection of the Nestle-Aland/SBL critical-text reading and mapping to KJV versification. All other texts on this page are public domain."
}
```

Notes on the example: translation texts for BSB/KJV/WEB are the real verses
(the exact strings are resolved at build time from `scripture.db`); the
prayer text shown is the real 1662 "second Collect for Peace" (original
spelling, served as stored), which the keyword matcher finds via
"eternal", "life", "trust", and others. `full_length` values marked
`1234`/`1876` are illustrative; the build test must assert the real ones.

## 10. Test plan

The build must add `api/tests/test_phos_interlinear.py` and keep the
full suite green.

- Shape test on John 3:16 (defaults): 3 translations, all present; 12
  key words in position order; first key word is `ἠγάπησεν` / G25;
  `cross_refs.total == 19` with 8 refs; `commentary_source ==
  "barnes_nt"`; at least one devotional with `match_kind == "exact"`;
  prayer present with `match_kind` in `("keyword", "office_opening")`;
  `sources` includes `step_tagnt` with rights `CC BY 4.0`.
- Genesis 1:1: 5 key words (preposition+noun compounds kept,
  article-only words excluded); `commentary_source ==
  "keil_delitzsch"`.
- Morphology rule unit tests: Greek `ADV` excluded, `A-ASM` included;
  Hebrew `HTd/Ncmpa` included, `HC/To` excluded.
- Devotional disambiguation: John 3:16 response must not contain the
  devotional anchored to 1 John 3:16 ("Hereby perceive we the love of
  God ...").
- Variant-only verse: Mark 16:9 returns 200, `key_words == []`, and
  `key_words_note` names the `/v1/interlinear` endpoint.
- Error tests: unknown book 400; unknown translation code 400; five
  translations 400; unknown commentary source 400; unknown office 400;
  verse missing from one translation gives `present: false` for that
  translation; reference missing everywhere 404.
- Attribution test: every `definition_source` in `key_words` appears in
  `sources`; `rights_note` names STEPBible and links the CC BY 4.0 deed.
- Auth test: no API key is a 401/403 per existing convention.
- OpenAPI regeneration includes the new path with the attribution note
  in its description.

## 11. Open questions for Jeremiah (answered 2026-09-20)

1. Public name: LOCKED as "Phos Intensive Verse Study" with endpoint
   `/v1/verse-study/{book}/{chapter}/{verse}` (Jeremiah, 2026-09-20).
   Clarity over poetry.
2. Devotional nearby fallback: KEEP. Show nearby devotionals labeled
   `nearby` when nothing is anchored exactly (Jeremiah, 2026-09-20).
3. Prayer default office: morning. Keep fixed and deterministic
   (Jeremiah, 2026-09-20).
4. Strong's OCR artifacts: CLEAN FIRST. Schedule the cleanup pass before
   building the endpoint (Jeremiah, 2026-09-20).
5. Commentary: excerpts from all eight sources like `/v1/study` does,
   not one curated source (Jeremiah, 2026-09-20).

## 12. Build checklist (for the implementing agent)

1. Add Pydantic models mirroring section 3.
2. Implement the key-word selector exactly per 5.1; unit-test the
   morphology rule before wiring the endpoint.
3. Implement devotional anchor parsing with the existing reference
   parser; add the 1 John / John disambiguation regression test first.
4. Implement prayer keyword matching per 6.4; log matched keywords.
5. Wire `GET /v1/verse-study/{book}/{chapter}/{verse}` following
   the `get_interlinear` handler pattern (API key dependency, 400/404
   conventions).
6. Regenerate `api/openapi.json`; confirm the path and the attribution
   note appear.
7. Add the "Phos Intensive Verse Study" section to
   `docs/public/sources-and-attribution.md` and a row to
   `docs/public/coverage-and-availability.md`.
8. Write `api/tests/test_phos_interlinear.py` per section 10; run the
   full suite independently.
9. Update `PLAN.md`, `BUILD_LOG.md`; write
   `verification/v2/verse-study-build-report.md`.
10. No database writes: this endpoint reads `scripture.db` and
    `study.db` only.
