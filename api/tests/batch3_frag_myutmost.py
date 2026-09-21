"""Pytest fragment: my_utmost devotional batch (batch 3).

Not collected directly; assembled into the API suite after the merge.
Requires the coordinator's allowlist change in api/study.py:
DEVOTIONAL_SOURCES must include "my_utmost", or these tests
get HTTP 400 (unknown source).

Uses the shared client/auth fixtures from conftest.py, following the
/devotional patterns in test_study.py.
"""

import datetime
import random

SOURCE = "my_utmost"
ROW_COUNT = 366  # days 1..366, leap-year convention (Feb 29 = day 60)

# Seeded spot-check days, drawn once with the batch seed.
_seed_rng = random.Random(20260920)
SEED_DAYS = sorted(_seed_rng.sample(range(1, ROW_COUNT + 1), 3))
assert SEED_DAYS == [301, 324, 364], SEED_DAYS

SPOT_CHECKS = {
    301: (
        "The Method Of Missions",
        '"Go ye therefore, and teach [disciple] all nations." '
        "\u2014 Matthew 28:19\n\nJesus Christ did not",
    ),
    324: (
        "When He Is Come",
        '"And when He is come, He will convict the world of sin\u2026" '
        "\u2014 John 16:8\n\nVery few of us know ",
    ),
    364: (
        "Deserter Or Disciple?",
        '"From that time many of His disciples went back, and walked no '
        'more with Him." \u2014 John 6:66',
    ),
}


def _day_to_date(day):
    # 2024 is a leap year: day-of-year maps 1:1 to the API's leap-year day
    # numbering (day 1 = 2024-01-01, day 60 = 2024-02-29, day 366 = 2024-12-31).
    return (datetime.date(2024, 1, 1) + datetime.timedelta(days=day - 1)).isoformat()


def _get_day(client, auth, day):
    r = client.get(
        "/v1/devotional?date=%s&source=%s" % (_day_to_date(day), SOURCE),
        headers=auth,
    )
    assert r.status_code == 200, (day, r.status_code)
    return r.json()


def test_my_utmost_row_count_constant():
    assert ROW_COUNT == 366


def test_my_utmost_days_no_gaps(client, auth):
    seen = []
    for day in range(1, ROW_COUNT + 1):
        body = _get_day(client, auth, day)
        assert body["day"] == day
        assert body["source"] == SOURCE
        assert body["morning"] is not None
        assert body["evening"] is None  # single (morning) entries only
        assert body["morning"]["anchor_ref"].strip()
        assert body["morning"]["title"].strip()
        assert body["morning"]["body"].strip()
        seen.append(body["day"])
    assert seen == list(range(1, ROW_COUNT + 1))


def test_my_utmost_seeded_spot_checks(client, auth):
    for day in SEED_DAYS:
        title, body_prefix = SPOT_CHECKS[day]
        body = _get_day(client, auth, day)
        assert body["morning"]["title"] == title
        assert body["morning"]["body"].startswith(body_prefix), day


def test_my_utmost_feb29_present(client, auth):
    # 2024-02-29 is day 60 in the leap-year convention (same as
    # spurgeon/daily_light).
    body = _get_day(client, auth, 60)
    assert body["day"] == 60
    assert body["morning"] is not None
    assert body["morning"]["title"] == "What Do You Want The Lord To Do For You?"


def test_my_utmost_day_367_absent(client, auth):
    # Day 367 (2025-01-01) is past the last reading: no entry.
    r = client.get(
        "/v1/devotional?date=2025-01-01&source=%s" % SOURCE,
        headers=auth,
    )
    assert r.status_code == 200, r.status_code
    body = r.json()
    assert body["morning"] is None
    assert body["evening"] is None
