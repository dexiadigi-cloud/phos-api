"""API tests for v2 study endpoints: study bundle, commentary, cross-refs,
devotional, prayer, memory pack."""

import re


# --- auth ------------------------------------------------------------------- #

def test_study_endpoints_reject_missing_key(client):
    for path in (
        "/v1/study?ref=Ps+23:1",
        "/v1/commentary?ref=Gen+1:1",
        "/v1/cross-refs?ref=Ps+23:1",
        "/v1/devotional?date=2026-09-20",
        "/v1/prayer?office=morning",
        "/v1/memory-pack?topic=peace",
    ):
        r = client.get(path)
        assert r.status_code == 401, path


# --- /v1/study -------------------------------------------------------------- #

def test_study_bundle_happy_path(client, auth):
    r = client.get("/v1/study?ref=Ps+23:1", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["ref"] == "Psalms 23:1"
    assert body["book"] == "Psalms"
    assert len(body["verses"]) == 1
    assert "shepherd" in body["verses"][0]["text"]
    # cross-refs: capped per verse, total reported
    assert len(body["cross_refs"]) == 1
    cr = body["cross_refs"][0]
    assert cr["chapter"] == 23 and cr["verse"] == 1
    assert cr["total"] >= len(cr["refs"])
    assert len(cr["refs"]) <= 25
    assert any("Ezekiel 34:11" in x for x in cr["refs"])
    # commentaries: OT sources present, incl. whole-chapter MH entry
    # (Barnes' transcription is NT-only, so no barnes_nt here)
    sources = {c["source"] for c in body["commentaries"]}
    assert {"matthew_henry", "jfb"} <= sources
    assert "barnes_nt" not in sources
    mh_ranges = [c["ref_range"] for c in body["commentaries"]
                 if c["source"] == "matthew_henry"]
    assert "Psalms 23" in mh_ranges  # whole-chapter comment matched the verse
    assert any(c["truncated"] for c in body["commentaries"])
    assert "public domain" in body["rights_note"].lower()
    assert {s["id"] for s in body["sources"]} >= {"tsk", "matthew_henry"}


def test_study_bundle_nt_includes_barnes(client, auth):
    # A NT reference pulls in all three commentaries, Barnes included.
    r = client.get("/v1/study?ref=Romans+8:28", headers=auth)
    assert r.status_code == 200
    sources = {c["source"] for c in r.json()["commentaries"]}
    assert {"matthew_henry", "jfb", "barnes_nt"} <= sources


def test_study_bad_ref_400(client, auth):
    r = client.get("/v1/study?ref=NotABook+99:99", headers=auth)
    assert r.status_code == 400


def test_study_missing_verse_404(client, auth):
    # WEB omits Acts 8:37 for textual-critical reasons (M1-verified).
    r = client.get("/v1/study?ref=Acts+8:37&translation=WEB", headers=auth)
    assert r.status_code == 404


# --- /v1/commentary ---------------------------------------------------------- #

def test_commentary_all_sources(client, auth):
    # Barnes' transcription is NT-only, so use a NT reference here.
    r = client.get("/v1/commentary?ref=John+1:1", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 3
    assert {c["source"] for c in body} >= {"matthew_henry", "jfb", "barnes_nt"}
    # full text here (not excerpts)
    assert all(c["truncated"] is False for c in body)
    assert all(c["full_length"] == len(c["text"]) for c in body)


def test_commentary_ot_has_no_barnes(client, auth):
    # Barnes' transcription covers the NT only: an OT query returns
    # no barnes_nt rows (but the OT commentaries do cover it).
    r = client.get("/v1/commentary?ref=Genesis+1:1", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body
    srcs = {c["source"] for c in body}
    assert "barnes_nt" not in srcs
    assert {"matthew_henry", "jfb", "gill", "clarke", "calvin", "keil_delitzsch"} <= srcs


def test_commentary_source_filter(client, auth):
    r = client.get("/v1/commentary?ref=Genesis+1:1&source=jfb", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body and all(c["source"] == "jfb" for c in body)
    assert body[0]["ref_range"] == "Genesis 1:1-2"


def test_commentary_whole_chapter_match(client, auth):
    # Genesis 1:5 must also match the whole-chapter Matthew Henry comment.
    r = client.get(
        "/v1/commentary?ref=Genesis+1:5&source=matthew_henry", headers=auth
    )
    assert r.status_code == 200
    ranges = {c["ref_range"] for c in r.json()}
    assert "Genesis 1" in ranges


def test_commentary_bad_source_400(client, auth):
    r = client.get("/v1/commentary?ref=Gen+1:1&source=not_a_source", headers=auth)
    assert r.status_code == 400


def test_commentary_bad_ref_400(client, auth):
    r = client.get("/v1/commentary?ref=Bogus+1:1", headers=auth)
    assert r.status_code == 400


# --- /v1/cross-refs ---------------------------------------------------------- #

def test_cross_refs_happy_path(client, auth):
    r = client.get("/v1/cross-refs?ref=Ps+23:1", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["total"] == len(body[0]["refs"])
    assert "Ezekiel 34:11" in body[0]["refs"]
    # ref strings are well-formed "Book C:V"
    assert all(re.match(r".+ \d+:\d+$", x) for x in body[0]["refs"])


def test_cross_refs_multi_verse(client, auth):
    r = client.get("/v1/cross-refs?ref=Ps+23:1-2", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert [(c["chapter"], c["verse"]) for c in body] == [(23, 1), (23, 2)]


def test_cross_refs_bad_ref_400(client, auth):
    r = client.get("/v1/cross-refs?ref=Nope+1:1", headers=auth)
    assert r.status_code == 400


# --- /v1/devotional ---------------------------------------------------------- #

def test_devotional_spurgeon(client, auth):
    r = client.get("/v1/devotional?date=2026-09-20&source=spurgeon", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "spurgeon"
    assert body["date"] == "2026-09-20"
    assert body["morning"] is not None and body["evening"] is not None
    assert body["morning"]["anchor_ref"]
    assert body["morning"]["body"].strip()
    # anchor resolved to verse text
    assert body["morning"]["anchor_verses"]


def test_devotional_daily_light(client, auth):
    r = client.get(
        "/v1/devotional?date=2026-01-01&source=daily_light", headers=auth
    )
    assert r.status_code == 200
    body = r.json()
    assert body["day"] == 1
    assert body["morning"]["anchor_verses"]


def test_devotional_feb29_leap_year(client, auth):
    # 2024 is a leap year: Feb 29 is day 60 and gets its own entry.
    r = client.get("/v1/devotional?date=2024-02-29", headers=auth)
    assert r.status_code == 200
    assert r.json()["day"] == 60


def test_devotional_non_leap_march1_skips_feb29(client, auth):
    # Non-leap Mar 1 must read Mar 1's entry (day 61), not Feb 29's (day 60).
    r = client.get("/v1/devotional?date=2025-03-01", headers=auth)
    assert r.status_code == 200
    assert r.json()["day"] == 61


def test_devotional_bad_source_400(client, auth):
    r = client.get("/v1/devotional?date=2026-09-20&source=tyndale", headers=auth)
    assert r.status_code == 400


def test_devotional_bad_date_400(client, auth):
    r = client.get("/v1/devotional?date=not-a-date", headers=auth)
    assert r.status_code == 400


# --- /v1/prayer -------------------------------------------------------------- #

def test_prayer_1662_morning(client, auth):
    r = client.get("/v1/prayer?office=morning&edition=1662", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["edition"] == "1662"
    assert body["office"] == "morning"
    assert len(body["blocks"]) == 198
    assert body["blocks"][0]["section"] == "opening_rubric"
    assert all(b["text"].strip() for b in body["blocks"])


def test_prayer_1928_evening(client, auth):
    r = client.get("/v1/prayer?office=evening&edition=1928", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body["blocks"]) == 154


def test_prayer_bad_office_400(client, auth):
    r = client.get("/v1/prayer?office=noon&edition=1662", headers=auth)
    assert r.status_code == 400


def test_prayer_bad_edition_400(client, auth):
    r = client.get("/v1/prayer?office=morning&edition=1979", headers=auth)
    assert r.status_code == 400


# --- /v1/memory-pack ---------------------------------------------------------- #

def test_memory_pack_happy_path(client, auth):
    r = client.get("/v1/memory-pack?topic=peace", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["topic"] == "peace"
    assert 5 <= body["count"] <= 10
    assert [v["n"] for v in body["verses"]] == list(range(1, body["count"] + 1))
    assert all(v["text"].strip() for v in body["verses"])
    assert all(v["ref"] for v in body["verses"])


def test_memory_pack_unknown_topic_404(client, auth):
    r = client.get("/v1/memory-pack?topic=not-a-topic", headers=auth)
    assert r.status_code == 404
