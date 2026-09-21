# Phos (Dexia Bible API) - Public API Reference

Version 1.0.0. The API is served by a single FastAPI app (`api/app.py`). The full
machine-readable contract is `api/openapi.json` (OpenAPI 3.1.0, 26 paths).

Base URL is wherever you run the service (locally: `http://127.0.0.1:8000`).

## Authentication

Every `/v1/*` endpoint requires a single API key sent in the `X-API-Key`
request header. There is no OAuth, no bearer token, no username/password.

```bash
curl -H "X-API-Key: your-secret-key" \
  "http://127.0.0.1:8000/v1/passage?ref=John+3:16&translation=BSB"
```

Server-side behavior (from `api/app.py`, `require_api_key`):

- The key is read from the `PHOS_API_KEY` environment variable. The server
  refuses to start without it.
- The supplied key is compared with `hmac.compare_digest`, a constant-time
  comparison.
- A missing or wrong key returns HTTP 401 with the exact body detail:
  `"Invalid or missing API key. Send it in the X-API-Key header."`

`/health` is the only endpoint that works without a key.

## Rate limiting

The code has **no rate limiting**. No throttles, quotas, or per-key budgets are
implemented in the service.

## Translations

14 translation codes, per `api/translations.py`. `BSB` is the default and is
used whenever the `translation` parameter is omitted. All codes are
case-insensitive at the API boundary (the server uppercases them).

| Code | Name | Notes |
|---|---|---|
| BSB | Berean Standard Bible | Default. Public domain (dedicated 2023-04-30) |
| KJV | King James Version | Public domain; within the UK, Crown copyright applies to the Authorized Version |
| WEB | World English Bible | Public domain; omits 7 KJV verse keys |
| ASV | American Standard Version | Public domain; omits 16 KJV verse keys |
| YLT | Young's Literal Translation | Public domain |
| DARBY | Darby Translation | Public domain |
| DRB | Douay-Rheims Bible (1899 American Edition) | 73 books; Vulgate Psalm numbering |
| GENEVA | Geneva Bible (1599) | Original 1599 spelling preserved |
| AKJV | American King James Version | Rights caveat documented in `translations.py` (author's 1999 PD dedication vs a getBible aggregator label) |
| OEB | Open English Bible (US spelling) | Partial: 44 books (full NT + parts of OT) |
| WEBSTER | Webster Bible | Noah Webster's 1833 KJV revision |
| WEYMOUTH | Weymouth New Testament | NT only (27 books); public domain in the USA |
| LXX2012 | Septuagint in English 2012 | Septuagint versification (Greek Psalm numbering, 151 psalms); 15 deuterocanonical books |

Per-translation rights metadata (copyright text, attribution text, edition,
source) is served by `GET /v1/translations`.

## Error conventions

- `400` - unknown translation (`"Unknown translation 'X'. Valid translations: ..."`),
  unparseable or out-of-range reference, invalid date or day, unknown
  commentary/lexicon/dictionary/devotional source, unknown office or edition,
  empty search query, blank dictionary term.
- `401` - missing or wrong `X-API-Key` header (every `/v1/*` endpoint).
- `404` - a valid reference whose verse key is absent from the requested
  translation; unknown topic id, mood, reading plan, Strong's number, or
  dictionary term.
- `422` - FastAPI request validation failures (e.g. `limit` outside 1-100).

WEB and ASV genuinely omit some KJV verse keys (7 and 16 respectively, e.g.
Acts 8:37). This is data, not an error: `/v1/passage` and `/v1/cross-refs`
return 404 for such keys, `/v1/compare` returns `null` texts, and the gap is
always described in the response or detail message.

## Meta

### GET /health

Auth: **none required**. Status, translation codes, and the total verse row
count across all translations (a live `COUNT(*)` over the verses table, not a
hardcoded number).

Response:

```json
{ "status": "ok", "translations": ["BSB", "KJV", ...], "verse_count": 124369 }
```

### GET /v1/translations

Auth: required. Per-translation metadata and rights: `code`, `name`,
`edition`, `source`, `retrieved`, `default` (bool), `verse_count`, `rights`
(`status`, `copyright`, `attribution`), and optional `notes`.

### GET /v1/books

Auth: required. The 66 canonical books in order for a translation, each with
`book_order`, `book`, `chapters`.

Parameters:

- `translation` (optional, string, default `"BSB"`) - translation code.

Errors: `400` unknown translation.

## Scripture

Reference forms accepted everywhere a `ref` parameter appears: `John 3:16`,
`Ps 23:1-3`, `Romans 8:28-30`, `John 14` (whole chapter), `Genesis 1-2`
(chapter range), `John 3:16-4:2` (multi-chapter range), `Ps 23:1,3,5` (comma
list). Book aliases are accepted (`Ps`, `Psalm`, `Psalms`; `Song of Solomon`
-> `Song of Songs`; `1John` -> `1 John`).

A verse object is always shaped `{book, chapter, verse, text}`.

### GET /v1/passage

Auth: required. Returns the verses for a reference in canonical order.

Parameters:

- `ref` (required, string) - the reference to look up.
- `translation` (optional, string, default `"BSB"`) - translation code.

Response: `{ref, translation, book, verses}`.

Errors: `400` unparseable or out-of-range reference; `404` valid verse key
not present in the translation; `400` unknown translation.

### GET /v1/compare

Auth: required. Renders the same reference in each requested translation,
side by side.

Parameters:

- `ref` (required, string).
- `translations` (optional, string, default `"BSB,KJV"`) - comma-separated
  codes; duplicates are removed; each code must be valid.

Response: `{ref, book, translations, verses, note}`, where each verse is
`{chapter, verse, texts: {CODE: text-or-null}}`. A `null` text means the verse
key is genuinely absent from that translation (reported, not an error).

Errors: `400` unknown translation code; `404` when the reference is present in
none of the requested translations.

### GET /v1/search

Auth: required. Full-text search over verse text using the FTS5 index with
porter stemming. Terms are ANDed together (punctuation is stripped first).
Results are ranked best-first and each hit includes an `<em>`-highlighted
snippet.

Parameters:

- `q` (required, string) - search terms.
- `translation` (optional, string, default `"BSB"`).
- `limit` (optional, integer, 1-100, default `20`) - max results.

Response: `{q, translation, count, hits}`, hits are
`{book, chapter, verse, text, snippet}`.

Errors: `400` if the query is empty after punctuation is removed; `422` if
`limit` is outside 1-100; `400` unknown translation.

### GET /v1/verse-of-day

Auth: required. Deterministic verse for a calendar date: SHA-256 of
`'YYYY-MM-DD|TRANSLATION'` selects an offset into the translation's canonical
verse order. Same date and translation always return the same verse.

Parameters:

- `translation` (optional, string, default `"BSB"`).
- `day` (optional, string `YYYY-MM-DD`, default today).

Response: `{date, translation, book, chapter, verse, text}`.

Errors: `400` invalid date format; `400` unknown translation.

## Topics and moods

The curated data lives in `api/data/topics.json`: 64 topics, 14 moods
(counts verified from the file, not hardcoded).

### GET /v1/topics

Auth: required. The full curated topic list (peace, anxiety, gratitude, ...),
each with `id`, `label`, `description`, and `moods` (the moods it speaks to).
No parameters. Fetch a topic's verses at `GET /v1/topics/{topic_id}`.

### GET /v1/topics/{topic_id}

Auth: required. The topic's representative verses resolved to full text.

Parameters: `topic_id` (path, required, string). `translation` (optional,
default `"BSB"`).

Response: `{id, label, description, moods, translation, verses}`.

Errors: `404` unknown topic.

### GET /v1/moods

Auth: required. The mood list (anxious, lonely, grateful, ...), each with
`mood`, `label`, `description`, and `topics` (topic ids that speak to it). No
parameters. Fetch a mood's verses at `GET /v1/moods/{mood}`.

### GET /v1/moods/{mood}

Auth: required. Maps a mood to its topics, each with its verses resolved to
full text. The mood value is lowercased before matching, so `Anxious` works.

Parameters: `mood` (path, required, string). `translation` (optional, default
`"BSB"`).

Response: `{mood, label, description, translation, topics: [{id, label, description, verses}]}`.

Errors: `404` unknown mood.

## Reading plans

Four plans, generated programmatically from the corpus's chapter structure
(ids, days, and chapter counts verified from `api/data/plans.json`):

| Plan id | Name | Days | Chapters |
|---|---|---|---|
| `bible-in-a-year` | Bible in a Year | 365 | 1189 |
| `new-testament-90` | New Testament in 90 Days | 90 | 260 |
| `psalms-proverbs-31` | Psalms & Proverbs in 31 Days | 31 | 181 |
| `gospels-30` | The Gospels in 30 Days | 30 | 89 |

Progress check-ins are stored locally in `api/data/progress.db` (path
overridable with `PHOS_PROGRESS_PATH`). The store holds **checkmarks only**:
`plan_id`, `start_date`, `day`, and a UTC timestamp - no scripture text.
Records are keyed by `(plan_id, start_date, day)`; because v1 uses a single
API key, one reader's progress per plan plus start date is the whole model.

### GET /v1/reading-plans

Auth: required. Plan list: `{id, name, description, days, total_chapters}`
per plan. No parameters.

### GET /v1/reading-plans/{plan_id}

Auth: required. The full day-by-day schedule:
`{id, name, description, days, total_chapters, schedule: [{day, refs}]}`,
each day's chapter refs in canonical order.

Errors: `404` unknown plan id.

### GET /v1/reading-plans/{plan_id}/today

Auth: required. Stateless daily reading: computes the current plan day as
`day = (today - start_date) + 1` and returns that day's passages with full
verse text. No login, no stored state.

Parameters:

- `plan_id` (path, required).
- `start_date` (required, string `YYYY-MM-DD`) - the date the plan started.
- `translation` (optional, default `"BSB"`).

Response: `{plan_id, plan_name, start_date, date, day, total_days, passages}`,
where each passage is `{ref, verses}`.

Errors: `404` unknown plan; `400` bad `start_date`; `400` if the plan has not
started yet; `400` with a "finished" message once the plan's days are complete.

### POST /v1/reading-plans/{plan_id}/checkin

Auth: required. Marks one plan day as read. Idempotent: checking in the same
day twice keeps the earlier record replaced by a new timestamp (INSERT OR
REPLACE), so the operation is safe to repeat.

Request body (JSON, required):

```json
{ "start_date": "2026-01-01", "day": 1 }
```

- `start_date` (required, string `YYYY-MM-DD`).
- `day` (required, integer, 1 to the plan's day count).

Response: `{plan_id, start_date, day, checked_in_at}` (UTC ISO-8601 timestamp).

Errors: `404` unknown plan; `400` bad date; `400` day outside 1..plan days.

### GET /v1/reading-plans/{plan_id}/progress

Auth: required. Completed days and completion percent from the local check-in
store.

Parameters: `plan_id` (path, required). `start_date` (required, `YYYY-MM-DD`).

Response: `{plan_id, start_date, total_days, completed_days, completed_count, percent}`
- `completed_days` is a sorted list of checked-in day numbers;
- `percent` is rounded to one decimal place.

Errors: `404` unknown plan; `400` bad date.

## Study resources

All study texts (commentaries, cross-references, devotionals, liturgies) are
public domain. Per-source rights metadata ships in responses. Lexicon entries
carry their source's own rights: Strong's (1890) is public domain; BDB
(OpenScriptures) and the four STEPBible lexicons are CC BY 4.0 and must be
attributed as shown in the response.

### GET /v1/study

Auth: required. The "route here first" bundle: the passage in full text, TSK
cross-references per verse, and commentary excerpts from all eight commentary
sources whose verse ranges cover the reference (whole-chapter comments are
included).

Parameters: `ref` (required), `translation` (optional, default `"BSB"`).

Response:

```json
{
  "ref": "Psalms 23:1",
  "translation": "BSB",
  "book": "Psalms",
  "verses": [{"book": "Psalms", "chapter": 23, "verse": 1, "text": "..."}],
  "cross_refs": [{"chapter": 23, "verse": 1, "total": 42, "refs": ["Ezekiel 34:11", ...]}],
  "commentaries": [{"source": "matthew_henry", "source_title": "...", "ref_range": "Psalms 23", "text": "...", "truncated": true, "full_length": 2148}],
  "sources": [{"id": "tsk", "title": "Treasury of Scripture Knowledge", "rights": "Public Domain"}],
  "rights_note": "All commentary, cross-reference, devotional, and liturgy texts served here are public domain."
}
```

- Cross-references are capped at 25 per verse; `total` gives the uncapped count.
- Commentary text is an excerpt truncated at 600 characters (`truncated`
  flags this; `full_length` is the original length).
- `sources` lists only the sources actually used, with their rights.

Errors: `400` bad reference; `404` reference not present in the translation.

### GET /v1/verse-study/{book}/{chapter}/{verse}

Auth: required. Phos Intensive Verse Study: everything for one verse in one
call. The verse in up to four translations; the most important
original-language words (nouns, verbs, adjectives) with transliteration,
Strong's number, morphology, and a short lexicon definition; the top 8
cross-references in canonical order with a total count; commentary excerpts
from all eight commentary sources; up to three devotionals anchored to the
verse; and a related prayer from the Book of Common Prayer.

Parameters:

- `translations` (optional, default `"BSB,KJV,WEB"`) - comma-separated
  translation codes, max 4. A translation missing the verse returns
  `present: false` instead of failing the request.
- `office` (optional, default `"morning"`) - `morning` or `evening`; selects
  which prayer office the prayer is drawn from.

Response:

```json
{
  "ref": "John 3:16",
  "book": "John",
  "chapter": 3,
  "verse": 16,
  "testament": "NT",
  "translations": [{"code": "BSB", "present": true, "text": "..."}],
  "key_words": [{"position": 3, "word": "ἠγάπησεν", "transliteration": "ēgapēsen", "strongs": "G25", "gloss": "to love", "morphology": "V-AAI-3S", "lemma": "ἀγαπάω", "definition": "to love", "definition_source": "step_tbesg"}],
  "key_words_note": null,
  "cross_refs": {"total": 19, "refs": [{"ref": "Romans 5:8", "text": "..."}]},
  "commentaries": [{"source": "barnes_nt", "source_title": "...", "ref_range": "John 3:16", "text": "...", "truncated": true, "full_length": 2176}],
  "devotionals": [{"source": "my_utmost", "source_title": "...", "part": "morning", "title": "...", "anchor_ref": "John 3:16", "text": "...", "truncated": true, "full_length": 1234, "match_kind": "exact"}],
  "prayer": {"office": "morning_prayer", "edition": "bcp1662", "label": "The second Collect for Peace", "speaker": null, "text": "...", "match_kind": "keyword", "matched_keywords": ["love", "god", "life"]},
  "sources": [{"id": "step_tagnt", "title": "STEPBible TAGNT (Translators Amalgamated Greek NT)", "rights": "CC BY 4.0"}],
  "rights_note": "Interlinear word data: ... used under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). ..."
}
```

- Key words are capped at 12, in verse position order. `definition_source`
  names the lexicon that supplied the definition and always appears in
  `sources`.
- The 42 KJV verses absent from the critical text (e.g. Mark 16:9-20,
  John 7:53-8:11) return `key_words: []` with `key_words_note` pointing to
  `GET /v1/interlinear/{book}/{chapter}/{verse}` for the
  variant-tradition readings.
- Devotional `match_kind` is `"exact"` when anchored to the verse,
  `"nearby"` when anchored to another verse in the same chapter within 3
  verses. Prayer `match_kind` is `"keyword"` when matched by key-word
  overlap, `"office_opening"` when no keyword hit (prayer matching is
  keyword relevance, not semantic understanding).
- Cross-reference texts use the first requested translation.
- The interlinear words and some key-word definitions are CC BY 4.0
  (STEPBible, BDB); attribution ships in `sources` and `rights_note` on
  every response.

Errors: `400` unknown book, bad reference, unknown translation code, more
than 4 translations, or unknown office; `404` verse absent from every
requested translation.

### GET /v1/commentary

Auth: required. Full-text commentary entries whose verse range covers the
requested reference (whole-chapter comments match verse queries). Eight
sources:

| Source id | Title |
|---|---|
| `matthew_henry` | Matthew Henry, Complete Commentary on the Whole Bible |
| `jfb` | Jamieson-Fausset-Brown |
| `barnes_nt` | Barnes NT |
| `gill` | Gill |
| `clarke` | Clarke |
| `calvin` | Calvin |
| `keil_delitzsch` | Keil & Delitzsch |
| `treasury_of_david` | Treasury of David |

Parameters:

- `ref` (required) - verse or chapter (e.g. `Gen 1:1`, `Ps 23`).
- `source` (optional) - one source id; omit to search all eight.
- `translation` (optional, default `"BSB"`).

Response: array of
`{source, source_title, ref_range, text, truncated, full_length}`.
`ref_range` reads like `Psalms 23` (whole chapter), `Genesis 1:1`, or
`Genesis 1:1-2`; here `text` is the full entry and `truncated` is false.

Errors: `400` bad reference or unknown source id.

### GET /v1/cross-refs

Auth: required. Treasury of Scripture Knowledge cross-references for each
verse in the reference, in canonical order. The full list per verse (no 25-cap
here).

Parameters: `ref` (required), `translation` (optional, default `"BSB"`).

Response: array of `{chapter, verse, total, refs}` where `refs` are strings
like `"Ezekiel 34:11"`.

Errors: `400` bad reference; `404` reference not present in the translation.

### GET /v1/devotional

Auth: required. The devotional entries for a calendar date. Spurgeon and Daily
Light provide morning and evening entries; My Utmost for His Highest, The
Practice of the Presence of God, and The Imitation of Christ provide a single
reading (`evening` is null). Anchor references are resolved to verse text in
the requested translation. The February 29 entry is served only on an actual
February 29; in non-leap years, dates after February 28 shift so March 1
reads March 1's entry.

Parameters:

- `date` (optional, string `YYYY-MM-DD`, default today).
- `source` (optional, default `"spurgeon"`). Valid values: `spurgeon`
  (Morning and Evening), `daily_light` (Daily Light on the Daily Path),
  `my_utmost` (My Utmost for His Highest), `practice_presence` (The Practice
  of the Presence of God), `imitation_christ` (The Imitation of Christ).
- `translation` (optional, default `"BSB"`).

Response: `{source, source_title, date, day, morning, evening}`, where each
entry is `{title, anchor_ref, anchor_verses, body}` and `day` is the
leap-year day-of-year number used to look up the entry.

Errors: `400` bad date or unknown source.

### GET /v1/prayer

Auth: required. A full Morning or Evening Prayer office from the 1662 or
1928 (US) Book of Common Prayer, as ordered liturgy blocks (sentences,
confession, psalms, lessons, creed, collects, ...). Both editions are public
domain.

Parameters:

- `office` (optional, default `"morning"`) - `morning` or `evening`.
- `edition` (optional, default `"1662"`) - `1662` or `1928`.

Response: `{edition, edition_title, office, blocks}`, blocks are
`{section, label, speaker, kind, text}`.

Errors: `400` unknown office or edition.

### GET /v1/memory-pack

Auth: required. A numbered memorization pack: the curated topic's verses
resolved to full text in the requested translation, in order, up to 10
verses.

Parameters: `topic` (required, topic id e.g. `peace`),
`translation` (optional, default `"BSB"`).

Response: `{topic, label, translation, count, verses}`, verses are
`{n, ref, book, chapter, verse, text}` (n = 1-based order).

Errors: `404` unknown topic.

### GET /v1/word/sources

Auth: required. Every lexicon behind `/v1/word`: `{id, title, rights,
rights_basis, attribution, entries}` per source, plus the rights and
attribution metadata each source requires. Strong's (1890) is public domain;
BDB (OpenScriptures) and the four STEPBible lexicons are CC BY 4.0.

### GET /v1/word

Auth: required. Lexicon entries for one Strong's number, case-insensitive,
leading zeros accepted (e.g. `G3056`, `H430`, `g0074` all canonicalize).

Parameters:

- `number` (required, string) - Greek (`G` + digits) or Hebrew (`H` + digits).
- `source` (optional) - one lexicon source id; omit for all sources. Valid
  values: `strongs`, `bdb`, `step_tbesh`, `step_tbesg`, `step_tflsj`,
  `step_tflsjx`.

Response: `{number, language, entries}` where `language` is `greek` or
`hebrew` and each entry is
`{number, language, lemma, transliteration, definition, gloss, source}` with
`source = {id, title, rights, attribution}`. Strong's Greek covers 89.1% of
G1-G5624; STEPBible's Greek lexicons fill the gaps.

Errors: `400` invalid Strong's number or unknown source; `404` no lexicon
entry for the number.

### GET /v1/dictionary/sources

Auth: required. Every dictionary behind `/v1/dictionary`:
`{id, title, rights, rights_basis, attribution, entries}` per source. All four
are public domain: Easton's (1897), ISBE 1915, Nave's Topical Bible (1896),
Torrey's New Topical Textbook (1897).

### GET /v1/dictionary

Auth: required. Dictionary entries for one term (e.g. `Aaron`, `Faith`),
case-insensitive.

Parameters:

- `term` (required, string) - must not be blank.
- `source` (optional) - one dictionary source id; omit for all sources. Valid
  values: `easton`, `isbe`, `naves`, `torrey`.

Response: `{term, entries}`, each entry is `{term, text, source}` with
`source = {id, title, rights, attribution}`.

Errors: `400` blank term or unknown source; `404` no dictionary entry for the
term.
