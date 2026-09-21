"""Tests for /v1/interlinear/{book}/{chapter}/{verse}."""

import pytest


def test_interlinear_no_auth_401(client):
    r = client.get("/v1/interlinear/John/1/1")
    assert r.status_code == 401


def test_interlinear_genesis_1_1(client, auth):
    r = client.get("/v1/interlinear/Genesis/1/1", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["book"] == "Genesis"
    assert body["chapter"] == 1
    assert body["verse"] == 1
    assert body["testament"] == "OT"
    assert body["reading"] == "main"
    words = body["words"]
    assert len(words) == 7
    # positions are a clean 1..N sequence in reading order
    assert [w["position"] for w in words] == list(range(1, 8))
    first = words[0]
    assert first["word"] == "בְּ/רֵאשִׁ֖ית"
    assert first["strongs"] == "H7225"
    assert first["gloss"] == "in/ beginning"
    assert first["lemma"] == "רֵאשִׁית"
    assert first["morphology"] == "HR/Ncfsa"
    for w in words:
        assert w["gloss"], f"word {w['position']} missing gloss"
        assert w["strongs"], f"word {w['position']} missing Strong's"


def test_interlinear_john_1_1(client, auth):
    r = client.get("/v1/interlinear/John/1/1", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["testament"] == "NT"
    assert body["reading"] == "main"
    words = body["words"]
    assert len(words) == 17
    assert [w["position"] for w in words] == list(range(1, 18))
    assert words[0]["word"] == "Ἐν"
    assert words[0]["strongs"] == "G1722"
    assert words[4]["word"] == "λόγος,"
    assert words[4]["strongs"] == "G3056"
    assert words[4]["lemma"] == "λόγος"


def test_interlinear_book_alias(client, auth):
    # aliases resolve like everywhere else in the API
    for alias, canonical in (("jn", "John"), ("1jn", "1 John"),
                             ("1 John", "1 John"), ("ps", "Psalms")):
        r = client.get(f"/v1/interlinear/{alias}/1/1", headers=auth)
        assert r.status_code == 200, alias
        assert r.json()["book"] == canonical, alias


def test_interlinear_split_verse_concatenated(client, auth):
    # 1Ki 18:33 spans two Hebrew-versification segments; they must come back
    # as one ordered sequence.
    r = client.get("/v1/interlinear/1%20Kings/18/33", headers=auth)
    assert r.status_code == 200
    words = r.json()["words"]
    assert len(words) == 19
    assert [w["position"] for w in words] == list(range(1, 20))
    assert words[0]["gloss"] == "and/ he arranged"
    assert words[9]["gloss"] == "and/ he said"
    assert words[18]["gloss"] == "the/ wood<s>"


def test_interlinear_disputed_verse_variant_reading(client, auth):
    # Mark 16:9 is absent from the critical text: variant-only response.
    r = client.get("/v1/interlinear/Mark/16/9", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["reading"] == "variant"
    assert body["note"]
    assert body["words"] == []
    assert len(body["variants"]) >= 1
    kinds = {g["kind"] for g in body["variants"]}
    assert kinds <= {
        "K", "k", "KO", "K(O)", "K(o)", "(k)O", "O", "o", "ko", "k(o)",
    }, f"unexpected variant kinds: {kinds}"
    for g in body["variants"]:
        assert g["words"], "variant group must not be empty"
        assert [w["position"] for w in g["words"]] == list(
            range(1, len(g["words"]) + 1)
        )


def test_interlinear_attribution(client, auth):
    r = client.get("/v1/interlinear/Psalms/23/1", headers=auth)
    assert r.status_code == 200
    srcs = {s["id"]: s for s in r.json()["sources"]}
    assert {"step_tagnt", "step_tahot"} <= set(srcs)
    for s in srcs.values():
        assert s["rights"] == "CC BY 4.0"
        assert "STEPBible.org" in s["rights_basis"]
        assert "creativecommons.org/licenses/by/4.0" in s["rights_basis"]


def test_interlinear_bad_book_400(client, auth):
    r = client.get("/v1/interlinear/Notabook/1/1", headers=auth)
    assert r.status_code == 400


@pytest.mark.parametrize("chapter,verse", [(0, 1), (1, 0), (1, 999), (151, 1)])
def test_interlinear_bad_ref_400(client, auth, chapter, verse):
    r = client.get(f"/v1/interlinear/Psalms/{chapter}/{verse}", headers=auth)
    assert r.status_code == 400


def test_interlinear_psalm_title_first(client, auth):
    # Psalm 3:1 begins with the psalm title (source verse 0), ordered first.
    r = client.get("/v1/interlinear/Psalms/3/1", headers=auth)
    assert r.status_code == 200
    words = r.json()["words"]
    assert words[0]["gloss"] == "a psalm"
    assert words[1]["gloss"] == "of/ David"
    assert words[6]["gloss"] == "O Yahweh"
