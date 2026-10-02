"""Phos (Dexia Bible API) - v1 FastAPI service.

Serves public-domain Bible text (BSB default, plus KJV, WEB, ASV, YLT,
DARBY, DRB, GENEVA, AKJV, OEB) from a
local read-only SQLite corpus. Authentication is a single API key in one
header (``X-API-Key``), read from the ``PHOS_API_KEY`` environment variable
and compared in constant time. No OAuth.

Run locally::

    PHOS_API_KEY=your-secret-key uvicorn app:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

import db
import progress
import study
from parser import RefError, parse_reference, resolve_book
from translations import DEFAULT_TRANSLATION, TRANSLATIONS, TRANSLATION_CODES

_API_KEY = os.environ.get("PHOS_API_KEY")
if not _API_KEY:
    raise RuntimeError(
        "PHOS_API_KEY environment variable is required (the API key clients "
        "must send in the X-API-Key header)."
    )

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    key: Annotated[str | None, Depends(api_key_header)],
) -> str:
    """Reject requests without the correct X-API-Key header (HTTP 401)."""
    try:
        ok = key is not None and hmac.compare_digest(key, _API_KEY)
    except (TypeError, ValueError):
        ok = False
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Send it in the X-API-Key header.",
        )
    return key  # type: ignore[return-value]


def _translation_or_400(code: str) -> str:
    code = (code or "").strip().upper()
    if code not in TRANSLATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown translation '{code}'. "
            f"Valid translations: {', '.join(TRANSLATION_CODES)}.",
        )
    return code


def _parse_or_400(ref: str, translation: str):
    try:
        return parse_reference(ref, db.get_bounds(translation))
    except RefError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _verse_int(row: dict) -> dict:
    return {
        "book": row["book"],
        "chapter": row["chapter"],
        "verse": int(row["verse"]),
        "text": row["text"],
    }


DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def _topics_data() -> dict:
    return json.loads((DATA_DIR / "topics.json").read_text())


@lru_cache(maxsize=1)
def _plans_data() -> dict:
    return json.loads((DATA_DIR / "plans.json").read_text())


def _topic_or_404(topic_id: str) -> dict:
    for topic in _topics_data()["topics"]:
        if topic["id"] == topic_id:
            return topic
    raise HTTPException(
        status_code=404,
        detail=f"Unknown topic '{topic_id}'. See GET /v1/topics for the list.",
    )


def _mood_or_404(mood: str) -> dict:
    mood = (mood or "").strip().lower()
    for entry in _topics_data()["moods"]:
        if entry["mood"] == mood:
            return entry
    raise HTTPException(
        status_code=404,
        detail=f"Unknown mood '{mood}'. See GET /v1/moods for the list.",
    )


def _plan_or_404(plan_id: str) -> dict:
    for plan in _plans_data()["plans"]:
        if plan["id"] == plan_id:
            return plan
    raise HTTPException(
        status_code=404,
        detail=f"Unknown reading plan '{plan_id}'. "
        "See GET /v1/reading-plans for the list.",
    )


def _topics_for_mood(mood: str) -> list[dict]:
    return [t for t in _topics_data()["topics"] if mood in t["moods"]]


def _resolve_refs(refs: list[str], code: str) -> list[dict]:
    """Resolve refs to ``[{ref, verses}]`` using the translation's own bounds."""
    bounds = db.get_bounds(code)
    out = []
    for ref in refs:
        try:
            parsed = parse_reference(ref, bounds)
        except RefError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        rows = db.fetch_spans(code, parsed.book, parsed.spans)
        out.append(
            {
                "ref": parsed.display,
                "verses": [VerseItem(**_verse_int(r)) for r in rows],
            }
        )
    return out


def _parse_date_or_400(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {name} '{value}'. Use YYYY-MM-DD.",
        )


def _day_number_or_400(plan: dict, start: date, today: date) -> int:
    day = (today - start).days + 1
    if day < 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The '{plan['name']}' plan starts on {start.isoformat()} "
                f"and has not begun yet."
            ),
        )
    if day > plan["days"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"You have finished the '{plan['name']}' plan! "
                f"It ran {plan['days']} days from {start.isoformat()}."
            ),
        )
    return day


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #

class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    translations: list[str] = Field(examples=[TRANSLATION_CODES])
    verse_count: int = Field(examples=[124369])


class RightsInfo(BaseModel):
    status: str = Field(examples=["public_domain"])
    copyright: str = Field(examples=["Public domain ..."])
    attribution: str = Field(examples=["No attribution required ..."])


class TranslationInfo(BaseModel):
    code: str = Field(examples=["BSB"])
    name: str = Field(examples=["Berean Standard Bible"])
    edition: str = Field(examples=["v5.2 (publisher USFM release)"])
    source: str = Field(examples=["BSB-publishing/bsb2usfm v5.2"])
    retrieved: str = Field(examples=["2026-09-20"])
    default: bool = Field(examples=[True])
    verse_count: int = Field(examples=[31086])
    rights: RightsInfo
    notes: str | None = Field(default=None, examples=["Includes the deuterocanonical books."])


class BookInfo(BaseModel):
    book_order: int = Field(examples=[18])
    book: str = Field(examples=["Psalms"])
    chapters: int = Field(examples=[150])


class VerseItem(BaseModel):
    book: str = Field(examples=["Psalms"])
    chapter: int = Field(examples=[23])
    verse: int = Field(examples=[1])
    text: str = Field(examples=["The LORD is my shepherd; I shall not want."])


class PassageResponse(BaseModel):
    ref: str = Field(examples=["Psalms 23:1-3"])
    translation: str = Field(examples=["BSB"])
    book: str = Field(examples=["Psalms"])
    verses: list[VerseItem]


class CompareVerse(BaseModel):
    chapter: int = Field(examples=[23])
    verse: int = Field(examples=[1])
    # Null text = verse key not present in that translation (e.g. WEB/ASV
    # omit some KJV verse keys for textual-critical reasons).
    texts: dict[str, str | None] = Field(
        examples=[{"BSB": "The LORD is my shepherd ...", "KJV": "The LORD is my shepherd ..."}]
    )


class CompareResponse(BaseModel):
    ref: str = Field(examples=["Psalms 23:1"])
    book: str = Field(examples=["Psalms"])
    translations: list[str] = Field(examples=[["BSB", "KJV", "WEB"]])
    verses: list[CompareVerse]
    note: str = Field(
        examples=[
            "A null text means the verse key is not present in that translation."
        ]
    )


class SearchHit(BaseModel):
    book: str = Field(examples=["Psalms"])
    chapter: int = Field(examples=[63])
    verse: int = Field(examples=[3])
    text: str = Field(examples=["Because thy lovingkindness is better than life ..."])
    snippet: str = Field(
        examples=["Because thy <em>lovingkindness</em> is better than life ..."]
    )


class SearchResponse(BaseModel):
    q: str = Field(examples=["lovingkindness"])
    translation: str = Field(examples=["KJV"])
    count: int = Field(examples=[3])
    hits: list[SearchHit]


class VerseOfDayResponse(BaseModel):
    date: str = Field(examples=["2026-09-20"])
    translation: str = Field(examples=["BSB"])
    book: str = Field(examples=["Jeremiah"])
    chapter: int = Field(examples=[29])
    verse: int = Field(examples=[11])
    text: str = Field(examples=["For I know the plans I have for you ..."])


class TopicSummary(BaseModel):
    id: str = Field(examples=["peace"])
    label: str = Field(examples=["Peace"])
    description: str = Field(examples=["The deep calm God gives ..."])
    moods: list[str] = Field(examples=[["anxious", "afraid"]])


class TopicDetail(BaseModel):
    id: str = Field(examples=["peace"])
    label: str = Field(examples=["Peace"])
    description: str = Field(examples=["The deep calm God gives ..."])
    moods: list[str] = Field(examples=[["anxious", "afraid"]])
    translation: str = Field(examples=["BSB"])
    verses: list[VerseItem]


class MoodSummary(BaseModel):
    mood: str = Field(examples=["anxious"])
    label: str = Field(examples=["Anxious"])
    description: str = Field(examples=["Worried, on edge, mind racing."])
    topics: list[str] = Field(examples=[["peace", "anxiety", "trust"]])


class MoodTopicVerses(BaseModel):
    id: str = Field(examples=["peace"])
    label: str = Field(examples=["Peace"])
    description: str = Field(examples=["The deep calm God gives ..."])
    verses: list[VerseItem]


class MoodDetail(BaseModel):
    mood: str = Field(examples=["anxious"])
    label: str = Field(examples=["Anxious"])
    description: str = Field(examples=["Worried, on edge, mind racing."])
    translation: str = Field(examples=["BSB"])
    topics: list[MoodTopicVerses]


class PlanSummary(BaseModel):
    id: str = Field(examples=["bible-in-a-year"])
    name: str = Field(examples=["Bible in a Year"])
    description: str = Field(examples=["The whole Bible in one year ..."])
    days: int = Field(examples=[365])
    total_chapters: int = Field(examples=[1189])


class PlanDay(BaseModel):
    day: int = Field(examples=[1])
    refs: list[str] = Field(examples=[["Genesis 1-4"]])


class PlanDetail(BaseModel):
    id: str = Field(examples=["bible-in-a-year"])
    name: str = Field(examples=["Bible in a Year"])
    description: str = Field(examples=["The whole Bible in one year ..."])
    days: int = Field(examples=[365])
    total_chapters: int = Field(exexamples=[1189])
    schedule: list[PlanDay]


class PlanPassage(BaseModel):
    ref: str = Field(examples=["Genesis 1-4"])
    verses: list[VerseItem]


class PlanTodayResponse(BaseModel):
    plan_id: str = Field(examples=["bible-in-a-year"])
    plan_name: str = Field(examples=["Bible in a Year"])
    start_date: str = Field(examples=["2026-01-01"])
    date: str = Field(examples=["2026-09-20"])
    day: int = Field(examples=[263])
    total_days: int = Field(examples=[365])
    passages: list[PlanPassage]


class CheckinRequest(BaseModel):
    start_date: str = Field(examples=["2026-01-01"])
    day: int = Field(examples=[1])


class CheckinResponse(BaseModel):
    plan_id: str = Field(examples=["bible-in-a-year"])
    start_date: str = Field(examples=["2026-01-01"])
    day: int = Field(examples=[1])
    checked_in_at: str = Field(examples=["2026-09-20T15:00:00+00:00"])


class PlanProgressResponse(BaseModel):
    plan_id: str = Field(examples=["bible-in-a-year"])
    start_date: str = Field(examples=["2026-01-01"])
    total_days: int = Field(examples=[365])
    completed_days: list[int] = Field(examples=[[1, 2, 3]])
    completed_count: int = Field(examples=[3])
    percent: float = Field(examples=[0.8])


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="Phos (Dexia Bible API)",
    version="1.0.0",
    openapi_version="3.1.0",
    description=(
        "A free public-domain Bible API. Serves BSB (default), KJV, WEB, and "
        "ASV scripture text with passage lookup, translation comparison, "
        "full-text search, a deterministic verse of the day, topic and mood "
        "discovery, guided reading plans with progress tracking, and "
        "public-domain study resources: commentaries (Matthew Henry, JFB, "
        "Barnes), Treasury of Scripture Knowledge cross-references, daily "
        "devotionals (Spurgeon, Daily Light), and Book of Common Prayer "
        "offices.\n\n"
        "All served text is public domain; per-translation rights metadata is "
        "available at `GET /v1/translations`. Authenticate with a single API "
        "key in the `X-API-Key` header."
    ),
    openapi_tags=[
        {"name": "meta", "description": "Service status and translation metadata."},
        {"name": "scripture", "description": "Passage lookup, comparison, and search."},
        {"name": "daily", "description": "Deterministic verse of the day."},
        {
            "name": "topics",
            "description": "Topic and mood discovery: curated verses for life topics.",
        },
        {
            "name": "plans",
            "description": "Guided reading plans with stateless daily readings and progress.",
        },
        {
            "name": "study",
            "description": "Public-domain study resources: commentaries, cross-references, devotionals, prayer offices, memory packs.",
        },
    ],
)


_LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phos - A Free Bible API</title>
<meta name="description" content="Phos is a free Bible API: public-domain translations, verse study, interlinear original-language data, commentaries, cross-references, lexicons, and devotionals.">
<style>
:root { color-scheme: light; --navy:#2b2e6f; --ink:#1a1a2e; --muted:#5b5b70; --paper:#faf8f2; --gold:#c2a878; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       line-height: 1.65; color: var(--ink); background: var(--paper); margin: 0; }
.wrap { max-width: 860px; margin: 0 auto; padding: 72px 24px 48px; }
.eyebrow { font-size: 13px; letter-spacing: 4px; text-transform: uppercase; color: var(--navy); font-weight: 700; }
h1 { font-size: 52px; margin: 10px 0 6px; color: var(--navy); letter-spacing: -1px; }
.tagline { font-size: 22px; color: var(--ink); margin: 0 0 16px; font-weight: 500; }
.lede { font-size: 17px; color: var(--muted); max-width: 640px; }
.stats { display: flex; gap: 32px; flex-wrap: wrap; margin: 36px 0; padding: 24px 0;
         border-top: 1px solid #e4ddcb; border-bottom: 1px solid #e4ddcb; }
.stat b { display: block; font-size: 28px; color: var(--navy); }
.stat span { font-size: 14px; color: var(--muted); }
h2 { font-size: 24px; color: var(--navy); margin: 48px 0 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
@media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
.card { background: #fff; border: 1px solid #e9e2d0; border-radius: 12px; padding: 20px; }
.card h3 { margin: 0 0 6px; font-size: 16px; color: var(--navy); }
.card p { margin: 0; font-size: 14px; color: var(--muted); }
.card code { font-size: 12px; background: #f1ecdd; padding: 1px 6px; border-radius: 4px; color: var(--navy); }
pre { background: #1e1f3d; color: #e8e4d5; padding: 20px; border-radius: 12px; overflow-x: auto; font-size: 13.5px; line-height: 1.5; }
pre .c { color: #8a8fa8; }
.btns { display: flex; gap: 12px; flex-wrap: wrap; margin: 40px 0 8px; }
.btn { display: inline-block; background: var(--navy); color: #fff; text-decoration: none;
       padding: 12px 28px; border-radius: 999px; font-size: 16px; font-weight: 600; }
.btn.ghost { background: transparent; color: var(--navy); border: 2px solid var(--navy); }
.auth { font-size: 14px; color: var(--muted); }
.auth code { background: #f1ecdd; padding: 1px 6px; border-radius: 4px; color: var(--navy); }
.footer { margin-top: 64px; padding-top: 24px; border-top: 1px solid #e4ddcb;
          font-size: 13px; color: #9a9aa8; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.footer a { color: var(--muted); }
</style>
</head>
<body>
<div class="wrap">

<div class="eyebrow">Phos</div>
<h1>A free Bible API</h1>
<p class="tagline">Scripture text and study tools, through one simple API.</p>
<p class="lede">Phos serves public-domain Bible translations and study resources over a clean REST
interface. Look up any passage, compare translations, dig into the original Greek and Hebrew,
and explore commentaries, cross-references, and devotionals - all with a single API key.</p>

<div class="stats">
<div class="stat"><b>17</b><span>translations</span></div>
<div class="stat"><b>490,335</b><span>verses</span></div>
<div class="stat"><b>8</b><span>commentary sources</span></div>
<div class="stat"><b>Free</b><span>forever, no fees</span></div>
</div>

<h2>What you can build with it</h2>
<div class="grid">
<div class="card">
<h3>Verse lookup</h3>
<p>Fetch any verse, range, chapter, or multi-chapter passage in canonical order, in any of 17 translations.</p>
<p><code>GET /v1/passage</code></p>
</div>
<div class="card">
<h3>Intensive verse study</h3>
<p>One call returns a verse in up to four translations, the key original-language words with meanings, top cross-references, commentary excerpts, related devotionals, and a prayer.</p>
<p><code>GET /v1/verse-study/{book}/{chapter}/{verse}</code></p>
</div>
<div class="card">
<h3>Original languages</h3>
<p>Word-by-word interlinear Greek and Hebrew data with lexicon definitions (STEPBible, CC BY 4.0, fully attributed).</p>
<p><code>GET /v1/interlinear/{book}/{chapter}/{verse}</code></p>
</div>
<div class="card">
<h3>Study tools</h3>
<p>Full-text search, commentaries, cross-references, Greek/Hebrew lexicons, dictionaries, topics, reading plans, verse of the day, and daily devotionals.</p>
<p><code>GET /v1/search</code> <code>GET /v1/study</code> <code>GET /v1/word</code></p>
</div>
</div>

<h2>Quick start</h2>
<pre><span class="c"># Every request authenticates with your API key in the X-API-Key header.</span>
curl -H "X-API-Key: YOUR_API_KEY" \
  "/v1/passage?ref=John%203:16&amp;translation=BSB"</pre>
<p class="auth">No accounts to create, no tracking, no fees. Free for personal and commercial use.</p>

<div class="btns">
<a class="btn" href="/docs">API reference</a>
<a class="btn ghost" href="/privacy">Privacy policy</a>
<a class="btn ghost" href="/terms">Terms of service</a>
</div>

<h2>Support Phos</h2>
<p class="lede">Phos is free and always will be. If it deepens your study, a tip helps keep the servers running.</p>
<script type='text/javascript' src='https://storage.ko-fi.com/cdn/widget/Widget_2.js'></script>
<script type='text/javascript'>kofiwidget2.init('Support me on Ko-fi', '#72a4f2', 'G7L427ZGGR');kofiwidget2.draw();</script>

<div class="footer">
<span>&copy; 2026 Dexia Digi. Scripture text is in the public domain; study data is licensed as noted.</span>
<span>Contact: <a href="mailto:dexiadigi@gmail.com">dexiadigi@gmail.com</a></span>
</div>

</div>
</body>
</html>
"""


@app.get(
    "/",
    include_in_schema=False,
    summary="Landing page (no auth)",
)
def landing():
    return HTMLResponse(_LANDING_HTML)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["meta"],
    summary="Service health (no auth required)",
    description=(
        "Returns service status, the available translation codes, and the "
        "total verse row count across all translations. "
        "This endpoint does not require an API key."
    ),
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        translations=TRANSLATION_CODES,
        verse_count=db.total_verse_count(),
    )


@app.get(
    "/v1/translations",
    response_model=list[TranslationInfo],
    tags=["meta"],
    summary="Translation metadata and rights",
    description=(
        "Per-translation metadata: name, edition, source, verse count, and "
        "rights/copyright/attribution text. All seventeen translations are public "
        "domain; the rights block preserves each translation's own copyright "
        "metadata as required by the getBible distribution terms."
    ),
    dependencies=[Depends(require_api_key)],
)
def list_translations() -> list[TranslationInfo]:
    counts = db.translation_counts()
    return [
        TranslationInfo(
            code=code,
            name=meta["name"],
            edition=meta["edition"],
            source=meta["source"],
            retrieved=meta["retrieved"],
            default=meta["default"],
            verse_count=counts.get(code, 0),
            rights=RightsInfo(**meta["rights"]),
            notes=meta.get("notes"),
        )
        for code, meta in TRANSLATIONS.items()
    ]


@app.get(
    "/v1/books",
    response_model=list[BookInfo],
    tags=["meta"],
    summary="Canonical book list",
    description=(
        "The 66 canonical books in order, with each book's chapter count, "
        "for the requested translation."
    ),
    dependencies=[Depends(require_api_key)],
)
def list_books(
    translation: Annotated[
        str,
        Query(
            description="Translation code.",
            examples=["BSB"],
        ),
    ] = DEFAULT_TRANSLATION,
) -> list[BookInfo]:
    code = _translation_or_400(translation)
    return [BookInfo(**b) for b in db.get_books(code)]


@app.get(
    "/v1/passage",
    response_model=PassageResponse,
    tags=["scripture"],
    summary="Look up a passage",
    description=(
        "Returns the verses for a Bible reference in canonical order. "
        "Accepts single verses ('John 3:16'), verse ranges ('Ps 23:1-3'), "
        "whole chapters ('John 14'), chapter ranges ('Genesis 1-2'), "
        "multi-chapter ranges ('John 3:16-4:2'), and comma lists "
        "('Ps 23:1,3,5'). Book aliases are accepted ('Ps', 'Psalms', "
        "'Song of Solomon', '1John'). Returns 400 for unparseable or "
        "out-of-range references, and 404 when a valid verse key is not "
        "present in the requested translation."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_passage(
    ref: Annotated[
        str,
        Query(
            description="Bible reference to look up.",
            examples=["John 3:16-18", "Ps 23:1-3", "Romans 8:28-30"],
        ),
    ],
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> PassageResponse:
    code = _translation_or_400(translation)
    parsed = _parse_or_400(ref, code)
    rows = db.fetch_spans(code, parsed.book, parsed.spans)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{parsed.display}' is not present in the {code} translation "
                "(some verse keys are absent from WEB/ASV for textual-critical "
                "reasons)."
            ),
        )
    return PassageResponse(
        ref=parsed.display,
        translation=code,
        book=parsed.book,
        verses=[VerseItem(**_verse_int(r)) for r in rows],
    )


@app.get(
    "/v1/compare",
    response_model=CompareResponse,
    tags=["scripture"],
    summary="Compare translations side by side",
    description=(
        "Returns the same reference rendered in each requested translation, "
        "side by side. A null text for a translation means that verse key is "
        "genuinely not present in that translation (WEB omits 7 and ASV omits "
        "16 KJV verse keys, e.g. Acts 8:37) - this is reported, not an error."
    ),
    dependencies=[Depends(require_api_key)],
)
def compare_translations(
    ref: Annotated[
        str,
        Query(
            description="Bible reference to compare.",
            examples=["Ps 23:1", "John 3:16"],
        ),
    ],
    translations: Annotated[
        str,
        Query(
            description="Comma-separated translation codes.",
            examples=["BSB,KJV,WEB"],
        ),
    ] = "BSB,KJV",
) -> CompareResponse:
    codes: list[str] = []
    for part in translations.split(","):
        code = _translation_or_400(part)
        if code not in codes:
            codes.append(code)
    # Parse against the first translation's bounds; each translation is then
    # read independently so genuine verse-key gaps surface as nulls.
    parsed = _parse_or_400(ref, codes[0])
    per_code: dict[str, dict[tuple[int, int], str]] = {}
    for code in codes:
        rows = db.fetch_spans(code, parsed.book, parsed.spans)
        per_code[code] = {
            (r["chapter"], int(r["verse"])): r["text"] for r in rows
        }
    keys = sorted({k for texts in per_code.values() for k in texts})
    if not keys:
        raise HTTPException(
            status_code=404,
            detail=f"'{parsed.display}' is not present in any of the requested translations.",
        )
    return CompareResponse(
        ref=parsed.display,
        book=parsed.book,
        translations=codes,
        verses=[
            CompareVerse(
                chapter=ch,
                verse=v,
                texts={code: per_code[code].get((ch, v)) for code in codes},
            )
            for ch, v in keys
        ],
        note=(
            "A null text means the verse key is not present in that "
            "translation (WEB omits 7 and ASV omits 16 KJV verse keys for "
            "textual-critical reasons; the content is preserved at the "
            "critical-text location)."
        ),
    )


_FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _fts_query(q: str) -> str:
    """Build a safe FTS5 MATCH query: quoted alphanumeric terms (implicit AND)."""
    terms = _FTS_TOKEN_RE.findall(q or "")
    if not terms:
        raise HTTPException(
            status_code=400, detail="Search query is empty after removing punctuation."
        )
    return " ".join(f'"{t}"' for t in terms)


@app.get(
    "/v1/search",
    response_model=SearchResponse,
    tags=["scripture"],
    summary="Full-text search",
    description=(
        "Searches verse text with the FTS5 index (porter stemming). Results "
        "are ranked best-first and include an <em>-highlighted snippet. "
        "Query terms are ANDed together."
    ),
    dependencies=[Depends(require_api_key)],
)
def search(
    q: Annotated[
        str,
        Query(description="Search terms.", examples=["lovingkindness"]),
    ],
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["KJV"]),
    ] = DEFAULT_TRANSLATION,
    limit: Annotated[
        int,
        Query(description="Max results (1-100).", examples=[20], ge=1, le=100),
    ] = 20,
) -> SearchResponse:
    code = _translation_or_400(translation)
    rows = db.search_verses(code, _fts_query(q), limit)
    return SearchResponse(
        q=q,
        translation=code,
        count=len(rows),
        hits=[
            SearchHit(
                book=r["book"],
                chapter=r["chapter"],
                verse=int(r["verse"]),
                text=r["text"],
                snippet=r["snippet"],
            )
            for r in rows
        ],
    )


@app.get(
    "/v1/verse-of-day",
    response_model=VerseOfDayResponse,
    tags=["daily"],
    summary="Verse of the day",
    description=(
        "Deterministic verse for a calendar date: SHA-256 of "
        "'YYYY-MM-DD|TRANSLATION' selects a verse by offset into the "
        "translation's canonical order. The same date and translation always "
        "return the same verse."
    ),
    dependencies=[Depends(require_api_key)],
)
def verse_of_day(
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
    day: Annotated[
        str | None,
        Query(
            description="Date as YYYY-MM-DD. Defaults to today.",
            examples=["2026-09-20"],
        ),
    ] = None,
) -> VerseOfDayResponse:
    code = _translation_or_400(translation)
    if day is None:
        day = date.today().isoformat()
    else:
        try:
            date.fromisoformat(day)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date '{day}'. Use YYYY-MM-DD.",
            )
    count = db.translation_counts()[code]
    offset = int(hashlib.sha256(f"{day}|{code}".encode()).hexdigest(), 16) % count
    row = db.verse_by_offset(code, offset)
    return VerseOfDayResponse(
        date=day,
        translation=code,
        book=row["book"],
        chapter=row["chapter"],
        verse=int(row["verse"]),
        text=row["text"],
    )


# --------------------------------------------------------------------------- #
# Topics and moods
# --------------------------------------------------------------------------- #

@app.get(
    "/v1/topics",
    response_model=list[TopicSummary],
    tags=["topics"],
    summary="List curated topics",
    description=(
        "The curated topic list (peace, anxiety, gratitude, ...), each with "
        "its description and the moods it speaks to. Fetch a topic's verses "
        "at GET /v1/topics/{topic_id}."
    ),
    dependencies=[Depends(require_api_key)],
)
def list_topics() -> list[TopicSummary]:
    return [
        TopicSummary(
            id=t["id"],
            label=t["label"],
            description=t["description"],
            moods=t["moods"],
        )
        for t in _topics_data()["topics"]
    ]


@app.get(
    "/v1/topics/{topic_id}",
    response_model=TopicDetail,
    tags=["topics"],
    summary="Verses for a topic",
    description=(
        "The curated representative verses for one topic, resolved to full "
        "text in the requested translation."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_topic(
    topic_id: str,
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> TopicDetail:
    code = _translation_or_400(translation)
    topic = _topic_or_404(topic_id)
    verses: list[VerseItem] = []
    for entry in _resolve_refs(topic["refs"], code):
        verses.extend(entry["verses"])
    return TopicDetail(
        id=topic["id"],
        label=topic["label"],
        description=topic["description"],
        moods=topic["moods"],
        translation=code,
        verses=verses,
    )


@app.get(
    "/v1/moods",
    response_model=list[MoodSummary],
    tags=["topics"],
    summary="List moods",
    description=(
        "The mood list (anxious, lonely, grateful, ...), each mapped to the "
        "topics that speak to it. Fetch a mood's verses at "
        "GET /v1/moods/{mood}."
    ),
    dependencies=[Depends(require_api_key)],
)
def list_moods() -> list[MoodSummary]:
    return [
        MoodSummary(
            mood=m["mood"],
            label=m["label"],
            description=m["description"],
            topics=[t["id"] for t in _topics_for_mood(m["mood"])],
        )
        for m in _topics_data()["moods"]
    ]


@app.get(
    "/v1/moods/{mood}",
    response_model=MoodDetail,
    tags=["topics"],
    summary="Verses for a mood",
    description=(
        "Maps a mood to its topics, each with the topic's verses resolved "
        "to full text in the requested translation."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_mood(
    mood: str,
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> MoodDetail:
    code = _translation_or_400(translation)
    entry = _mood_or_404(mood)
    topics = []
    for topic in _topics_for_mood(entry["mood"]):
        verses: list[VerseItem] = []
        for resolved in _resolve_refs(topic["refs"], code):
            verses.extend(resolved["verses"])
        topics.append(
            MoodTopicVerses(
                id=topic["id"],
                label=topic["label"],
                description=topic["description"],
                verses=verses,
            )
        )
    return MoodDetail(
        mood=entry["mood"],
        label=entry["label"],
        description=entry["description"],
        translation=code,
        topics=topics,
    )


# --------------------------------------------------------------------------- #
# Reading plans
# --------------------------------------------------------------------------- #

@app.get(
    "/v1/reading-plans",
    response_model=list[PlanSummary],
    tags=["plans"],
    summary="List reading plans",
    description=(
        "The available guided reading plans (Bible in a year, New Testament "
        "in 90 days, Psalms & Proverbs in 31 days, the Gospels in 30 days). "
        "Schedules are generated programmatically from the corpus's canonical "
        "chapter structure."
    ),
    dependencies=[Depends(require_api_key)],
)
def list_plans() -> list[PlanSummary]:
    return [
        PlanSummary(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            days=p["days"],
            total_chapters=p["total_chapters"],
        )
        for p in _plans_data()["plans"]
    ]


@app.get(
    "/v1/reading-plans/{plan_id}",
    response_model=PlanDetail,
    tags=["plans"],
    summary="Full plan schedule",
    description=(
        "The complete day-by-day schedule for a reading plan: each day's "
        "chapter refs in canonical order."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_plan(plan_id: str) -> PlanDetail:
    plan = _plan_or_404(plan_id)
    return PlanDetail(
        id=plan["id"],
        name=plan["name"],
        description=plan["description"],
        days=plan["days"],
        total_chapters=plan["total_chapters"],
        schedule=[PlanDay(**d) for d in plan["schedule"]],
    )


@app.get(
    "/v1/reading-plans/{plan_id}/today",
    response_model=PlanTodayResponse,
    tags=["plans"],
    summary="Today's reading (stateless)",
    description=(
        "Computes the current plan day from the given start date "
        "(day = (today - start_date) + 1, stateless, no login) and returns "
        "that day's passages with full text. Returns 400 with a 'finished' "
        "message once the plan's days are complete, and 400 if the plan has "
        "not started yet."
    ),
    dependencies=[Depends(require_api_key)],
)
def plan_today(
    plan_id: str,
    start_date: Annotated[
        str,
        Query(
            description="The date the plan started, YYYY-MM-DD.",
            examples=["2026-01-01"],
        ),
    ],
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> PlanTodayResponse:
    code = _translation_or_400(translation)
    plan = _plan_or_404(plan_id)
    start = _parse_date_or_400(start_date, "start_date")
    today = date.today()
    day = _day_number_or_400(plan, start, today)
    day_entry = plan["schedule"][day - 1]
    return PlanTodayResponse(
        plan_id=plan["id"],
        plan_name=plan["name"],
        start_date=start.isoformat(),
        date=today.isoformat(),
        day=day,
        total_days=plan["days"],
        passages=[
            PlanPassage(ref=entry["ref"], verses=entry["verses"])
            for entry in _resolve_refs(day_entry["refs"], code)
        ],
    )


@app.post(
    "/v1/reading-plans/{plan_id}/checkin",
    response_model=CheckinResponse,
    tags=["plans"],
    summary="Check in a completed day",
    description=(
        "Marks one plan day as read. Progress is stored locally in "
        "api/data/progress.db (checkmarks only, no scripture) and keyed by "
        "plan plus start_date, since v1 uses a single API key."
    ),
    dependencies=[Depends(require_api_key)],
)
def plan_checkin(plan_id: str, body: CheckinRequest) -> CheckinResponse:
    plan = _plan_or_404(plan_id)
    start = _parse_date_or_400(body.start_date, "start_date")
    if not 1 <= body.day <= plan["days"]:
        raise HTTPException(
            status_code=400,
            detail=f"Day must be between 1 and {plan['days']} "
            f"for the '{plan['name']}' plan.",
        )
    checked_in_at = progress.checkin(plan["id"], start.isoformat(), body.day)
    return CheckinResponse(
        plan_id=plan["id"],
        start_date=start.isoformat(),
        day=body.day,
        checked_in_at=checked_in_at,
    )


@app.get(
    "/v1/reading-plans/{plan_id}/progress",
    response_model=PlanProgressResponse,
    tags=["plans"],
    summary="Reading progress",
    description=(
        "Completed days and completion percent for a plan and start_date, "
        "from the local check-in store."
    ),
    dependencies=[Depends(require_api_key)],
)
def plan_progress(
    plan_id: str,
    start_date: Annotated[
        str,
        Query(
            description="The date the plan started, YYYY-MM-DD.",
            examples=["2026-01-01"],
        ),
    ],
) -> PlanProgressResponse:
    plan = _plan_or_404(plan_id)
    start = _parse_date_or_400(start_date, "start_date")
    done = progress.completed_days(plan["id"], start.isoformat())
    return PlanProgressResponse(
        plan_id=plan["id"],
        start_date=start.isoformat(),
        total_days=plan["days"],
        completed_days=done,
        completed_count=len(done),
        percent=round(len(done) / plan["days"] * 100, 1),
    )


class CommentaryItem(BaseModel):
    source: str = Field(examples=["matthew_henry"])
    source_title: str = Field(
        examples=["Matthew Henry, Complete Commentary on the Whole Bible"]
    )
    ref_range: str = Field(examples=["Psalms 23"])
    # Excerpt in /v1/study (truncated at 600 chars); full text in /v1/commentary.
    text: str = Field(examples=["David's confidence in God's grace ..."])
    truncated: bool = Field(examples=[True])
    full_length: int = Field(examples=[2148])


class CrossRefVerse(BaseModel):
    chapter: int = Field(examples=[23])
    verse: int = Field(examples=[1])
    total: int = Field(examples=[42])
    refs: list[str] = Field(examples=[["Ezekiel 34:11", "Hebrews 13:5"]])


class StudySourceRef(BaseModel):
    id: str = Field(examples=["tsk"])
    title: str = Field(examples=["Treasury of Scripture Knowledge"])
    rights: str = Field(examples=["Public Domain"])


class StudyResponse(BaseModel):
    ref: str = Field(examples=["Psalms 23:1"])
    translation: str = Field(examples=["BSB"])
    book: str = Field(examples=["Psalms"])
    verses: list[VerseItem]
    cross_refs: list[CrossRefVerse]
    commentaries: list[CommentaryItem]
    sources: list[StudySourceRef]
    rights_note: str = Field(
        examples=["All commentary, cross-reference, devotional, and liturgy "
                  "texts served here are public domain."]
    )


class DevotionalEntry(BaseModel):
    title: str | None = Field(examples=["They did eat of the fruit ..."])
    anchor_ref: str = Field(examples=["Joshua 5:12"])
    anchor_verses: list[VerseItem]
    body: str = Field(examples=["..."])


class DevotionalResponse(BaseModel):
    source: str = Field(examples=["spurgeon"])
    source_title: str = Field(examples=["C. H. Spurgeon, Morning and Evening (1866)"])
    date: str = Field(examples=["2026-09-20"])
    day: int = Field(
        examples=[264],
        description="Leap-year day-of-year number used to look up the entry.",
    )
    morning: DevotionalEntry | None
    evening: DevotionalEntry | None


class PrayerBlock(BaseModel):
    section: str = Field(examples=["sentence"])
    label: str | None = Field(examples=["The Order for Morning Prayer"])
    speaker: str | None = Field(examples=["Minister"])
    kind: str = Field(examples=["text"])
    text: str = Field(examples=["When the wicked man turneth away ..."])


class PrayerResponse(BaseModel):
    edition: str = Field(examples=["1662"])
    edition_title: str = Field(examples=["Book of Common Prayer (1662)"])
    office: str = Field(examples=["morning"])
    blocks: list[PrayerBlock]


class MemoryVerse(BaseModel):
    n: int = Field(examples=[1])
    ref: str = Field(examples=["Psalms 23:1"])
    book: str = Field(examples=["Psalms"])
    chapter: int = Field(examples=[23])
    verse: int = Field(examples=[1])
    text: str = Field(examples=["The LORD is my shepherd; I shall not want."])


class MemoryPackResponse(BaseModel):
    topic: str = Field(examples=["peace"])
    label: str = Field(examples=["Peace"])
    translation: str = Field(examples=["BSB"])
    count: int = Field(examples=[8])
    verses: list[MemoryVerse]


# --------------------------------------------------------------------------- #
# Study resources (v2): commentaries, cross-refs, devotionals, prayer, memory
# --------------------------------------------------------------------------- #

_EXCERPT_LEN = 600
_STUDY_CROSSREF_CAP = 25


@lru_cache(maxsize=1)
def _study_sources() -> dict[str, dict]:
    return {s["source_id"]: s for s in study.get_sources()}


def _commentary_range_display(
    book: str, sc: int, sv: int, ec: int, ev: int
) -> str:
    """'Psalms 23' (whole chapter), 'Genesis 1:1', 'Genesis 1:1-2',
    'Isaiah 8:1-9:7' (cross-chapter). Verse 0 = whole chapter."""
    if sv == 0 and ev == 0:
        return f"{book} {sc}" if sc == ec else f"{book} {sc}-{ec}"
    if sc == ec:
        return f"{book} {sc}:{sv}" if sv == ev else f"{book} {sc}:{sv}-{ev}"
    return f"{book} {sc}:{sv}-{ec}:{ev}"


def _excerpt(text: str) -> tuple[str, bool]:
    if len(text) <= _EXCERPT_LEN:
        return text, False
    cut = text[:_EXCERPT_LEN].rsplit(" ", 1)[0]
    return cut + "...", True


def _commentary_item(row: dict, full: bool) -> CommentaryItem:
    src = _study_sources().get(row["source_id"], {})
    text = row["text"] if full else _excerpt(row["text"])[0]
    truncated = False if full else _excerpt(row["text"])[1]
    return CommentaryItem(
        source=row["source_id"],
        source_title=src.get("title", row["source_id"]),
        ref_range=_commentary_range_display(
            row["book"],
            row["start_chapter"],
            row["start_verse"],
            row["end_chapter"],
            row["end_verse"],
        ),
        text=text,
        truncated=truncated,
        full_length=len(row["text"]),
    )


def _verse_keys(code: str, parsed) -> tuple[int, list[tuple[int, int]]]:
    """Book order plus the (chapter, verse) keys present for parsed spans.

    NOTE: book_order conventions differ per table. The M1 verses table and
    study.db crossrefs/devotionals use 0-based book_order (0..65); the
    study.db commentaries table uses 1-based (1..66). This returns 0-based;
    callers targeting commentaries add 1.
    """
    book_order = db.get_bounds(code)[parsed.book]["order"]
    rows = db.fetch_spans(code, parsed.book, parsed.spans)
    return book_order, [(r["chapter"], int(r["verse"])) for r in rows]


def _covering_commentaries(
    code: str, parsed, source_id: str | None, full: bool
) -> list[CommentaryItem]:
    book_order, keys = _verse_keys(code, parsed)
    seen: set[int] = set()
    items: list[CommentaryItem] = []
    for ch, v in keys:
        # commentaries.book_order is 1-based; everything else is 0-based.
        rows = study.commentaries_covering(book_order + 1, ch, v, source_id)
        for row in rows:
            if row["id"] not in seen:
                seen.add(row["id"])
                items.append(_commentary_item(row, full))
    return items


def _cross_ref_verse(
    book_order: int, ch: int, v: int, cap: int | None
) -> CrossRefVerse:
    refs = [
        f"{r['ref_book']} {r['ref_chapter']}:{r['ref_verse']}"
        for r in study.crossrefs_for(book_order, ch, v)
    ]
    return CrossRefVerse(
        chapter=ch,
        verse=v,
        total=len(refs),
        refs=refs if cap is None else refs[:cap],
    )


def _commentary_source_or_400(source: str | None) -> str | None:
    if source is None:
        return None
    if source not in study.COMMENTARY_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown commentary source '{source}'. "
            f"Valid sources: {', '.join(study.COMMENTARY_SOURCES)}.",
        )
    return source


@app.get(
    "/v1/study",
    response_model=StudyResponse,
    tags=["study"],
    summary="One-call study bundle",
    description=(
        "The 'route here first' endpoint: the passage in full text, TSK "
        "cross-references per verse (capped at 25 per verse with a total "
        "count), and commentary excerpts from all eight commentary sources "
        "whose ranges cover the reference (whole-chapter comments included). "
        "All study texts are public domain; per-source rights metadata is in "
        "`sources`."
    ),
    dependencies=[Depends(require_api_key)],
)
def study_bundle(
    ref: Annotated[
        str,
        Query(
            description="Bible reference to study.",
            examples=["Ps 23:1", "Romans 8:28-30"],
        ),
    ],
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> StudyResponse:
    code = _translation_or_400(translation)
    parsed = _parse_or_400(ref, code)
    rows = db.fetch_spans(code, parsed.book, parsed.spans)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"'{parsed.display}' is not present in the {code} translation.",
        )
    book_order, keys = _verse_keys(code, parsed)
    srcs = _study_sources()
    used = {"tsk"}
    commentaries = _covering_commentaries(code, parsed, None, full=False)
    for item in commentaries:
        used.add(item.source)
    return StudyResponse(
        ref=parsed.display,
        translation=code,
        book=parsed.book,
        verses=[VerseItem(**_verse_int(r)) for r in rows],
        cross_refs=[
            _cross_ref_verse(book_order, ch, v, _STUDY_CROSSREF_CAP)
            for ch, v in keys
        ],
        commentaries=commentaries,
        sources=[
            StudySourceRef(
                id=sid,
                title=srcs[sid]["title"],
                rights=srcs[sid]["rights"],
            )
            for sid in sorted(used)
            if sid in srcs
        ],
        rights_note=(
            "All commentary, cross-reference, devotional, and liturgy texts "
            "served here are public domain."
        ),
    )


@app.get(
    "/v1/commentary",
    response_model=list[CommentaryItem],
    tags=["study"],
    summary="Commentary entries covering a reference",
    description=(
        "Full-text commentary entries whose verse range covers the requested "
        "reference. A verse query also matches whole-chapter comments. "
        "Omit `source` to search all eight commentaries "
        "(Matthew Henry, JFB, Barnes NT, Gill, Clarke, Calvin, "
        "Keil & Delitzsch, Treasury of David)."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_commentary(
    ref: Annotated[
        str,
        Query(
            description="Bible reference.",
            examples=["Genesis 1:1", "Ps 23"],
        ),
    ],
    source: Annotated[
        str | None,
        Query(
            description="Commentary source: matthew_henry, jfb, barnes_nt, gill, clarke, calvin, keil_delitzsch, treasury_of_david.",
            examples=["matthew_henry"],
        ),
    ] = None,
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> list[CommentaryItem]:
    code = _translation_or_400(translation)
    src = _commentary_source_or_400(source)
    parsed = _parse_or_400(ref, code)
    return _covering_commentaries(code, parsed, src, full=True)


@app.get(
    "/v1/cross-refs",
    response_model=list[CrossRefVerse],
    tags=["study"],
    summary="TSK cross-references for a reference",
    description=(
        "Treasury of Scripture Knowledge cross-references for each verse in "
        "the requested reference, in canonical order."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_cross_refs(
    ref: Annotated[
        str,
        Query(
            description="Bible reference.",
            examples=["Ps 23:1", "John 3:16"],
        ),
    ],
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> list[CrossRefVerse]:
    code = _translation_or_400(translation)
    parsed = _parse_or_400(ref, code)
    book_order, keys = _verse_keys(code, parsed)
    if not keys:
        raise HTTPException(
            status_code=404,
            detail=f"'{parsed.display}' is not present in the {code} translation.",
        )
    return [_cross_ref_verse(book_order, ch, v, None) for ch, v in keys]


def _devotional_day(d) -> int:
    """Leap-year day-of-year for devotional lookup.

    Devotionals are keyed 1..366 with Feb 29 = day 60. Feb 29's entry is
    served only on an actual Feb 29; in non-leap years, dates after Feb 28
    shift by one so Mar 1 reads Mar 1's entry (day 61), never Feb 29's.
    """
    doy = d.timetuple().tm_yday
    leap = d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)
    if leap:
        return doy
    return doy + (1 if d.month > 2 else 0)


def _devotional_entry(
    entry: dict | None, code: str
) -> DevotionalEntry | None:
    if entry is None:
        return None
    # Daily Light anchor_refs are semicolon-separated ref lists
    # ("Deuteronomy 31:8; Exodus 33:15; ..."); resolve each part.
    anchor_verses: list[VerseItem] = []
    bounds = db.get_bounds(code)
    for part in entry["anchor_ref"].split(";"):
        part = part.strip()
        if not part:
            continue
        try:
            parsed = parse_reference(part, bounds)
            rows = db.fetch_spans(code, parsed.book, parsed.spans)
            anchor_verses.extend(VerseItem(**_verse_int(r)) for r in rows)
        except RefError:
            continue
    return DevotionalEntry(
        title=entry["title"],
        anchor_ref=entry["anchor_ref"],
        anchor_verses=anchor_verses,
        body=entry["body"],
    )


@app.get(
    "/v1/devotional",
    response_model=DevotionalResponse,
    tags=["study"],
    summary="Daily devotional",
    description=(
        "The devotional entries for a calendar date. Spurgeon's Morning and "
        "Evening and Daily Light on the Daily Path provide morning and "
        "evening entries; My Utmost for His Highest, The Practice of the "
        "Presence of God, and The Imitation of Christ provide a single "
        "reading (evening is null). Anchor references are resolved to verse "
        "text in the requested translation."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_devotional(
    date_: Annotated[
        str,
        Query(
            alias="date",
            description="Date as YYYY-MM-DD. Defaults to today.",
            examples=["2026-09-20"],
        ),
    ] = "",
    source: Annotated[
        str,
        Query(
            description="Devotional source: spurgeon, daily_light, my_utmost, "
                        "practice_presence, or imitation_christ.",
            examples=["spurgeon"],
        ),
    ] = "spurgeon",
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> DevotionalResponse:
    code = _translation_or_400(translation)
    if source not in study.DEVOTIONAL_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown devotional source '{source}'. "
            f"Valid sources: {', '.join(study.DEVOTIONAL_SOURCES)}.",
        )
    day = _parse_date_or_400(date_ or date.today().isoformat(), "date")
    day_no = _devotional_day(day)
    entries = study.devotional(source, day_no)
    src = _study_sources().get(source, {})
    return DevotionalResponse(
        source=source,
        source_title=src.get("title", source),
        date=day.isoformat(),
        day=day_no,
        morning=_devotional_entry(entries["morning"], code),
        evening=_devotional_entry(entries["evening"], code),
    )


@app.get(
    "/v1/prayer",
    response_model=PrayerResponse,
    tags=["study"],
    summary="Book of Common Prayer office",
    description=(
        "A full Morning or Evening Prayer office from the 1662 or 1928 "
        "(US) Book of Common Prayer, as ordered liturgy blocks "
        "(sentences, confession, psalms, lessons, creed, collects, ...). "
        "Both editions are public domain."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_prayer(
    office: Annotated[
        str,
        Query(
            description="Office: morning or evening.",
            examples=["morning"],
        ),
    ] = "morning",
    edition: Annotated[
        str,
        Query(
            description="BCP edition: 1662 or 1928.",
            examples=["1662"],
        ),
    ] = "1662",
) -> PrayerResponse:
    if office not in study.PRAYER_OFFICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown office '{office}'. "
            f"Valid offices: {', '.join(study.PRAYER_OFFICES)}.",
        )
    if edition not in study.PRAYER_EDITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown edition '{edition}'. "
            f"Valid editions: {', '.join(study.PRAYER_EDITIONS)}.",
        )
    meta, blocks = study.prayer_office(edition, office)
    return PrayerResponse(
        edition=edition,
        edition_title=meta.get("title", f"Book of Common Prayer ({edition})"),
        office=office,
        blocks=[PrayerBlock(**b) for b in blocks],
    )


@app.get(
    "/v1/memory-pack",
    response_model=MemoryPackResponse,
    tags=["study"],
    summary="Memorization pack for a topic",
    description=(
        "A numbered memorization pack: the curated topic's verses resolved "
        "to full text in the requested translation, in order, up to 10 "
        "verses."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_memory_pack(
    topic: Annotated[
        str,
        Query(
            description="Topic id, e.g. peace.",
            examples=["peace"],
        ),
    ],
    translation: Annotated[
        str,
        Query(description="Translation code.", examples=["BSB"]),
    ] = DEFAULT_TRANSLATION,
) -> MemoryPackResponse:
    code = _translation_or_400(translation)
    entry = _topic_or_404(topic)
    verses: list[MemoryVerse] = []
    n = 0
    for resolved in _resolve_refs(entry["refs"], code):
        for v in resolved["verses"]:
            n += 1
            verses.append(
                MemoryVerse(
                    n=n,
                    ref=f"{v.book} {v.chapter}:{v.verse}",
                    book=v.book,
                    chapter=v.chapter,
                    verse=v.verse,
                    text=v.text,
                )
            )
            if n >= 10:
                break
        if n >= 10:
            break
    return MemoryPackResponse(
        topic=entry["id"],
        label=entry["label"],
        translation=code,
        count=len(verses),
        verses=verses,
    )


# --------------------------------------------------------------------------- #
# Word studies (v2): lexicons keyed by Strong's number
# --------------------------------------------------------------------------- #


class WordSourceRef(BaseModel):
    id: str = Field(examples=["strongs"])
    title: str = Field(examples=["Strong's Greek and Hebrew Dictionaries (1890)"])
    rights: str = Field(examples=["Public domain"])
    attribution: str | None = Field(
        default=None,
        examples=[
            "STEPBible lexicon data (TBESH, TBESG, TFLSJ), Tyndale House, "
            "Cambridge, licensed under CC BY 4.0 "
            "(https://creativecommons.org/licenses/by/4.0/)."
        ],
    )


class WordEntry(BaseModel):
    number: str = Field(examples=["G3056"])
    language: str = Field(examples=["greek"])
    lemma: str | None = Field(default=None, examples=["λόγος"])
    transliteration: str | None = Field(default=None, examples=["logos"])
    definition: str | None = Field(
        default=None,
        examples=["something said (including the thought); by implication..."],
    )
    gloss: str | None = Field(default=None)
    source: WordSourceRef


class WordResponse(BaseModel):
    number: str = Field(examples=["G3056"])
    language: str = Field(examples=["greek"])
    entries: list[WordEntry]


class LexiconSourceInfo(BaseModel):
    id: str = Field(examples=["bdb"])
    title: str = Field(examples=["OpenScriptures HebrewLexicon"])
    rights: str = Field(examples=["CC BY 4.0"])
    rights_basis: str | None = Field(default=None)
    attribution: str | None = Field(default=None)
    entries: int = Field(examples=[8674])


# --------------------------------------------------------------------------- #
# Dictionaries (v2): topical and alphabetical Bible dictionaries
# --------------------------------------------------------------------------- #


class DictionarySourceRef(BaseModel):
    id: str = Field(examples=["easton"])
    title: str = Field(examples=["M. G. Easton, Illustrated Bible Dictionary (1897)"])
    rights: str = Field(examples=["Public Domain"])
    attribution: str | None = Field(default=None)


class DictionaryEntry(BaseModel):
    term: str = Field(examples=["Aaron"])
    text: str = Field(
        examples=["The eldest son of Amram and Jochebed, a daughter of Levi..."]
    )
    source: DictionarySourceRef


class DictionaryResponse(BaseModel):
    term: str = Field(examples=["Aaron"])
    entries: list[DictionaryEntry]


class DictionarySourceInfo(BaseModel):
    id: str = Field(examples=["isbe"])
    title: str = Field(
        examples=["International Standard Bible Encyclopaedia (1915), ed. James Orr"]
    )
    rights: str = Field(examples=["Public Domain"])
    rights_basis: str | None = Field(default=None)
    attribution: str | None = Field(default=None)
    entries: int = Field(examples=[9349])


def _word_number_or_400(value: str) -> str:
    """Canonical Strong's number: letter + digits, e.g. 'G3056'."""
    m = re.fullmatch(r"([GH])0*(\d+)", value.strip().upper())
    if not m:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Strong's number '{value}'. Use a Greek (G) or "
            "Hebrew (H) number, e.g. G3056 or H430.",
        )
    return f"{m.group(1)}{int(m.group(2))}"


def _lexicon_source_or_400(source: str | None) -> str | None:
    if source is None:
        return None
    if source not in study.LEXICON_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown lexicon source '{source}'. "
            f"Valid sources: {', '.join(study.LEXICON_SOURCES)}.",
        )
    return source


def _word_entry(row: dict, canonical: str) -> WordEntry:
    return WordEntry(
        number=canonical,
        language=row["language"],
        lemma=row["lemma"],
        transliteration=row["transliteration"],
        definition=row["definition"],
        gloss=row["gloss"],
        source=WordSourceRef(
            id=row["source_id"],
            title=row["source_title"],
            rights=row["source_rights"],
            attribution=row["source_attribution"],
        ),
    )


@app.get(
    "/v1/word/sources",
    response_model=list[LexiconSourceInfo],
    tags=["study"],
    summary="Lexicon sources and rights",
    description=(
        "Every word-study lexicon behind /v1/word: entry counts plus the "
        "rights and attribution metadata each source requires. Strong's "
        "(1890) is public domain; BDB (OpenScriptures) and the four "
        "STEPBible lexicons are CC BY 4.0 and must be attributed as shown."
    ),
    dependencies=[Depends(require_api_key)],
)
def list_word_sources() -> list[LexiconSourceInfo]:
    return [
        LexiconSourceInfo(
            id=r["source_id"],
            title=r["title"],
            rights=r["rights"],
            rights_basis=r["rights_basis"],
            attribution=r["attribution"],
            entries=r["entries"],
        )
        for r in study.get_lexicon_sources()
    ]


# --------------------------------------------------------------------------- #
# Interlinear (v3): word-by-word original-language data per verse
# --------------------------------------------------------------------------- #


class InterlinearWord(BaseModel):
    position: int = Field(examples=[1])
    word: str = Field(examples=["Ἐν"])
    transliteration: str | None = Field(default=None, examples=["En"])
    gloss: str | None = Field(default=None, examples=["in/on/among"])
    strongs: str | None = Field(default=None, examples=["G1722"])
    morphology: str | None = Field(default=None, examples=["PREP"])
    lemma: str | None = Field(default=None, examples=["ἐν"])


class InterlinearVariantGroup(BaseModel):
    kind: str = Field(
        examples=["KO"],
        description="STEPBible edition sigla for this variant reading "
        "(N=Nestle-Aland/SBL, K=KJV/Textus Receptus, O=other manuscripts).",
    )
    words: list[InterlinearWord]


class InterlinearSourceRef(BaseModel):
    id: str = Field(examples=["step_tagnt"])
    title: str = Field(
        examples=["STEPBible TAGNT (Translators Amalgamated Greek NT)"]
    )
    rights: str = Field(examples=["CC BY 4.0"])
    rights_basis: str | None = Field(default=None)


class InterlinearResponse(BaseModel):
    book: str = Field(examples=["John"])
    chapter: int = Field(examples=[1])
    verse: int = Field(examples=[1])
    testament: str | None = Field(default=None, examples=["NT"])
    reading: str = Field(
        examples=["main"],
        description="'main' = the selected critical-text reading; "
        "'variant' = the verse is absent from the critical text, so only "
        "Byzantine/Majority-tradition variant readings are returned.",
    )
    note: str | None = Field(default=None)
    words: list[InterlinearWord]
    variants: list[InterlinearVariantGroup]
    sources: list[InterlinearSourceRef]


def _interlinear_word(r: dict) -> InterlinearWord:
    return InterlinearWord(
        position=r["position"],
        word=r["word"],
        transliteration=r["transliteration"],
        gloss=r["gloss"],
        strongs=r["strongs"],
        morphology=r["morphology"],
        lemma=r["lemma"],
    )


@app.get(
    "/v1/interlinear/{book}/{chapter}/{verse}",
    response_model=InterlinearResponse,
    tags=["study"],
    summary="Interlinear: original-language words for a verse",
    description=(
        "Word-by-word Hebrew (OT) or Greek (NT) for one KJV verse: the "
        "original word, transliteration, English gloss, Strong's number, "
        "morphology, and lemma, in reading order. The Greek reading follows "
        "the Nestle-Aland/SBL critical text; the Hebrew follows the "
        "Leningrad Codex with the translators' Qere choices. Forty-two "
        "KJV verses absent from the critical text (e.g. Mark 16:9-20, "
        "John 7:53-8:11) return reading='variant' with the "
        "Byzantine/Majority-tradition words instead. Source data: STEPBible "
        "TAGNT/TAHOT (CC BY 4.0, attribution in `sources`)."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_interlinear(
    book: str,
    chapter: int,
    verse: int,
) -> InterlinearResponse:
    canonical = resolve_book(book)
    if canonical is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown book '{book}'.",
        )
    parsed = _parse_or_400(f"{canonical} {chapter}:{verse}", "KJV")
    data = study.get_interlinear(parsed.book, chapter, verse)
    if data["reading"] == "none":
        raise HTTPException(
            status_code=404,
            detail=f"No interlinear data for '{parsed.display}'.",
        )
    note = None
    if data["reading"] == "variant":
        note = (
            "This verse is absent from the Nestle-Aland/SBL critical text "
            "(Greek) or the Leningrad Codex (Hebrew); only variant-tradition "
            "readings are available, grouped by manuscript tradition."
        )
    return InterlinearResponse(
        book=data["book"],
        chapter=data["chapter"],
        verse=data["verse"],
        testament=data["testament"],
        reading=data["reading"],
        note=note,
        words=[_interlinear_word(r) for r in data["words"]],
        variants=[
            InterlinearVariantGroup(
                kind=g["kind"],
                words=[_interlinear_word(r) for r in g["words"]],
            )
            for g in data["variants"]
        ],
        sources=[
            InterlinearSourceRef(
                id=s["source_id"],
                title=s["title"],
                rights=s["rights"],
                rights_basis=s["rights_basis"],
            )
            for s in data["sources"]
        ],
    )


# --------------------------------------------------------------------------- #
# Phos Intensive Verse Study (v3): one-call composite for a single verse
# --------------------------------------------------------------------------- #


class VerseStudyTranslation(BaseModel):
    code: str = Field(examples=["BSB"])
    present: bool = Field(examples=[True])
    text: str | None = Field(examples=["For God so loved the world ..."])


class VerseStudyKeyWord(BaseModel):
    position: int = Field(examples=[3])
    word: str = Field(examples=["ἠγάπησεν"])
    transliteration: str | None = Field(examples=["ēgapēsen"])
    strongs: str = Field(examples=["G25"])
    gloss: str = Field(examples=["to love"])
    morphology: str = Field(examples=["V-AAI-3S"])
    lemma: str | None = Field(examples=["ἀγαπάω"])
    definition: str = Field(examples=["to love (in a social or moral sense)"])
    definition_source: str = Field(examples=["step_tbesg"])


class VerseStudyCrossRefItem(BaseModel):
    ref: str = Field(examples=["Romans 5:8"])
    text: str | None = Field(examples=["But God demonstrates ..."])


class VerseStudyCrossRefs(BaseModel):
    total: int = Field(examples=[19])
    refs: list[VerseStudyCrossRefItem]


class VerseStudyDevotional(BaseModel):
    source: str = Field(examples=["daily_light"])
    source_title: str = Field(examples=["Daily Light on the Daily Path"])
    part: str = Field(examples=["morning"])
    title: str | None = Field(examples=["God so loved the world ..."])
    anchor_ref: str = Field(examples=["John 3:16"])
    text: str = Field(examples=["..."])
    truncated: bool = Field(examples=[True])
    full_length: int = Field(examples=[1876])
    match_kind: str = Field(examples=["exact"])


class VerseStudyPrayer(BaseModel):
    office: str = Field(examples=["morning_prayer"])
    edition: str = Field(examples=["bcp1662"])
    label: str | None = Field(examples=["The second Collect for Peace"])
    speaker: str | None = Field(examples=[None])
    text: str = Field(examples=["O God who art the Author of peace ..."])
    match_kind: str = Field(examples=["keyword"])
    matched_keywords: list[str] = Field(examples=[["love", "god", "life"]])


class VerseStudyResponse(BaseModel):
    ref: str = Field(examples=["John 3:16"])
    book: str = Field(examples=["John"])
    chapter: int = Field(examples=[3])
    verse: int = Field(examples=[16])
    testament: str = Field(examples=["NT"])
    translations: list[VerseStudyTranslation]
    key_words: list[VerseStudyKeyWord]
    key_words_note: str | None = Field(examples=[None])
    cross_refs: VerseStudyCrossRefs
    commentaries: list[CommentaryItem]
    devotionals: list[VerseStudyDevotional]
    prayer: VerseStudyPrayer | None
    sources: list[StudySourceRef]
    rights_note: str
    brief: bool = Field(
        default=False,
        description="True when the response was trimmed for brief mode.",
    )
    full_hint: str | None = Field(
        default=None,
        description="How to fetch the full intensive when brief is true.",
    )


_VERSE_STUDY_DEFAULT_TRANSLATIONS = ("BSB", "KJV", "WEB")
_VERSE_STUDY_MAX_TRANSLATIONS = 4
_VERSE_STUDY_KEYWORD_CAP = 12
_VERSE_STUDY_DEF_PRIORITY = (
    "bdb",
    "step_tbesh",
    "step_tbesg",
    "step_tflsj",
    "step_tflsjx",
)
_VERSE_STUDY_DEF_FALLBACK_LEN = 250
_VERSE_STUDY_DEVOTIONAL_ORDER = (
    "spurgeon",
    "daily_light",
    "my_utmost",
    "imitation_christ",
    "practice_presence",
)
_VERSE_STUDY_PRAYER_STOPWORDS = frozenset(
    {
        # articles, prepositions, conjunctions
        "the", "a", "an", "to", "of", "in", "on", "at", "by", "for",
        "with", "from", "as", "or", "and", "but", "nor", "so", "if",
        "than", "then", "when", "while", "because", "until", "though",
        "although",
        # pronouns
        "i", "me", "my", "mine", "we", "us", "our", "ours", "you",
        "your", "yours", "he", "him", "his", "she", "her", "hers",
        "it", "its", "they", "them", "their", "theirs", "this",
        "that", "these", "those", "who", "whom", "whose", "which",
        "what",
        # auxiliary and common verbs
        "be", "am", "is", "are", "was", "were", "been", "being",
        "do", "does", "did", "done", "doing", "have", "has", "had",
        "having", "will", "would", "shall", "should", "can", "could",
        "may", "might", "must", "ought",
        # adverbs and fillers
        "not", "no", "yes", "very", "too", "also", "just", "only",
        "even", "still", "yet", "now", "here", "there", "how", "why",
        "where",
    }
)
_VERSE_STUDY_KEYWORDS_RE = re.compile(r"[^a-z]+")


def _strongs_base(number: str) -> str:
    """'G0025' -> 'G25': the base form /v1/word accepts."""
    number = (number or "").strip()
    if len(number) > 1 and number[1:].isdigit():
        return number[0] + str(int(number[1:]))
    return number


def _is_key_word(morphology: str | None, testament: str) -> bool:
    """Content words only: nouns, verbs, adjectives.

    Greek: the part-of-speech tag is the morphology string up to the first
    ``-`` (for ``+``-compounds such as ``CONJ + G1565=D``, the text before
    the first ``+``); it must be exactly ``N``, ``V``, or ``A``. Hebrew:
    the morphology is ``/``-separated segments; after stripping one
    leading ``H`` per segment, any segment starting with ``N``, ``V``,
    or ``A`` qualifies.
    """
    if not morphology:
        return False
    if testament == "NT":
        pos = morphology.split("+", 1)[0].split("-", 1)[0].strip()
        return pos in ("N", "V", "A")
    for segment in morphology.split("/"):
        seg = segment[1:] if segment.startswith("H") else segment
        if seg and seg[0] in ("N", "V", "A"):
            return True
    return False


def _cut_words(text: str, max_len: int) -> str:
    """Truncate to max_len at a word boundary, appending an ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def _key_word_definition(canonical: str) -> tuple[str, str]:
    """One short lexicon definition for a Strong's number.

    First non-empty gloss from the CC BY 4.0 lexicons (bdb, step_tbesh,
    step_tbesg, step_tflsj, step_tflsjx), in that order; fallback is the
    public-domain Strong's definition truncated to 250 characters.
    Returns (definition, source_id).
    """
    by_source: dict[str, dict] = {}
    for entry in study.lookup_word(canonical):
        by_source.setdefault(entry["source_id"], entry)
    for source_id in _VERSE_STUDY_DEF_PRIORITY:
        entry = by_source.get(source_id)
        if not entry:
            continue
        gloss = (entry.get("gloss") or "").strip()
        if gloss:
            return gloss, source_id
        definition = (entry.get("definition") or "").strip()
        if definition:
            return definition, source_id
    entry = by_source.get("strongs")
    if entry and (entry.get("definition") or "").strip():
        return (
            _cut_words(
                entry["definition"].strip(), _VERSE_STUDY_DEF_FALLBACK_LEN
            ),
            "strongs",
        )
    return "", "strongs"


@lru_cache(maxsize=1)
def _verse_study_devotionals() -> list[dict]:
    """All devotionals with anchor_ref pre-parsed into (book, spans) parts.

    Parsed once per process against KJV bounds; unparseable anchor parts
    are skipped.
    """
    bounds = db.get_bounds("KJV")
    out = []
    for row in study.all_devotionals():
        parts = []
        for piece in (row["anchor_ref"] or "").split(";"):
            piece = piece.strip()
            if not piece:
                continue
            try:
                parsed = parse_reference(piece, bounds)
            except RefError:
                continue
            parts.append({"book": parsed.book, "spans": parsed.spans})
        out.append(
            {
                "id": row["id"],
                "source_id": row["source_id"],
                "part": row["part"],
                "title": row["title"],
                "anchor_ref": row["anchor_ref"],
                "body": row["body"],
                "parts": parts,
                "anchor_count": len(parts),
            }
        )
    return out


def _devotional_part_matches(
    parts: list[dict], book: str, chapter: int, verse: int, nearby: bool
) -> bool:
    for part in parts:
        if part["book"] != book:
            continue
        for ch, vs, ve in part["spans"]:
            if nearby:
                if ch == chapter and vs <= verse + 3 and ve >= verse - 3:
                    return True
            elif ch == chapter and vs <= verse <= ve:
                return True
    return False


def _verse_study_devotional_order(dev: dict) -> tuple[int, int, int]:
    try:
        priority = _VERSE_STUDY_DEVOTIONAL_ORDER.index(dev["source_id"])
    except ValueError:
        priority = len(_VERSE_STUDY_DEVOTIONAL_ORDER)
    return (dev["anchor_count"], priority, dev["id"])


def _verse_study_devotionals_for(
    book: str, chapter: int, verse: int
) -> list[VerseStudyDevotional]:
    srcs = _study_sources()
    all_dev = _verse_study_devotionals()
    exact = sorted(
        (
            d
            for d in all_dev
            if _devotional_part_matches(d["parts"], book, chapter, verse, False)
        ),
        key=_verse_study_devotional_order,
    )[:3]
    if exact:
        chosen, match_kind = exact, "exact"
    else:
        chosen, match_kind = sorted(
            (
                d
                for d in all_dev
                if _devotional_part_matches(
                    d["parts"], book, chapter, verse, True
                )
            ),
            key=_verse_study_devotional_order,
        )[:3], "nearby"
    items = []
    for dev in chosen:
        excerpt, truncated = _excerpt(dev["body"])
        src = srcs.get(dev["source_id"], {})
        items.append(
            VerseStudyDevotional(
                source=dev["source_id"],
                source_title=src.get("title", dev["source_id"]),
                part=dev["part"],
                title=dev["title"],
                anchor_ref=dev["anchor_ref"],
                text=excerpt,
                truncated=truncated,
                full_length=len(dev["body"]),
                match_kind=match_kind,
            )
        )
    return items


def _prayer_keywords(key_words: list[VerseStudyKeyWord]) -> list[str]:
    """Keyword set from the key words' English glosses.

    Lowercased, split on non-letters, English stopwords dropped.
    """
    keywords: list[str] = []
    seen: set[str] = set()
    for kw in key_words:
        for token in _VERSE_STUDY_KEYWORDS_RE.split((kw.gloss or "").lower()):
            if (
                token
                and token not in _VERSE_STUDY_PRAYER_STOPWORDS
                and token not in seen
            ):
                seen.add(token)
                keywords.append(token)
    return keywords


def _verse_study_prayer(
    office: str, keywords: list[str]
) -> VerseStudyPrayer | None:
    """Keyword-matched prayer from the BCP offices.

    Scores kind='text' blocks of the requested office by the number of
    distinct keywords appearing as case-insensitive substrings (deliberate:
    the 1662 text uses archaic spellings whole-word matching would miss).
    Blocks in the 'opening_rubric' and 'title' sections are directions, not
    prayers, and are excluded from matching. The 1662 book is searched
    first, then 1928; ties break by lowest seq. With no keyword hit, falls
    back to the office opening.
    """
    office_key = f"{office}_prayer"

    def text_blocks(edition: str) -> list[dict]:
        _, blocks = study.prayer_office(edition, office)
        return [
            b
            for b in blocks
            if b["kind"] == "text"
            and b.get("section") not in ("opening_rubric", "title")
        ]

    def best_hit(blocks: list[dict]) -> tuple[dict | None, list[str]]:
        best: dict | None = None
        best_hits: list[str] = []
        for block in blocks:
            text_low = block["text"].lower()
            hits = [kw for kw in keywords if kw in text_low]
            if len(hits) > len(best_hits):
                best, best_hits = block, hits
        return best, best_hits

    blocks_1662 = text_blocks("1662")
    best, hits = best_hit(blocks_1662)
    edition = "bcp1662"
    if not hits:
        best, hits = best_hit(text_blocks("1928"))
        if hits:
            edition = "bcp1928"
    if hits and best is not None:
        return VerseStudyPrayer(
            office=office_key,
            edition=edition,
            label=best["label"],
            speaker=best["speaker"],
            text=best["text"],
            match_kind="keyword",
            matched_keywords=hits,
        )
    if blocks_1662:
        opening = blocks_1662[0]
        return VerseStudyPrayer(
            office=office_key,
            edition="bcp1662",
            label=opening["label"],
            speaker=opening["speaker"],
            text=opening["text"],
            match_kind="office_opening",
            matched_keywords=[],
        )
    return None


def _verse_study_rights_note(
    testament: str, definition_sources: list[str]
) -> str:
    """CC BY 4.0 attribution for the interlinear words and any CC BY 4.0
    key-word definitions, plus the Phos modification record."""
    srcs = _study_sources()
    interlinear_id = "step_tagnt" if testament == "NT" else "step_tahot"
    interlinear_title = srcs.get(interlinear_id, {}).get(
        "title", interlinear_id
    )
    note = (
        f"Interlinear word data: {interlinear_title} "
        "(https://www.stepbible.org), data created by STEPBible.org based "
        "on work at Tyndale House, Cambridge, used under CC BY 4.0 "
        "(https://creativecommons.org/licenses/by/4.0/)."
    )
    cc_defs = [
        s for s in definition_sources if srcs.get(s, {}).get("rights") == "CC BY 4.0"
    ]
    if cc_defs:
        titles = "; ".join(srcs[s]["title"] for s in cc_defs)
        note += (
            f" Key-word definitions: {titles}, used under CC BY 4.0 "
            "(https://creativecommons.org/licenses/by/4.0/)."
        )
    note += (
        " Phos modifications: selection of the Nestle-Aland/SBL "
        "critical-text reading (Greek) or the Leningrad Codex with the "
        "translators' Qere choices (Hebrew), mapped to KJV versification. "
        "All other texts on this page are public domain."
    )
    return note


@app.get(
    "/v1/verse-study/{book}/{chapter}/{verse}",
    response_model=VerseStudyResponse,
    tags=["study"],
    summary="Phos Intensive Verse Study: everything for one verse",
    description=(
        "One-call composite for a single verse: the verse in up to four "
        "translations, the most important original-language words with "
        "their meanings, the top cross-references, commentary excerpts "
        "from all eight commentary sources, devotionals anchored to the "
        "verse (or nearby), and a related prayer from the Book of Common "
        "Prayer. Interlinear word data: STEPBible TAGNT/TAHOT and STEPBible "
        "lexicon definitions are used under CC BY 4.0 "
        "(https://creativecommons.org/licenses/by/4.0/); full attribution "
        "in `sources` and `rights_note`."
    ),
    dependencies=[Depends(require_api_key)],
)
def verse_study(
    book: str,
    chapter: int,
    verse: int,
    translations: Annotated[
        str,
        Query(
            description=(
                "Comma-separated translation codes (max 4). "
                "Each is validated against the translation registry."
            ),
            examples=["BSB,KJV,WEB"],
        ),
    ] = "BSB,KJV,WEB",
    office: Annotated[
        str,
        Query(
            description="Prayer office the prayer is drawn from.",
            examples=["morning"],
        ),
    ] = "morning",
    brief: Annotated[
        bool,
        Query(
            description=(
                "Brief mode: trims the composite to a chat-friendly size "
                "(top 4 key words, top 4 cross-refs, 2 commentary excerpts, "
                "1 devotional, no prayer text). The full intensive is "
                "available with brief=false."
            ),
        ),
    ] = False,
) -> VerseStudyResponse:
    canonical = resolve_book(book)
    if canonical is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown book '{book}'.",
        )
    parsed = _parse_or_400(f"{canonical} {chapter}:{verse}", "KJV")

    office = (office or "").strip().lower()
    if office not in ("morning", "evening"):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown office '{office}'. Valid offices: morning, evening.",
        )

    codes = [
        c.strip().upper() for c in (translations or "").split(",") if c.strip()
    ]
    if not codes:
        raise HTTPException(
            status_code=400,
            detail="Query parameter 'translations' must name at least one "
            "translation.",
        )
    if len(codes) > _VERSE_STUDY_MAX_TRANSLATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"At most {_VERSE_STUDY_MAX_TRANSLATIONS} translations "
            f"are allowed; got {len(codes)}.",
        )
    for code in codes:
        _translation_or_400(code)

    t_items: list[VerseStudyTranslation] = []
    any_present = False
    for code in codes:
        row = None
        try:
            per = parse_reference(
                f"{canonical} {chapter}:{verse}", db.get_bounds(code)
            )
            row = db.get_verse(code, per.book, chapter, verse)
        except RefError:
            row = None
        present = row is not None
        any_present = any_present or present
        t_items.append(
            VerseStudyTranslation(
                code=code, present=present, text=row["text"] if row else None
            )
        )
    if not any_present:
        raise HTTPException(
            status_code=404,
            detail=f"'{parsed.display}' is not present in any of the "
            f"requested translations.",
        )

    interlinear = study.get_interlinear(parsed.book, chapter, verse)
    testament = interlinear["testament"]
    if testament is None:
        order = db.get_bounds("KJV")[parsed.book]["order"]
        testament = "OT" if order < 39 else "NT"

    key_words: list[VerseStudyKeyWord] = []
    key_words_note: str | None = None
    definition_sources: list[str] = []
    if interlinear["words"]:
        for row in interlinear["words"]:
            if not _is_key_word(row["morphology"], testament):
                continue
            if len(key_words) >= _VERSE_STUDY_KEYWORD_CAP:
                break
            strongs = _strongs_base(row["strongs"])
            definition, def_source = _key_word_definition(strongs)
            if def_source not in definition_sources:
                definition_sources.append(def_source)
            key_words.append(
                VerseStudyKeyWord(
                    position=row["position"],
                    word=row["word"],
                    transliteration=row["transliteration"],
                    strongs=strongs,
                    gloss=row["gloss"],
                    morphology=row["morphology"],
                    lemma=row["lemma"],
                    definition=definition,
                    definition_source=def_source,
                )
            )
    elif interlinear["reading"] == "variant":
        key_words_note = (
            "Interlinear data for this verse exists in variant manuscript "
            "traditions only; see GET "
            f"/v1/interlinear/{parsed.book}/{chapter}/{verse}."
        )

    book_order = db.get_bounds("KJV")[parsed.book]["order"]
    xref_rows = study.crossrefs_for(book_order, chapter, verse)
    first_code = codes[0]
    cross_refs = VerseStudyCrossRefs(
        total=len(xref_rows),
        refs=[
            VerseStudyCrossRefItem(
                ref=f"{r['ref_book']} {r['ref_chapter']}:{r['ref_verse']}",
                text=(
                    db.get_verse(
                        first_code,
                        r["ref_book"],
                        r["ref_chapter"],
                        r["ref_verse"],
                    ) or {}
                ).get("text"),
            )
            for r in xref_rows[:8]
        ],
    )

    commentaries = _covering_commentaries("KJV", parsed, None, full=False)
    devotionals = _verse_study_devotionals_for(parsed.book, chapter, verse)
    prayer = _verse_study_prayer(
        office, _prayer_keywords(key_words)
    )

    srcs = _study_sources()
    sources: list[StudySourceRef] = []
    seen_sources: set[str] = set()

    def add_source(source_id: str, title: str, rights: str) -> None:
        if source_id not in seen_sources:
            seen_sources.add(source_id)
            sources.append(
                StudySourceRef(id=source_id, title=title, rights=rights)
            )

    for code in codes:
        add_source(code, TRANSLATIONS[code]["name"], "Public Domain")
    interlinear_id = "step_tagnt" if testament == "NT" else "step_tahot"
    if interlinear_id in srcs:
        add_source(
            interlinear_id,
            srcs[interlinear_id]["title"],
            srcs[interlinear_id]["rights"],
        )
    for source_id in definition_sources:
        if source_id in srcs:
            add_source(
                source_id, srcs[source_id]["title"], srcs[source_id]["rights"]
            )
    add_source("tsk", srcs["tsk"]["title"], srcs["tsk"]["rights"])
    for item in commentaries:
        if item.source in srcs:
            add_source(
                item.source,
                srcs[item.source]["title"],
                srcs[item.source]["rights"],
            )
    for dev in devotionals:
        if dev.source in srcs:
            add_source(
                dev.source, srcs[dev.source]["title"], srcs[dev.source]["rights"]
            )
    if prayer is not None and prayer.edition in srcs:
        add_source(
            prayer.edition,
            srcs[prayer.edition]["title"],
            srcs[prayer.edition]["rights"],
        )

    full_hint: str | None = None
    if brief:
        key_words = key_words[:4]
        cross_refs = VerseStudyCrossRefs(
            total=cross_refs.total, refs=cross_refs.refs[:4]
        )
        commentaries = commentaries[:2]
        devotionals = devotionals[:1]
        prayer = None
        full_hint = (
            "Full intensive available: GET "
            f"/v1/verse-study/{parsed.book}/{chapter}/{verse}"
        )

    return VerseStudyResponse(
        ref=parsed.display,
        book=parsed.book,
        chapter=chapter,
        verse=verse,
        testament=testament,
        translations=t_items,
        key_words=key_words,
        key_words_note=key_words_note,
        cross_refs=cross_refs,
        commentaries=commentaries,
        devotionals=devotionals,
        prayer=prayer,
        sources=sources,
        rights_note=_verse_study_rights_note(testament, definition_sources),
        brief=brief,
        full_hint=full_hint,
    )


@app.get(
    "/v1/word",
    response_model=WordResponse,
    tags=["study"],
    summary="Word study by Strong's number",
    description=(
        "Lexicon entries for one Strong's number (e.g. G3056, H430; "
        "case-insensitive, leading zeros accepted). Omit `source` to get "
        "entries from every lexicon that has the number; Strong's Greek "
        "covers 89.1% of G1-G5624 from OCR, and STEPBible's Greek lexicons "
        "fill the gaps. Every entry carries its source's rights and "
        "attribution."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_word(
    number: Annotated[
        str,
        Query(
            description="Strong's number: G + digits or H + digits.",
            examples=["G3056", "H430"],
        ),
    ],
    source: Annotated[
        str | None,
        Query(
            description=(
                "Lexicon source: strongs, bdb, step_tbesh, step_tbesg, "
                "step_tflsj, step_tflsjx. Omit for all sources."
            ),
            examples=["strongs"],
        ),
    ] = None,
) -> WordResponse:
    canonical = _word_number_or_400(number)
    src = _lexicon_source_or_400(source)
    rows = study.lookup_word(canonical, src)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No lexicon entry for '{canonical}'"
            + (f" in source '{src}'." if src else " in any lexicon source."),
        )
    language = "greek" if canonical.startswith("G") else "hebrew"
    return WordResponse(
        number=canonical,
        language=language,
        entries=[_word_entry(r, canonical) for r in rows],
    )


def _dictionary_source_or_400(source: str | None) -> str | None:
    if source is None:
        return None
    if source not in study.DICTIONARY_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown dictionary source '{source}'. "
            f"Valid sources: {', '.join(study.DICTIONARY_SOURCES)}.",
        )
    return source


def _dictionary_entry(row: dict) -> DictionaryEntry:
    return DictionaryEntry(
        term=row["term"],
        text=row["text"],
        source=DictionarySourceRef(
            id=row["source_id"],
            title=row["source_title"],
            rights=row["source_rights"],
            attribution=row["source_attribution"],
        ),
    )


@app.get(
    "/v1/dictionary/sources",
    response_model=list[DictionarySourceInfo],
    tags=["study"],
    summary="Dictionary sources and rights",
    description=(
        "Every Bible dictionary behind /v1/dictionary: entry counts plus the "
        "rights metadata each source requires. All four are public domain: "
        "Easton's (1897), ISBE 1915, Nave's Topical Bible (1896), and "
        "Torrey's New Topical Textbook (1897)."
    ),
    dependencies=[Depends(require_api_key)],
)
def list_dictionary_sources() -> list[DictionarySourceInfo]:
    return [
        DictionarySourceInfo(
            id=r["source_id"],
            title=r["title"],
            rights=r["rights"],
            rights_basis=r["rights_basis"],
            attribution=r["attribution"],
            entries=r["entries"],
        )
        for r in study.get_dictionary_sources()
    ]


@app.get(
    "/v1/dictionary",
    response_model=DictionaryResponse,
    tags=["study"],
    summary="Dictionary lookup by term",
    description=(
        "Dictionary entries for one term (e.g. Aaron, Faith; case-insensitive). "
        "Omit `source` to get entries from every dictionary that has the term. "
        "Every entry carries its source's rights metadata."
    ),
    dependencies=[Depends(require_api_key)],
)
def get_dictionary(
    term: Annotated[
        str,
        Query(
            description="Dictionary term or topic.",
            examples=["Aaron", "Faith"],
        ),
    ],
    source: Annotated[
        str | None,
        Query(
            description=(
                "Dictionary source: easton, isbe, naves, torrey. "
                "Omit for all sources."
            ),
            examples=["easton"],
        ),
    ] = None,
) -> DictionaryResponse:
    if not term or not term.strip():
        raise HTTPException(
            status_code=400,
            detail="Query parameter 'term' is required and must not be blank.",
        )
    src = _dictionary_source_or_400(source)
    rows = study.lookup_dictionary(term, src)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No dictionary entry for '{term.strip()}'"
            + (f" in source '{src}'." if src else " in any dictionary source."),
        )
    return DictionaryResponse(
        term=term.strip(),
        entries=[_dictionary_entry(r) for r in rows],
    )
