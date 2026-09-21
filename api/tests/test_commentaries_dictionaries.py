"""Tests for the commentaries + dictionaries batch (v2 expansion)."""

import re

import study

TAG_RE = re.compile(r"<(p|div|span|table|tr|td|a|b|i|em|strong|br|h[1-6]|ul|ol|li)\b", re.IGNORECASE)

EXPECTED_COMMENTARY_COUNTS = {
    "clarke": 14206,
    "calvin": 4972,
    "keil_delitzsch": 6324,  # 2026-09-20: -1 pure-ad row deleted (id 71579, Eccl 1:1 was 100% catalog); -4 stamp strips are text-only
    "treasury_of_david": 150,
}

EXPECTED_DICT_COUNTS = {
    "easton": 3961,
    "isbe": 9349,
    "naves": 4726,
    "torrey": 628,
}


def test_new_commentary_sources_registered():
    for sid in EXPECTED_COMMENTARY_COUNTS:
        assert sid in study.COMMENTARY_SOURCES, sid


def test_new_commentary_counts():
    rows = study._query(
        "SELECT source_id, COUNT(*) AS n FROM commentaries "
        "WHERE source_id IN ('clarke','calvin','keil_delitzsch','treasury_of_david') "
        "GROUP BY source_id"
    )
    got = {r["source_id"]: r["n"] for r in rows}
    assert got == EXPECTED_COMMENTARY_COUNTS


def test_new_commentary_sources_in_rights_table():
    rows = study.get_sources()
    by_id = {r["source_id"]: r for r in rows}
    for sid in EXPECTED_COMMENTARY_COUNTS:
        assert sid in by_id, sid
        assert by_id[sid]["kind"] == "commentary"
        assert by_id[sid]["rights"] == "Public Domain"
        assert by_id[sid]["rights_basis"]


def test_commentary_book_orders_canonical():
    bad = study._query(
        "SELECT COUNT(*) AS n FROM commentaries "
        "WHERE source_id IN ('clarke','calvin','keil_delitzsch','treasury_of_david') "
        "AND (book_order < 1 OR book_order > 66)"
    )
    assert bad[0]["n"] == 0


def test_clarke_genesis_1_1():
    rows = study.commentaries_covering(1, 1, 1, source_id="clarke")
    assert rows, "Clarke should cover Genesis 1:1"
    assert any("beginning" in r["text"].lower() for r in rows)


def test_treasury_psalm_23():
    rows = study.commentaries_covering(19, 23, 1, source_id="treasury_of_david")
    assert len(rows) == 1
    assert "shepherd" in rows[0]["text"].lower() or "psalm" in rows[0]["text"].lower()


def test_treasury_covers_all_150_psalms():
    rows = study._query(
        "SELECT COUNT(DISTINCT start_chapter) AS n FROM commentaries "
        "WHERE source_id='treasury_of_david'"
    )
    assert rows[0]["n"] == 150


def test_calvin_john_3_16():
    rows = study.commentaries_covering(43, 3, 16, source_id="calvin")
    assert rows, "Calvin should cover John 3:16"


def test_keil_delitzsch_isaiah_53_5():
    rows = study.commentaries_covering(23, 53, 5, source_id="keil_delitzsch")
    assert rows, "Keil & Delitzsch should cover Isaiah 53:5"


def test_new_commentary_no_html_tags():
    rows = study._query(
        "SELECT COUNT(*) AS n FROM commentaries "
        "WHERE source_id IN ('clarke','calvin','keil_delitzsch','treasury_of_david') "
        "AND (text LIKE '%<p>%' OR text LIKE '%</%')"
    )
    # 8 known OCR-noise rows in Keil & Delitzsch (verified 2026-09-20, not real
    # markup): KXrjpo<; (Isa 55:1), </iee) (Dan 2:29), «.</. (Num 22:2, Prov 15:25),
    # "</te (Josh 14:6), <f>pd%a>p (Judg 5:6), </macA-word (Prov 14:5), stray < (Lam 5:17).
    assert rows[0]["n"] <= 8


def test_commentary_endpoint_new_sources(client, auth):
    r = client.get(
        "/v1/commentary",
        params={"ref": "Ps 23:1", "source": "treasury_of_david"},
        headers=auth,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["source"] == "treasury_of_david"


def test_commentary_endpoint_bad_source_400(client, auth):
    r = client.get(
        "/v1/commentary",
        params={"ref": "Gen 1:1", "source": "not_a_source"},
        headers=auth,
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Dictionaries
# ---------------------------------------------------------------------------


def test_dictionary_sources_registered():
    assert set(study.DICTIONARY_SOURCES) == set(EXPECTED_DICT_COUNTS)


def test_dictionary_counts():
    rows = study._query(
        "SELECT source_id, COUNT(*) AS n FROM dictionaries GROUP BY source_id"
    )
    got = {r["source_id"]: r["n"] for r in rows}
    assert got == EXPECTED_DICT_COUNTS


def test_dictionary_sources_endpoint(client, auth):
    r = client.get("/v1/dictionary/sources", headers=auth)
    assert r.status_code == 200
    body = r.json()
    by_id = {s["id"]: s for s in body}
    for sid, count in EXPECTED_DICT_COUNTS.items():
        assert sid in by_id, sid
        assert by_id[sid]["entries"] == count
        assert by_id[sid]["rights"] == "Public Domain"
        assert by_id[sid]["rights_basis"]
        assert by_id[sid]["title"]


def test_dictionary_lookup_aaron(client, auth):
    r = client.get("/v1/dictionary", params={"term": "Aaron"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["term"] == "Aaron"
    srcs = {e["source"]["id"] for e in body["entries"]}
    assert {"easton", "isbe", "naves"} <= srcs
    for e in body["entries"]:
        assert e["text"]
        assert e["source"]["title"]
        assert e["source"]["rights"] == "Public Domain"


def test_dictionary_lookup_case_insensitive(client, auth):
    for variant in ("aaron", "AARON", " Aaron "):
        r = client.get("/v1/dictionary", params={"term": variant}, headers=auth)
        assert r.status_code == 200, variant
        assert r.json()["entries"], variant


def test_dictionary_lookup_source_filter(client, auth):
    r = client.get(
        "/v1/dictionary", params={"term": "Faith", "source": "torrey"}, headers=auth
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["source"]["id"] == "torrey"


def test_dictionary_lookup_faith_all_sources(client, auth):
    r = client.get("/v1/dictionary", params={"term": "Faith"}, headers=auth)
    assert r.status_code == 200
    srcs = {e["source"]["id"] for e in r.json()["entries"]}
    assert {"easton", "isbe", "naves", "torrey"} <= srcs


def test_dictionary_unknown_term_404(client, auth):
    r = client.get(
        "/v1/dictionary", params={"term": "ZzxqNotAWord"}, headers=auth
    )
    assert r.status_code == 404


def test_dictionary_bad_source_400(client, auth):
    r = client.get(
        "/v1/dictionary", params={"term": "Faith", "source": "webster"}, headers=auth
    )
    assert r.status_code == 400


def test_dictionary_blank_term_400(client, auth):
    r = client.get("/v1/dictionary", params={"term": "   "}, headers=auth)
    assert r.status_code == 400


def test_dictionary_no_key_401(client):
    r = client.get("/v1/dictionary", params={"term": "Faith"})
    assert r.status_code == 401


def test_dictionary_sources_no_key_401(client):
    r = client.get("/v1/dictionary/sources")
    assert r.status_code == 401


def test_dictionary_entries_carry_rights_metadata(client, auth):
    r = client.get("/v1/dictionary", params={"term": "Prayer"}, headers=auth)
    assert r.status_code == 200
    for e in r.json()["entries"]:
        assert e["source"]["title"]
        assert e["source"]["rights"] == "Public Domain"


def test_dictionary_no_html_tags():
    rows = study._query(
        "SELECT COUNT(*) AS n FROM dictionaries "
        "WHERE text LIKE '%<p>%' OR text LIKE '%</%'"
    )
    assert rows[0]["n"] == 0


def test_isbe_jesus_christ_present():
    rows = study.lookup_dictionary("Jesus Christ", source_id="isbe")
    assert len(rows) == 1
    assert len(rows[0]["text"]) > 300000


def test_naves_has_subtopics():
    rows = study.lookup_dictionary("Faith", source_id="naves")
    assert rows
