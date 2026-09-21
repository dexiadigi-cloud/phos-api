"""Tests for GET /v1/verse-study (Phos Intensive Verse Study)."""

import pytest

from app import _is_key_word


def test_shape_john_3_16_defaults(client, auth):
    r = client.get("/v1/verse-study/John/3/16", headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["ref"] == "John 3:16"
    assert d["book"] == "John"
    assert d["chapter"] == 3
    assert d["verse"] == 16
    assert d["testament"] == "NT"

    assert [t["code"] for t in d["translations"]] == ["BSB", "KJV", "WEB"]
    assert all(t["present"] for t in d["translations"])
    assert all(t["text"] for t in d["translations"])

    kws = d["key_words"]
    assert len(kws) == 12
    positions = [k["position"] for k in kws]
    assert positions == sorted(positions)
    first = kws[0]
    assert first["word"] == "ἠγάπησεν"
    assert first["strongs"] == "G25"
    assert first["definition"]
    assert first["definition_source"]

    assert d["key_words_note"] is None
    assert d["cross_refs"]["total"] == 19
    assert len(d["cross_refs"]["refs"]) == 8

    comm_sources = {c["source"] for c in d["commentaries"]}
    assert "barnes_nt" in comm_sources
    assert len(d["commentaries"]) >= 1

    assert len(d["devotionals"]) >= 1
    assert any(x["match_kind"] == "exact" for x in d["devotionals"])

    prayer = d["prayer"]
    assert prayer is not None
    assert prayer["match_kind"] in ("keyword", "office_opening")
    assert prayer["office"] == "morning_prayer"

    src_ids = {s["id"]: s["rights"] for s in d["sources"]}
    assert src_ids["step_tagnt"] == "CC BY 4.0"

    assert "STEPBible" in d["rights_note"]
    assert "https://creativecommons.org/licenses/by/4.0/" in d["rights_note"]


def test_genesis_1_1_hebrew(client, auth):
    r = client.get("/v1/verse-study/Genesis/1/1", headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["testament"] == "OT"
    assert len(d["key_words"]) == 5
    comm_sources = {c["source"] for c in d["commentaries"]}
    assert "keil_delitzsch" in comm_sources
    src_ids = {s["id"] for s in d["sources"]}
    assert "step_tahot" in src_ids


@pytest.mark.parametrize(
    "morph, testament, expected",
    [
        ("V-AAI-3S", "NT", True),
        ("N-NSM-T", "NT", True),
        ("A-ASM", "NT", True),
        ("ADV", "NT", False),
        ("T-NSM", "NT", False),
        ("PREP", "NT", False),
        ("CONJ", "NT", False),
        ("CONJ + G1565=D", "NT", False),
        ("V-PAP-NSM", "NT", True),
        ("HTd/Ncmpa", "OT", True),
        ("HVqp3ms", "OT", True),
        ("HR/Ncfsa", "OT", True),
        ("HC/To", "OT", False),
        ("HTo", "OT", False),
        ("", "NT", False),
        (None, "OT", False),
    ],
)
def test_morphology_rule(morph, testament, expected):
    assert _is_key_word(morph, testament) is expected


def test_devotional_john_disambiguation(client, auth):
    """The devotional anchored to 1 John 3:16 must not match John 3:16."""
    d = client.get("/v1/verse-study/John/3/16", headers=auth).json()
    for dev in d["devotionals"]:
        assert "Hereby perceive we the love of God" not in dev["text"]
        assert not dev["anchor_ref"].startswith("1 John 3:16;")


def test_variant_only_verse(client, auth):
    r = client.get("/v1/verse-study/Mark/16/9", headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["key_words"] == []
    assert d["key_words_note"] is not None
    assert "/v1/interlinear" in d["key_words_note"]
    # Everything else still behaves normally.
    assert d["prayer"] is not None
    assert d["prayer"]["match_kind"] == "office_opening"


def test_nearby_devotional_fallback(client, auth):
    d = client.get("/v1/verse-study/John/1/2", headers=auth).json()
    assert len(d["devotionals"]) >= 1
    assert all(x["match_kind"] == "nearby" for x in d["devotionals"])


def test_translations_override(client, auth):
    d = client.get(
        "/v1/verse-study/John/3/16?translations=KJV", headers=auth
    ).json()
    assert [t["code"] for t in d["translations"]] == ["KJV"]
    assert d["cross_refs"]["refs"][0]["text"]


def test_partial_translation_presence(client, auth):
    # Acts 15:34 is in KJV but not in BSB or WEB.
    d = client.get("/v1/verse-study/Acts/15/34", headers=auth).json()
    by_code = {t["code"]: t for t in d["translations"]}
    assert by_code["KJV"]["present"] is True
    assert by_code["KJV"]["text"]
    assert by_code["BSB"]["present"] is False
    assert by_code["BSB"]["text"] is None
    assert by_code["WEB"]["present"] is False


def test_missing_everywhere_404(client, auth):
    r = client.get(
        "/v1/verse-study/Acts/15/34?translations=BSB", headers=auth
    )
    assert r.status_code == 404


def test_unknown_book_400(client, auth):
    r = client.get("/v1/verse-study/Nope/1/1", headers=auth)
    assert r.status_code == 400


def test_out_of_range_400(client, auth):
    r = client.get("/v1/verse-study/John/99/99", headers=auth)
    assert r.status_code == 400


def test_unknown_translation_400(client, auth):
    r = client.get(
        "/v1/verse-study/John/3/16?translations=NOPE", headers=auth
    )
    assert r.status_code == 400


def test_too_many_translations_400(client, auth):
    r = client.get(
        "/v1/verse-study/John/3/16?translations=BSB,KJV,WEB,ASV,YLT",
        headers=auth,
    )
    assert r.status_code == 400


def test_unknown_office_400(client, auth):
    r = client.get("/v1/verse-study/John/3/16?office=dawn", headers=auth)
    assert r.status_code == 400


def test_evening_office(client, auth):
    d = client.get(
        "/v1/verse-study/John/3/16?office=evening", headers=auth
    ).json()
    assert d["prayer"]["office"] == "evening_prayer"


def test_attribution_traceability(client, auth):
    d = client.get("/v1/verse-study/John/3/16", headers=auth).json()
    src_ids = {s["id"] for s in d["sources"]}
    for kw in d["key_words"]:
        assert kw["definition_source"] in src_ids


def test_requires_api_key(client):
    r = client.get("/v1/verse-study/John/3/16")
    assert r.status_code == 401


def test_prayer_keywords_drop_stopwords():
    from app import _prayer_keywords, VerseStudyKeyWord

    kws = [
        VerseStudyKeyWord(
            position=1, word="x", transliteration="x", strongs="G1",
            gloss="[is] shepherd/ my", morphology="", lemma="",
            definition="", definition_source="",
        ),
        VerseStudyKeyWord(
            position=2, word="y", transliteration="y", strongs="G2",
            gloss="I lack", morphology="", lemma="",
            definition="", definition_source="",
        ),
    ]
    got = _prayer_keywords(kws)
    assert got == ["shepherd", "lack"]


def test_prayer_match_never_reports_stopwords(client, auth):
    d = client.get("/v1/verse-study/Psalm/23/1", headers=auth).json()
    prayer = d["prayer"]
    assert prayer is not None
    for kw in prayer["matched_keywords"]:
        assert kw not in ("is", "my", "i", "me", "he", "not", "it")


def test_prayer_match_never_returns_rubric(client, auth):
    d = client.get("/v1/verse-study/Psalm/23/1", headers=auth).json()
    prayer = d["prayer"]
    assert prayer is not None
    assert prayer["match_kind"] == "keyword"
    assert "psalm following" not in prayer["text"].lower()


def test_brief_mode_trims_composite(client, auth):
    d = client.get("/v1/verse-study/John/3/16?brief=true", headers=auth).json()
    assert d["brief"] is True
    assert d["full_hint"] == "Full intensive available: GET /v1/verse-study/John/3/16"
    assert len(d["key_words"]) <= 4
    assert d["cross_refs"]["total"] == 19
    assert len(d["cross_refs"]["refs"]) <= 4
    assert len(d["commentaries"]) <= 2
    assert len(d["devotionals"]) <= 1
    assert d["prayer"] is None
    # core identity fields intact
    assert d["ref"] == "John 3:16"
    assert len(d["translations"]) == 3


def test_full_mode_unchanged_by_default(client, auth):
    d = client.get("/v1/verse-study/John/3/16", headers=auth).json()
    assert d["brief"] is False
    assert d["full_hint"] is None
    assert len(d["key_words"]) == 12
    assert len(d["cross_refs"]["refs"]) == 8
    assert d["prayer"] is not None
