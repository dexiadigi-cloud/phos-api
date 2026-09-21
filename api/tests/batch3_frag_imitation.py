"""Pytest fragment: imitation_christ devotional batch (batch 3).

Not collected directly; assembled into the API suite after the merge.
Requires the coordinator's allowlist change in api/study.py:
DEVOTIONAL_SOURCES must include "imitation_christ", or these tests
get HTTP 400 (unknown source).

Uses the shared client/auth fixtures from conftest.py, following the
/devotional patterns in test_study.py.
"""

import datetime
import random
import re

SOURCE = "imitation_christ"
ROW_COUNT = 114  # Book 1: 25 + Book 2: 12 + Book 3: 59 + Book 4: 18

# Seeded spot-check days, drawn once with the batch seed.
_seed_rng = random.Random(20260920)
SEED_DAYS = sorted(_seed_rng.sample(range(1, ROW_COUNT + 1), 3))
assert SEED_DAYS == [76, 81, 91], SEED_DAYS

SPOT_CHECKS = {
    76: (
        "Book 3, Chapter 39: That man must not be immersed in business",
        "\u201cMy Son, always commit thy cause to Me; I will dispose it aright in due\ntime. Wa",
    ),
    81: (
        "Book 3, Chapter 44: Of not troubling ourselves about outward things",
        "\u201cMy Son, in many things it behoveth thee to be ignorant, and to esteem\nthyself a",
    ),
    91: (
        "Book 3, Chapter 54: Of the diverse motions of Nature and of Grace",
        "\u201cMy Son, pay diligent heed to the motions of Nature and of Grace,\nbecause they m",
    ),
}

TITLE_RE = re.compile(r"^Book (\d+), Chapter (\d+): ")

# (book, first_day, chapter_count)
BOOKS = [(1, 1, 25), (2, 26, 12), (3, 38, 59), (4, 97, 18)]


def _day_to_date(day):
    # 2024 is a leap year: day-of-year maps 1:1 to the API's leap-year day
    # numbering (day 1 = 2024-01-01, day 114 = 2024-04-23).
    return (datetime.date(2024, 1, 1) + datetime.timedelta(days=day - 1)).isoformat()


def _get_day(client, auth, day):
    r = client.get(
        "/v1/devotional?date=%s&source=%s" % (_day_to_date(day), SOURCE),
        headers=auth,
    )
    assert r.status_code == 200, (day, r.status_code)
    return r.json()


def _expected_book_chapter(day):
    for book, first, count in BOOKS:
        if first <= day < first + count:
            return book, day - first + 1
    raise AssertionError("day out of range: %d" % day)


def test_imitation_christ_row_count_constant():
    assert ROW_COUNT == 114


def test_imitation_christ_days_no_gaps(client, auth):
    seen = []
    for day in range(1, ROW_COUNT + 1):
        body = _get_day(client, auth, day)
        assert body["day"] == day
        assert body["source"] == SOURCE
        assert body["morning"] is not None
        assert body["evening"] is None  # single (morning) entries only
        assert body["morning"]["anchor_ref"] == ""
        assert body["morning"]["body"].strip()
        seen.append(body["day"])
    assert seen == list(range(1, ROW_COUNT + 1))


def test_imitation_christ_title_sequence_ordered(client, auth):
    for day in range(1, ROW_COUNT + 1):
        body = _get_day(client, auth, day)
        title = body["morning"]["title"]
        m = TITLE_RE.match(title)
        assert m, (day, title)
        book, chapter = _expected_book_chapter(day)
        assert (int(m.group(1)), int(m.group(2))) == (book, chapter), (day, title)


def test_imitation_christ_seeded_spot_checks(client, auth):
    for day in SEED_DAYS:
        title, body_prefix = SPOT_CHECKS[day]
        body = _get_day(client, auth, day)
        assert body["morning"]["title"] == title
        assert body["morning"]["body"].startswith(body_prefix), day


def test_imitation_christ_day_115_absent(client, auth):
    # Day 115 (2024-04-24) is past the last chapter: no entry.
    body = _get_day(client, auth, 115)
    assert body["day"] == 115
    assert body["morning"] is None
    assert body["evening"] is None
