"""Tests for /v1/word and /v1/word/sources (lexicon word studies)."""

import re

TAG_RE = re.compile(r"</?(b|i|a|br|ref|level[1-4]|re|author)\b", re.IGNORECASE)


def test_word_g3056_all_sources(client, auth):
    r = client.get("/v1/word", params={"number": "G3056"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["number"] == "G3056"
    assert body["language"] == "greek"
    srcs = {e["source"]["id"] for e in body["entries"]}
    assert {"strongs", "step_tbesg", "step_tflsj"} <= srcs
    for e in body["entries"]:
        assert e["definition"], "every entry must carry a definition"
        assert e["source"]["title"]
        assert e["source"]["rights"]
        assert e["source"]["attribution"]


def test_word_number_normalization(client, auth):
    for variant in ("g3056", "G03056", " g3056 "):
        r = client.get("/v1/word", params={"number": variant}, headers=auth)
        assert r.status_code == 200, variant
        assert r.json()["number"] == "G3056"


def test_word_zero_padded_source_numbers(client, auth):
    # STEPBible stores 'G0001'; a plain 'G1' query must still match it.
    r = client.get("/v1/word", params={"number": "G1", "source": "step_tbesg"}, headers=auth)
    assert r.status_code == 200
    assert len(r.json()["entries"]) >= 1


def test_word_hebrew_h430(client, auth):
    r = client.get("/v1/word", params={"number": "H430"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "hebrew"
    assert {"strongs", "bdb", "step_tbesh"} <= {e["source"]["id"] for e in body["entries"]}


def test_word_source_filter(client, auth):
    r = client.get(
        "/v1/word", params={"number": "G3056", "source": "strongs"}, headers=auth
    )
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["source"]["id"] == "strongs"


def test_word_unknown_number_404(client, auth):
    r = client.get("/v1/word", params={"number": "G99999"}, headers=auth)
    assert r.status_code == 404


def test_word_bad_number_400(client, auth):
    for bad in ("xyz", "3056", "", "GG1"):
        r = client.get("/v1/word", params={"number": bad}, headers=auth)
        assert r.status_code == 400, bad


def test_word_bad_source_400(client, auth):
    r = client.get(
        "/v1/word", params={"number": "G3056", "source": "nope"}, headers=auth
    )
    assert r.status_code == 400


def test_word_requires_auth(client):
    r = client.get("/v1/word", params={"number": "G3056"})
    assert r.status_code == 401


def test_word_no_html_in_stepbible_definitions(client, auth):
    # TFLSJ definitions are the heaviest HTML source; served text must be clean.
    r = client.get(
        "/v1/word", params={"number": "G1", "source": "step_tflsj"}, headers=auth
    )
    assert r.status_code == 200
    for e in r.json()["entries"]:
        assert not TAG_RE.search(e["definition"] or ""), e["definition"][:80]


def test_word_sources_listing(client, auth):
    r = client.get("/v1/word/sources", headers=auth)
    assert r.status_code == 200
    srcs = {s["id"]: s for s in r.json()}
    assert set(srcs) == {
        "strongs",
        "bdb",
        "step_tbesh",
        "step_tbesg",
        "step_tflsj",
        "step_tflsjx",
    }
    assert srcs["strongs"]["rights"] == "Public domain"
    for sid, s in srcs.items():
        assert s["attribution"], f"{sid} must expose attribution"
        assert s["entries"] > 0, f"{sid} must have entries"


def test_word_sources_requires_auth(client):
    assert client.get("/v1/word/sources").status_code == 401
