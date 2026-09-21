"""API tests: auth, all endpoints, error paths, verse-of-day determinism."""

import hashlib

import db


# --- auth ------------------------------------------------------------------- #

def test_health_no_auth(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["translations"] == ["BSB", "KJV", "WEB", "ASV", "YLT", "DARBY",
                                    "DRB", "GENEVA", "AKJV", "OEB",
                                    "WEBSTER", "WEYMOUTH", "LXX2012", "LSG1910", "LUTHER1912",
                                    "ALMEIDA", "RVA1909"]
    assert body["verse_count"] == 490335  # 2026-09-21: BBE removed (US-only PD)


def test_protected_rejects_missing_key(client):
    for path in ("/v1/translations", "/v1/books", "/v1/passage?ref=John+3:16",
                 "/v1/compare?ref=John+3:16", "/v1/search?q=grace",
                 "/v1/verse-of-day"):
        r = client.get(path)
        assert r.status_code == 401, path


def test_protected_rejects_wrong_key(client):
    r = client.get("/v1/translations", headers={"X-API-Key": "wrong-key"})
    assert r.status_code == 401


def test_protected_accepts_correct_key(client, auth):
    r = client.get("/v1/translations", headers=auth)
    assert r.status_code == 200


# --- translations ----------------------------------------------------------- #

def test_translations_metadata(client, auth):
    r = client.get("/v1/translations", headers=auth)
    assert r.status_code == 200
    items = {t["code"]: t for t in r.json()}
    assert set(items) == {"BSB", "KJV", "WEB", "ASV", "YLT", "DARBY", "DRB",
                          "GENEVA", "AKJV", "OEB",
                          "WEBSTER", "WEYMOUTH", "LXX2012", "LSG1910", "LUTHER1912",
                          "ALMEIDA", "RVA1909"}
    assert items["BSB"]["default"] is True
    assert items["BSB"]["verse_count"] == 31086
    assert items["KJV"]["verse_count"] == 31102
    assert items["WEB"]["verse_count"] == 31095
    assert items["ASV"]["verse_count"] == 31086
    assert items["YLT"]["verse_count"] == 31102
    assert items["DARBY"]["verse_count"] == 31099
    assert items["DRB"]["verse_count"] == 35811
    assert items["GENEVA"]["verse_count"] == 31090
    assert items["AKJV"]["verse_count"] == 31102
    assert items["OEB"]["verse_count"] == 13894
    assert items["LSG1910"]["verse_count"] == 31170  # 2026-09-20
    assert items["LUTHER1912"]["verse_count"] == 31102  # 2026-09-20
    assert items["ALMEIDA"]["verse_count"] == 31102  # 2026-09-20
    assert items["RVA1909"]["verse_count"] == 31084  # 2026-09-20
    for t in items.values():
        assert t["rights"]["status"] == "public_domain"
        assert t["rights"]["copyright"]
        assert t["rights"]["attribution"]


# --- books ------------------------------------------------------------------ #

def test_books_list(client, auth):
    r = client.get("/v1/books", params={"translation": "BSB"}, headers=auth)
    assert r.status_code == 200
    books = r.json()
    assert len(books) == 66
    assert books[0] == {"book_order": 0, "book": "Genesis", "chapters": 50}
    psalms = next(b for b in books if b["book"] == "Psalms")
    assert psalms["chapters"] == 150
    assert books[-1]["book"] == "Revelation"


def test_books_bad_translation(client, auth):
    r = client.get("/v1/books", params={"translation": "NIV"}, headers=auth)
    assert r.status_code == 400


# --- passage ---------------------------------------------------------------- #

def test_passage_john_3_16(client, auth):
    r = client.get("/v1/passage", params={"ref": "John 3:16", "translation": "BSB"},
                   headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["ref"] == "John 3:16"
    assert body["translation"] == "BSB"
    assert len(body["verses"]) == 1
    v = body["verses"][0]
    assert (v["book"], v["chapter"], v["verse"]) == ("John", 3, 16)
    assert v["text"].startswith("For God so loved the world")


def test_passage_range_default_translation(client, auth):
    r = client.get("/v1/passage", params={"ref": "Ps 23:1-3"}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["translation"] == "BSB"  # default
    assert body["ref"] == "Psalms 23:1-3"
    assert [v["verse"] for v in body["verses"]] == [1, 2, 3]


def test_passage_whole_chapter(client, auth):
    r = client.get("/v1/passage", params={"ref": "Romans 8", "translation": "KJV"},
                   headers=auth)
    assert r.status_code == 200
    assert len(r.json()["verses"]) == 39


def test_passage_bad_ref_400(client, auth):
    r = client.get("/v1/passage", params={"ref": "John 99:1"}, headers=auth)
    assert r.status_code == 400
    r = client.get("/v1/passage", params={"ref": "Foo 1:1"}, headers=auth)
    assert r.status_code == 400


def test_passage_bad_translation_400(client, auth):
    r = client.get("/v1/passage", params={"ref": "John 3:16", "translation": "ESV"},
                   headers=auth)
    assert r.status_code == 400


def test_passage_missing_verse_404(client, auth):
    # Acts 8:37 is a genuine KJV-only verse key; WEB/ASV lack it.
    r = client.get("/v1/passage",
                   params={"ref": "Acts 8:37", "translation": "WEB"}, headers=auth)
    assert r.status_code == 404
    r = client.get("/v1/passage",
                   params={"ref": "Acts 8:37", "translation": "KJV"}, headers=auth)
    assert r.status_code == 200
    assert len(r.json()["verses"]) == 1


# --- compare ---------------------------------------------------------------- #

def test_compare_side_by_side(client, auth):
    r = client.get("/v1/compare",
                   params={"ref": "Ps 23:1", "translations": "BSB,KJV,WEB"},
                   headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["translations"] == ["BSB", "KJV", "WEB"]
    assert len(body["verses"]) == 1
    texts = body["verses"][0]["texts"]
    assert all(texts[c] for c in ("BSB", "KJV", "WEB"))
    assert "shepherd" in texts["KJV"].lower()


def test_compare_reports_missing_not_error(client, auth):
    r = client.get("/v1/compare",
                   params={"ref": "Acts 8:37", "translations": "KJV,WEB,ASV"},
                   headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body["verses"]) == 1
    texts = body["verses"][0]["texts"]
    assert texts["KJV"] is not None
    assert texts["WEB"] is None
    assert texts["ASV"] is None
    assert "null" in body["note"]


def test_compare_bad_translation_400(client, auth):
    r = client.get("/v1/compare",
                   params={"ref": "John 3:16", "translations": "BSB,NIV"},
                   headers=auth)
    assert r.status_code == 400


# --- search ----------------------------------------------------------------- #

def test_search_happy_path(client, auth):
    r = client.get("/v1/search",
                   params={"q": "lovingkindness", "translation": "KJV", "limit": 20},
                   headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["translation"] == "KJV"
    assert body["count"] > 0
    assert len(body["hits"]) <= 20
    first = body["hits"][0]
    assert "<em>lovingkindness</em>" in first["snippet"].lower()
    assert "lovingkindness" in first["text"].lower()


def test_search_limit_clamped(client, auth):
    r = client.get("/v1/search", params={"q": "grace", "limit": 5}, headers=auth)
    assert r.status_code == 200
    assert len(r.json()["hits"]) <= 5
    r = client.get("/v1/search", params={"q": "grace", "limit": 500}, headers=auth)
    assert r.status_code == 422  # FastAPI query validation


def test_search_empty_query_400(client, auth):
    r = client.get("/v1/search", params={"q": "!!!", "translation": "KJV"},
                   headers=auth)
    assert r.status_code == 400


def test_search_special_chars_safe(client, auth):
    # FTS5 syntax characters must not break the query.
    r = client.get("/v1/search", params={"q": 'god "love" OR hate: *',
                                         "translation": "BSB"}, headers=auth)
    assert r.status_code == 200


# --- verse of day ----------------------------------------------------------- #

def _expected_votd(day: str, translation: str) -> dict:
    count = db.translation_counts()[translation]
    offset = int(hashlib.sha256(f"{day}|{translation}".encode()).hexdigest(), 16) % count
    return db.verse_by_offset(translation, offset)


def test_verse_of_day_deterministic(client, auth):
    for day in ("2026-09-20", "2026-09-21"):
        r = client.get("/v1/verse-of-day",
                       params={"day": day, "translation": "BSB"}, headers=auth)
        assert r.status_code == 200
        body = r.json()
        expected = _expected_votd(day, "BSB")
        assert body["date"] == day
        assert body["translation"] == "BSB"
        assert body["book"] == expected["book"]
        assert body["chapter"] == expected["chapter"]
        assert body["verse"] == int(expected["verse"])
        assert body["text"] == expected["text"]


def test_verse_of_day_same_all_day(client, auth):
    a = client.get("/v1/verse-of-day", params={"day": "2026-09-20"},
                   headers=auth).json()
    b = client.get("/v1/verse-of-day", params={"day": "2026-09-20"},
                   headers=auth).json()
    assert a == b


def test_verse_of_day_differs_by_translation(client, auth):
    a = client.get("/v1/verse-of-day",
                   params={"day": "2026-09-20", "translation": "BSB"},
                   headers=auth).json()
    b = client.get("/v1/verse-of-day",
                   params={"day": "2026-09-20", "translation": "KJV"},
                   headers=auth).json()
    assert (a["book"], a["chapter"], a["verse"]) != (b["book"], b["chapter"], b["verse"])


def test_verse_of_day_bad_date_400(client, auth):
    r = client.get("/v1/verse-of-day", params={"day": "not-a-date"}, headers=auth)
    assert r.status_code == 400


# --- openapi ---------------------------------------------------------------- #

def test_openapi_is_3_1(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["openapi"].startswith("3.1")
