# Phos (Dexia Bible API) - v1 service

Free public-domain Bible API. Serves BSB (default), KJV, WEB, and ASV
scripture text from a local read-only SQLite corpus
(`../data/scripture.db`, opened read-only - the API never writes).

## Run locally

```bash
cd ~/workspace/scripture-desk/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

PHOS_API_KEY=your-secret-key uvicorn app:app --host 127.0.0.1 --port 8000
```

The server refuses to start without `PHOS_API_KEY`. Every `/v1/*`
endpoint requires the key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key" \
  "http://127.0.0.1:8000/v1/passage?ref=John+3:16&translation=BSB"
```

Health needs no key: `curl http://127.0.0.1:8000/health`.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /health | no | Status, translations, total verse count |
| GET | /v1/translations | yes | Per-translation metadata + rights/copyright text |
| GET | /v1/books?translation=BSB | yes | 66 books with chapter counts |
| GET | /v1/passage?ref=Ps+23:1-3&translation=BSB | yes | Verse lookup (ranges, chapters, aliases) |
| GET | /v1/compare?ref=John+3:16&translations=BSB,KJV | yes | Side-by-side translations; missing verse keys reported as null, not errors |
| GET | /v1/search?q=lovingkindness&translation=KJV&limit=20 | yes | FTS5 ranked search with snippets |
| GET | /v1/verse-of-day?translation=BSB&day=2026-09-20 | yes | Deterministic per date+translation |
| GET | /v1/topics | yes | 64 curated topics with mood tags |
| GET | /v1/topics/peace?translation=BSB | yes | Topic verses resolved to full text |
| GET | /v1/moods | yes | 14 moods mapped to topics |
| GET | /v1/moods/anxious?translation=BSB | yes | Mood -> topics -> verses |
| GET | /v1/reading-plans | yes | Plan list (Bible in a year, NT 90, Psalms/Proverbs 31, Gospels 30) |
| GET | /v1/reading-plans/bible-in-a-year | yes | Full day-by-day schedule |
| GET | /v1/reading-plans/gospels-30/today?start_date=2026-01-01 | yes | Stateless: computes day from start date, returns today's passages |
| POST | /v1/reading-plans/gospels-30/checkin | yes | Body `{start_date, day}`: marks a day done |
| GET | /v1/reading-plans/gospels-30/progress?start_date=2026-01-01 | yes | Completed days + percent |
| GET | /v1/study?ref=Ps+23:1&translation=BSB | yes | One-call bundle: passage + TSK cross-refs (capped 25/verse) + commentary excerpts + rights |
| GET | /v1/commentary?ref=Gen+1:1&source=jfb | yes | Full-text commentary entries covering a ref (MH, JFB, Barnes NT; whole-chapter comments match verses) |
| GET | /v1/cross-refs?ref=Ps+23:1 | yes | TSK cross-references per verse, canonical order |
| GET | /v1/devotional?date=2026-09-20&source=spurgeon | yes | Morning + evening devotional (Spurgeon or Daily Light); Feb 29 entry served only on real Feb 29 |
| GET | /v1/prayer?office=morning&edition=1662 | yes | BCP Morning/Evening Prayer office as ordered liturgy blocks (1662 or 1928) |
| GET | /v1/memory-pack?topic=peace | yes | Numbered memorization pack, up to 10 verses |

Topics live in `data/topics.json` (curated refs; `data/validate_refs.py`
resolves every ref through the parser against the DB and fails the build
if any ref is invalid). Reading plans are generated programmatically by
`data/gen_plans.py` from the DB's chapter lists.

Study resources live in `data/study.db` (opened read-only via
`PHOS_STUDY_DB_PATH`, default `../data/study.db`; served by `study.py`).
Contents: `commentaries` (Matthew Henry, JFB, Barnes NT - verse 0 means
whole chapter), `crossrefs` (TSK), `devotionals` (Spurgeon, Daily Light -
day 1..366, Feb 29 = 60), `liturgy` + `liturgy_sources` (BCP 1662/1928
offices), `sources` (rights metadata). Note: `commentaries.book_order` is
1-based (1..66) while `crossrefs.book_order` and the M1 verses table are
0-based (0..65); the API bridges the two.

Reference forms: `John 3:16`, `Ps 23:1-3`, `Romans 8:28-30`, `John 14`,
`Genesis 1-2`, `John 3:16-4:2`, `Ps 23:1,3,5`. Aliases: `Ps`/`Psalm`,
`Song of Solomon` -> `Song of Songs`, `1John`/`1 John`, etc.

## Regenerate the OpenAPI spec

```bash
PHOS_API_KEY=dummy python gen_openapi.py   # writes openapi.json (3.1.0)
```

## Run tests

```bash
pytest -q
```

## Notes

- stdlib `sqlite3` only, no ORM. The scripture DB is opened with `mode=ro`.
- Progress tracking (check-ins) is stored in `data/progress.db` - checkmarks
  only, no scripture text; keyed by (plan_id, start_date) since v1 has a
  single API key. Override with `PHOS_PROGRESS_PATH` (the test suite points
  it at a temp file).
- Auth is constant-time `hmac.compare_digest` against `PHOS_API_KEY`.
- All served text is public domain; rights metadata ships with the API
  (`GET /v1/translations`) per the getBible distribution terms.
