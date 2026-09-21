"""Pytest fragment: practice_presence devotional batch (batch 3).

Not collected directly; assembled into the API suite after the merge.
Requires the coordinator's allowlist change in api/study.py:
DEVOTIONAL_SOURCES must include "practice_presence", or these tests
get HTTP 400 (unknown source).

Uses the shared client/auth fixtures from conftest.py, following the
/devotional patterns in test_study.py.
"""

import random

SOURCE = "practice_presence"
ROW_COUNT = 20  # Preface + 4 Conversations + 15 Letters

# Seeded spot-check days, drawn once with the batch seed.
_seed_rng = random.Random(20260920)
SEED_DAYS = sorted(_seed_rng.sample(range(1, ROW_COUNT + 1), 3))
assert SEED_DAYS == [5, 9, 19], SEED_DAYS

SPOT_CHECKS = {
    5: (
        "Fourth Conversation",
        "He discoursed with me very frequently, and with great openness of\n"
        "heart concerni",
    ),
    9: (
        "Fourth Letter",
        "I have taken this opportunity to communicate to you the sentiments "
        "of\none of our",
    ),
    19: (
        "Fourteenth Letter",
        "_To the Same_.\n\n"
        "I render thanks to our LORD for having relieved you a little,\nac",
    ),
}


def _get_day(client, auth, day):
    # Days 1..20 are 2026-01-01..2026-01-20 (2026 is not a leap year,
    # so day-of-year equals the January date).
    r = client.get(
        "/v1/devotional?date=2026-01-%02d&source=%s" % (day, SOURCE),
        headers=auth,
    )
    assert r.status_code == 200, (day, r.status_code)
    return r.json()


def test_practice_presence_row_count_constant():
    assert ROW_COUNT == 20


def test_practice_presence_days_no_gaps(client, auth):
    seen = []
    for day in range(1, ROW_COUNT + 1):
        body = _get_day(client, auth, day)
        assert body["day"] == day
        assert body["source"] == SOURCE
        assert body["morning"] is not None
        assert body["evening"] is None  # single (morning) entries only
        assert body["morning"]["anchor_ref"] == ""
        seen.append(body["day"])
    assert seen == list(range(1, ROW_COUNT + 1))


def test_practice_presence_seeded_spot_checks(client, auth):
    for day in SEED_DAYS:
        title, body_prefix = SPOT_CHECKS[day]
        body = _get_day(client, auth, day)
        assert body["morning"]["title"] == title
        assert body["morning"]["body"].startswith(body_prefix), day
