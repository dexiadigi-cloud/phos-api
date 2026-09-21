# Phos API - Usage Examples

Five core flows, each in curl, Python, and JavaScript. Every response below
was captured from a live run against the local API on 2026-09-20; nothing
here is invented. Long bodies are trimmed where noted.

**Setup (all snippets assume this):**

- The server is running on `http://127.0.0.1:8000` (see `api/README.md`).
- Every `/v1/*` endpoint needs the key in the `X-API-Key` header.
  `/health` needs no key.
- Bash examples read the key from `$PHOS_API_KEY`.

```bash
export PHOS_API_KEY=your-api-key
export PHOS_BASE=http://127.0.0.1:8000
```

Python examples use only the standard library (`urllib`). JavaScript
examples use the built-in `fetch` (Node 18+, or any modern browser).

A shared helper is used in the Python and JavaScript snippets:

```python
# python helper
import json, urllib.request, urllib.parse

BASE = "http://127.0.0.1:8000"
HEADERS = {"X-API-Key": "your-api-key"}  # your own key from the operator

def get(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.load(r)
```

```javascript
// javascript helper
const BASE = "http://127.0.0.1:8000";
const HEADERS = { "X-API-Key": "your-api-key" }; // your own key from the operator

async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}?${qs}`, { headers: HEADERS });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}
```

---

## 1. Fetch a passage

`GET /v1/passage?ref=John+3:16&translation=BSB`

```bash
curl -s -H "X-API-Key: $PHOS_API_KEY" \
  "$PHOS_BASE/v1/passage?ref=John+3:16&translation=BSB"
```

```python
d = get("/v1/passage", {"ref": "John 3:16", "translation": "BSB"})
v = d["verses"][0]
print(f'{d["ref"]} ({d["translation"]}): {v["text"]}')
```

```javascript
const d = await get("/v1/passage", { ref: "John 3:16", translation: "BSB" });
const v = d.verses[0];
console.log(`${d.ref} (${d.translation}): ${v.text}`);
```

**Response** (verbatim):

```json
{
  "ref": "John 3:16",
  "translation": "BSB",
  "book": "John",
  "verses": [
    {
      "book": "John",
      "chapter": 3,
      "verse": 16,
      "text": "For God so loved the world that He gave His one and only Son, that everyone who believes in Him shall not perish but have eternal life."
    }
  ]
}
```

`ref` accepts ranges, whole chapters, and aliases: `Ps 23:1-3`, `John 14`,
`Genesis 1-2`, `Romans 8:28-30`, `Ps 23:1,3,5`.

---

## 2. Run a word search

`GET /v1/search?q=lovingkindness&translation=KJV&limit=5`

FTS5 full-text search with relevance ranking. `text` is the verse;
`snippet` highlights matches with `<em>` tags.

```bash
curl -s -H "X-API-Key: $PHOS_API_KEY" \
  "$PHOS_BASE/v1/search?q=lovingkindness&translation=KJV&limit=5"
```

```python
d = get("/v1/search", {"q": "lovingkindness", "translation": "KJV", "limit": 5})
for h in d["hits"]:
    print(f'{h["book"]} {h["chapter"]}:{h["verse"]} - {h["text"]}')
```

```javascript
const d = await get("/v1/search", {
  q: "lovingkindness",
  translation: "KJV",
  limit: 5,
});
for (const h of d.hits) {
  console.log(`${h.book} ${h.chapter}:${h.verse} - ${h.text}`);
}
```

**Response** (verbatim):

```json
{
  "q": "lovingkindness",
  "translation": "KJV",
  "count": 5,
  "hits": [
    {
      "book": "Psalms",
      "chapter": 63,
      "verse": 3,
      "text": "Because thy lovingkindness is better than life, my lips shall praise thee.",
      "snippet": "Because thy <em>lovingkindness</em> is better than life, my lips shall praise thee."
    },
    {
      "book": "Psalms",
      "chapter": 88,
      "verse": 11,
      "text": "Shall thy lovingkindness be declared in the grave? or thy faithfulness in destruction?",
      "snippet": "Shall thy <em>lovingkindness</em> be declared in the grave? or thy faithfulness in..."
    },
    {
      "book": "Psalms",
      "chapter": 92,
      "verse": 2,
      "text": "To shew forth thy lovingkindness in the morning, and thy faithfulness every night,",
      "snippet": "To shew forth thy <em>lovingkindness</em> in the morning, and thy faithfulness every..."
    },
    {
      "book": "Psalms",
      "chapter": 26,
      "verse": 3,
      "text": "For thy lovingkindness is before mine eyes: and I have walked in thy truth.",
      "snippet": "For thy <em>lovingkindness</em> is before mine eyes: and I have walked in..."
    },
    {
      "book": "Psalms",
      "chapter": 48,
      "verse": 9,
      "text": "We have thought of thy lovingkindness, O God, in the midst of thy temple.",
      "snippet": "We have thought of thy <em>lovingkindness</em>, O God, in the midst of..."
    }
  ]
}
```

---

## 3. Get cross-references

`GET /v1/cross-refs?ref=Ps+23:1`

Treasury of Scripture Knowledge (TSK) cross-references per verse, in
canonical order. `total` is the full ref count; the listing above shows all
of them here.

```bash
curl -s -H "X-API-Key: $PHOS_API_KEY" \
  "$PHOS_BASE/v1/cross-refs?ref=Ps+23:1"
```

```python
refs = get("/v1/cross-refs", {"ref": "Ps 23:1"})
for v in refs:
    print(f'Ps 23:{v["verse"]}: {v["total"]} refs, first 5: {v["refs"][:5]}')
```

```javascript
const refs = await get("/v1/cross-refs", { ref: "Ps 23:1" });
for (const v of refs) {
  console.log(`Ps 23:${v.verse}: ${v.total} refs, first 5: ${v.refs.slice(0, 5)}`);
}
```

**Response** (verbatim, all 32 refs shown):

```json
[
  {
    "chapter": 23,
    "verse": 1,
    "total": 32,
    "refs": [
      "Psalms 34:9",
      "Psalms 34:10",
      "Psalms 79:13",
      "Psalms 80:1",
      "Psalms 84:11",
      "Isaiah 40:11",
      "Jeremiah 23:3",
      "Jeremiah 23:4",
      "Ezekiel 34:11",
      "Ezekiel 34:12",
      "Ezekiel 34:23",
      "Ezekiel 34:24",
      "Micah 5:2",
      "Micah 5:4",
      "Matthew 6:33",
      "Luke 12:30",
      "Luke 12:31",
      "Luke 12:32",
      "John 10:11",
      "John 10:14",
      "John 10:27",
      "John 10:28",
      "John 10:29",
      "John 10:30",
      "Romans 8:32",
      "Philippians 4:19",
      "Hebrews 13:5",
      "Hebrews 13:6",
      "Hebrews 13:20",
      "1 Peter 2:25",
      "1 Peter 5:4",
      "Revelation 7:17"
    ]
  }
]
```

---

## 4. Look up a Strong's lexicon entry

`GET /v1/word?source=strongs&number=H430`

**Check the source IDs first** with `GET /v1/word/sources`. The valid
`source` values are `strongs`, `bdb`, `step_tbesh`, `step_tbesg`,
`step_tflsj`, `step_tflsjx`. **Note:** the query parameter is `source`
(singular) - the examples below use the real signature from `api/app.py`.

`number` takes `H`/`G` plus digits, case-insensitive, leading zeros
accepted (`h0430` works). Omit `source` to get entries from every lexicon
that has the number.

```bash
curl -s -H "X-API-Key: $PHOS_API_KEY" \
  "$PHOS_BASE/v1/word?source=strongs&number=H430"
```

```python
d = get("/v1/word", {"source": "strongs", "number": "H430"})
e = d["entries"][0]
print(f'{d["number"]} ({d["language"]}) - {e["source"]["title"]}')
print(e["definition"])
print("Rights:", e["source"]["rights"])
```

```javascript
const d = await get("/v1/word", { source: "strongs", number: "H430" });
const e = d.entries[0];
console.log(`${d.number} (${d.language}) - ${e.source.title}`);
console.log(e.definition);
console.log("Rights:", e.source.rights);
```

**Response** (verbatim):

```json
{
  "number": "H430",
  "language": "hebrew",
  "entries": [
    {
      "number": "H430",
      "language": "hebrew",
      "lemma": null,
      "transliteration": null,
      "definition": "<-PN  'eloabb,  el-o'-ah;  prob.  prol.  (emphat.) from  410;  a  deity  or  the  Deity:\u2014 God' god.    See  430. 434.  ?13N  'eluwl,  el-ool';  for  457;  good  for  noth-",
      "gloss": null,
      "source": {
        "id": "strongs",
        "title": "Strong's Greek and Hebrew Dictionaries (1890)",
        "rights": "Public domain",
        "attribution": "Strong's Greek and Hebrew Dictionaries (1890) by James Strong; public domain text via Internet Archive (CC0)."
      }
    }
  ]
}
```

Every entry carries its source's rights and attribution. With `source`
omitted, H430 returns 5 entries (BDB, two STEPBible TBESH senses, and the
Strong's OCR entry shown above).

---

## 5. Fetch a devotional

`GET /v1/devotional?date=2026-09-20&source=spurgeon`

Morning + evening reading from Spurgeon or Daily Light, with the anchor
verse text included. The Feb 29 entry is served only on a real Feb 29.

```bash
curl -s -H "X-API-Key: $PHOS_API_KEY" \
  "$PHOS_BASE/v1/devotional?date=2026-09-20&source=spurgeon"
```

```python
d = get("/v1/devotional", {"date": "2026-09-20", "source": "spurgeon"})
m = d["morning"]
print(f'{d["source_title"]} - day {d["day"]} ({d["date"]})')
print("Morning:", m["title"], "-", m["anchor_ref"])
print(m["body"][:120] + "...")
print("Evening:", d["evening"]["title"], "-", d["evening"]["anchor_ref"])
```

```javascript
const d = await get("/v1/devotional", {
  date: "2026-09-20",
  source: "spurgeon",
});
const m = d.morning;
console.log(`${d.source_title} - day ${d.day} (${d.date})`);
console.log("Morning:", m.title, "-", m.anchor_ref);
console.log(m.body.slice(0, 120) + "...");
console.log("Evening:", d.evening.title, "-", d.evening.anchor_ref);
```

**Response** (bodies trimmed after the first ~350 characters; marked):

```json
{
  "source": "spurgeon",
  "source_title": "C. H. Spurgeon, Morning and Evening (1866)",
  "date": "2026-09-20",
  "day": 264,
  "morning": {
    "title": "The sword of the Lord, and of Gideon.",
    "anchor_ref": "Judges 7:20",
    "anchor_verses": [
      {
        "book": "Judges",
        "chapter": 7,
        "verse": 20,
        "text": "The three companies blew their horns and shattered their jars. Holding the torches in their left hands and the horns in their right hands, they shouted, \u201cA sword for the LORD and for Gideon!\u201d"
      }
    ],
    "body": "Gideon ordered his men to do two things: covering up a torch in an earthen pitcher, he bade them, at an appointed signal, break the pitcher and let the light shine, and then sound with the trumpet, crying, \"The sword of the Lord, and of Gideon! the sword of the Lord, and of Gideon!\" This is precisely what all Christians must do. First, you must shine; break the pitcher which conceals your light; throw aside the bushel which has been hiding your candle, and shine. Let your light shine before men; let your good works be such, that when men look upon you, they shall know that you have been with Jesus. [trimmed: body continues ~1,450 more characters]"
  },
  "evening": {
    "title": "In the evening withhold not thy hand.",
    "anchor_ref": "Ecclesiastes 11:6",
    "anchor_verses": [
      {
        "book": "Ecclesiastes",
        "chapter": 11,
        "verse": 6,
        "text": "Sow your seed in the morning, and do not rest your hands in the evening, for you do not know which will succeed, whether this or that, or if both will equally prosper."
      }
    ],
    "body": "In the evening of the day opportunities are plentiful: men return from their labour, and the zealous soul-winner finds time to tell abroad the love of Jesus. Have I no evening work for Jesus? If I have not, let me no longer withhold my hand from a service which requires abundant labour. Sinners are perishing for lack of knowledge; he who loiters may find his skirts crimson with the blood of souls. [trimmed: body continues ~1,500 more characters]"
  }
}
```

---

## 6. Study one verse in depth

`GET /v1/verse-study/John/3/16`

Phos Intensive Verse Study: everything for one verse in one call. The verse
in up to four translations, the key original-language words with meanings,
top cross-references, commentary excerpts from all eight sources,
devotionals anchored to the verse, and a related prayer.

```bash
curl -s -H "X-API-Key: $PHOS_API_KEY" \
  "$PHOS_BASE/v1/verse-study/John/3/16"
```

```python
d = get("/v1/verse-study/John/3/16")
print(d["ref"], "-", d["translations"][0]["text"][:60] + "...")
print("Key words:", len(d["key_words"]))
for kw in d["key_words"][:4]:
    print(f'  {kw["word"]} ({kw["strongs"]}): {kw["gloss"]} - {kw["definition"]}')
print("Cross-refs:", d["cross_refs"]["total"])
print("Prayer:", d["prayer"]["label"], f'({d["prayer"]["match_kind"]})')
```

```javascript
const d = await get("/v1/verse-study/John/3/16");
console.log(d.ref, "-", d.translations[0].text.slice(0, 60) + "...");
console.log("Key words:", d.key_words.length);
for (const kw of d.key_words.slice(0, 4)) {
  console.log(`  ${kw.word} (${kw.strongs}): ${kw.gloss} - ${kw.definition}`);
}
console.log("Cross-refs:", d.cross_refs.total);
console.log("Prayer:", d.prayer.label, `(${d.prayer.match_kind})`);
```

**Response** (sections trimmed; marked):

```json
{
  "ref": "John 3:16",
  "book": "John",
  "chapter": 3,
  "verse": 16,
  "testament": "NT",
  "translations": [
    {"code": "BSB", "present": true, "text": "For God so loved the world that He gave His one and only Son, that everyone who believes in Him shall not perish but have eternal life."},
    {"code": "KJV", "present": true, "text": "[trimmed]"},
    {"code": "WEB", "present": true, "text": "[trimmed]"}
  ],
  "key_words": [
    {"position": 3, "word": "ἠγάπησεν", "transliteration": "ēgapēsen", "strongs": "G25", "gloss": "to love", "morphology": "V-AAI-3S", "lemma": "ἀγαπάω", "definition": "to love", "definition_source": "step_tbesg"}
  ],
  "key_words_note": null,
  "cross_refs": {"total": 19, "refs": [{"ref": "Genesis 22:12", "text": "[trimmed]"}]},
  "commentaries": [{"source": "barnes_nt", "source_title": "Albert Barnes, Barnes' New Testament Notes (NT only)", "ref_range": "John 3:16", "text": "[trimmed]", "truncated": true, "full_length": 2176}],
  "devotionals": [{"source": "my_utmost", "source_title": "My Utmost for His Highest", "part": "morning", "title": "The Abandonment Of God", "anchor_ref": "John 3:16", "text": "[trimmed]", "truncated": true, "full_length": 1234, "match_kind": "exact"}],
  "prayer": {"office": "morning_prayer", "edition": "bcp1662", "label": "The second Collect for Peace", "speaker": null, "text": "[trimmed]", "match_kind": "keyword", "matched_keywords": ["love", "god", "all", "trust", "life", "eternal"]},
  "sources": [{"id": "step_tagnt", "title": "STEPBible TAGNT (Translators Amalgamated Greek NT)", "rights": "CC BY 4.0"}],
  "rights_note": "Interlinear word data: STEPBible TAGNT (Translators Amalgamated Greek NT) (https://www.stepbible.org), data created by STEPBible.org based on work at Tyndale House, Cambridge, used under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Key-word definitions: STEPBible Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt, used under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Phos modifications: selection of the Nestle-Aland/SBL critical-text reading (Greek) or the Leningrad Codex with the translators' Qere choices (Hebrew), mapped to KJV versification. All other texts on this page are public domain."
}
```

`?translations=` accepts up to four codes (default `BSB,KJV,WEB`); a verse
absent from one translation returns `present: false` for that translation.
`?office=evening` draws the prayer from Evening Prayer instead.
