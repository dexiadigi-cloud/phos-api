"""M2b tests: topic/mood discovery, reading plans, progress.

Ref validation mirrors data/validate_refs.py (the build gate): topic refs
are verse-level (every verse key must exist in BSB); plan refs are
chapter-level (chapter must exist; BSB omits some textual-critical verse
keys, e.g. Matthew 17:21, which fetch_spans simply skips).
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

import db
import progress
from parser import RefError, parse_reference

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture()
def _isolated_progress(tmp_path, monkeypatch):
    monkeypatch.setattr(progress, "PROGRESS_PATH", tmp_path / "progress.db")


# --- ref validation (build gate) -------------------------------------------- #

def _bounds():
    return db.get_bounds("BSB")


def test_all_topic_refs_parse_and_exist():
    topics = json.loads((DATA_DIR / "topics.json").read_text())
    assert len(topics["topics"]) >= 60
    bounds = _bounds()
    checked = 0
    for topic in topics["topics"]:
        assert 3 <= len(topic["refs"]) <= 8, topic["id"]
        for ref in topic["refs"]:
            try:
                parsed = parse_reference(ref, bounds)
            except RefError as exc:
                pytest.fail(f"topic '{topic['id']}' ref {ref!r}: {exc}")
            for ch, vs, ve in parsed.spans:
                for v in range(vs, ve + 1):
                    assert db.get_verse("BSB", parsed.book, ch, v) is not None, (
                        f"topic '{topic['id']}' ref {ref!r}: "
                        f"{parsed.book} {ch}:{v} missing from BSB"
                    )
                    checked += 1
    assert checked > 200


def test_all_plan_refs_parse_and_chapters_exist():
    plans = json.loads((DATA_DIR / "plans.json").read_text())
    assert len(plans["plans"]) == 4
    bounds = _bounds()
    for plan in plans["plans"]:
        assert len(plan["schedule"]) == plan["days"]
        for day in plan["schedule"]:
            for ref in day["refs"]:
                try:
                    parsed = parse_reference(ref, bounds)
                except RefError as exc:
                    pytest.fail(f"plan '{plan['id']}' day {day['day']}: {exc}")
                for ch, vs, _ve in parsed.spans:
                    assert db.get_verse("BSB", parsed.book, ch, 1) is not None


def test_plan_schedules_cover_expected_chapters():
    plans = {p["id"]: p for p in json.loads((DATA_DIR / "plans.json").read_text())["plans"]}
    assert plans["bible-in-a-year"]["total_chapters"] == 1189
    assert plans["new-testament-90"]["total_chapters"] == 260
    assert plans["psalms-proverbs-31"]["total_chapters"] == 181
    assert plans["gospels-30"]["total_chapters"] == 89


# --- topics ------------------------------------------------------------------ #

def test_list_topics(client, auth):
    r = client.get("/v1/topics", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 60
    ids = [t["id"] for t in body]
    assert len(ids) == len(set(ids))
    assert "peace" in ids and "gratitude" in ids
    assert all(t["moods"] for t in body)


def test_get_topic(client, auth):
    r = client.get("/v1/topics/peace", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "peace"
    assert body["translation"] == "BSB"
    assert len(body["verses"]) >= 5
    assert all(v["text"].strip() for v in body["verses"])


def test_get_topic_translation(client, auth):
    r = client.get("/v1/topics/peace?translation=KJV", headers=auth)
    assert r.status_code == 200
    assert r.json()["translation"] == "KJV"
    assert r.json()["verses"]


def test_get_topic_unknown(client, auth):
    r = client.get("/v1/topics/not-a-topic", headers=auth)
    assert r.status_code == 404


def test_get_topic_bad_translation(client, auth):
    r = client.get("/v1/topics/peace?translation=XYZ", headers=auth)
    assert r.status_code == 400


# --- moods ------------------------------------------------------------------- #

def test_list_moods(client, auth):
    r = client.get("/v1/moods", headers=auth)
    assert r.status_code == 200
    body = r.json()
    by_mood = {m["mood"]: m for m in body}
    assert "anxious" in by_mood and "grateful" in by_mood
    assert "peace" in by_mood["anxious"]["topics"]


def test_get_mood(client, auth):
    r = client.get("/v1/moods/anxious", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["mood"] == "anxious"
    assert body["topics"]
    assert all(t["verses"] for t in body["topics"])


def test_get_mood_case_insensitive(client, auth):
    r = client.get("/v1/moods/Anxious", headers=auth)
    assert r.status_code == 200
    assert r.json()["mood"] == "anxious"


def test_get_mood_unknown(client, auth):
    r = client.get("/v1/moods/bemused", headers=auth)
    assert r.status_code == 404


# --- reading plans ----------------------------------------------------------- #

def test_list_plans(client, auth):
    r = client.get("/v1/reading-plans", headers=auth)
    assert r.status_code == 200
    body = r.json()
    ids = [p["id"] for p in body]
    assert ids == ["bible-in-a-year", "new-testament-90",
                   "psalms-proverbs-31", "gospels-30"]
    assert all(p["days"] > 0 and p["total_chapters"] > 0 for p in body)


def test_get_plan(client, auth):
    r = client.get("/v1/reading-plans/bible-in-a-year", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body["schedule"]) == 365
    assert body["schedule"][0]["day"] == 1
    assert body["schedule"][0]["refs"] == ["Genesis 1-4"]
    assert body["schedule"][-1]["refs"] == ["Revelation 20-22"]


def test_get_plan_unknown(client, auth):
    r = client.get("/v1/reading-plans/nope", headers=auth)
    assert r.status_code == 404


def test_plan_today_day_one(client, auth):
    today = date.today().isoformat()
    r = client.get(
        f"/v1/reading-plans/gospels-30/today?start_date={today}", headers=auth
    )
    assert r.status_code == 200
    body = r.json()
    assert body["day"] == 1
    assert body["total_days"] == 30
    assert body["passages"][0]["ref"] == "Matthew 1-3"
    verses = body["passages"][0]["verses"]
    assert len(verses) > 50  # three whole chapters
    assert all(v["text"].strip() for v in verses)


def test_plan_today_bad_date(client, auth):
    r = client.get(
        "/v1/reading-plans/gospels-30/today?start_date=not-a-date", headers=auth
    )
    assert r.status_code == 400


def test_plan_today_not_started(client, auth):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = client.get(
        f"/v1/reading-plans/gospels-30/today?start_date={tomorrow}", headers=auth
    )
    assert r.status_code == 400
    assert "not begun" in r.json()["detail"]


def test_plan_today_finished(client, auth):
    long_ago = (date.today() - timedelta(days=400)).isoformat()
    r = client.get(
        f"/v1/reading-plans/gospels-30/today?start_date={long_ago}", headers=auth
    )
    assert r.status_code == 400
    assert "finished" in r.json()["detail"].lower()


def test_plan_today_unknown_plan(client, auth):
    r = client.get("/v1/reading-plans/nope/today?start_date=2026-01-01",
                   headers=auth)
    assert r.status_code == 404


# --- progress ---------------------------------------------------------------- #

def test_checkin_and_progress(client, auth, _isolated_progress):
    start = "2026-01-01"
    for day in (1, 2, 3):
        r = client.post(
            "/v1/reading-plans/gospels-30/checkin",
            headers=auth,
            json={"start_date": start, "day": day},
        )
        assert r.status_code == 200, r.text
        assert r.json()["day"] == day
    r = client.get(
        f"/v1/reading-plans/gospels-30/progress?start_date={start}", headers=auth
    )
    assert r.status_code == 200
    body = r.json()
    assert body["completed_days"] == [1, 2, 3]
    assert body["completed_count"] == 3
    assert body["total_days"] == 30
    assert body["percent"] == 10.0


def test_checkin_idempotent(client, auth, _isolated_progress):
    start = "2026-01-01"
    for _ in range(2):
        r = client.post(
            "/v1/reading-plans/gospels-30/checkin",
            headers=auth,
            json={"start_date": start, "day": 5},
        )
        assert r.status_code == 200
    r = client.get(
        f"/v1/reading-plans/gospels-30/progress?start_date={start}", headers=auth
    )
    assert r.json()["completed_days"] == [5]


def test_progress_empty(client, auth, _isolated_progress):
    r = client.get(
        "/v1/reading-plans/gospels-30/progress?start_date=2026-06-01",
        headers=auth,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["completed_days"] == []
    assert body["percent"] == 0.0


def test_checkin_day_out_of_range(client, auth, _isolated_progress):
    for day in (0, 31, 999):
        r = client.post(
            "/v1/reading-plans/gospels-30/checkin",
            headers=auth,
            json={"start_date": "2026-01-01", "day": day},
        )
        assert r.status_code == 400, day


def test_checkin_bad_date(client, auth, _isolated_progress):
    r = client.post(
        "/v1/reading-plans/gospels-30/checkin",
        headers=auth,
        json={"start_date": "yesterday", "day": 1},
    )
    assert r.status_code == 400


def test_checkin_unknown_plan(client, auth, _isolated_progress):
    r = client.post(
        "/v1/reading-plans/nope/checkin",
        headers=auth,
        json={"start_date": "2026-01-01", "day": 1},
    )
    assert r.status_code == 404


# --- auth -------------------------------------------------------------------- #

def test_new_endpoints_require_auth(client):
    for path in (
        "/v1/topics",
        "/v1/topics/peace",
        "/v1/moods",
        "/v1/moods/anxious",
        "/v1/reading-plans",
        "/v1/reading-plans/gospels-30",
        "/v1/reading-plans/gospels-30/today?start_date=2026-01-01",
        "/v1/reading-plans/gospels-30/progress?start_date=2026-01-01",
    ):
        r = client.get(path)
        assert r.status_code == 401, path
    r = client.post(
        "/v1/reading-plans/gospels-30/checkin",
        json={"start_date": "2026-01-01", "day": 1},
    )
    assert r.status_code == 401
