"""Tests for GET /recipes?tag=... (Task 2).

The SQLite file is shared with other tests, so every test uses unique tags and
only asserts on the recipes it created.
"""
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _create(title: str, tags: list[str]) -> int:
    r = client.post("/recipes", json={"title": title, "ingredients": [], "tags": tags})
    assert r.status_code == 200
    return r.json()["id"]


def _ids(resp) -> list[int]:
    assert resp.status_code == 200
    return [rec["id"] for rec in resp.json()]


def test_filter_returns_only_matching_recipes():
    tag = f"breakfast-{uuid4().hex}"
    other = f"dinner-{uuid4().hex}"
    a = _create("Pancakes", [tag])
    b = _create("Omelette", [other, tag])
    c = _create("Steak", [other])

    ids = _ids(client.get("/recipes", params={"tag": tag}))
    assert ids == [a, b]
    assert c not in ids


def test_filtered_results_have_full_recipe_shape():
    tag = f"shape-{uuid4().hex}"
    rid = _create("Waffles", [tag, "sweet"])
    body = client.get("/recipes", params={"tag": tag}).json()
    assert body == [
        {"id": rid, "title": "Waffles", "ingredients": [], "tags": [tag, "sweet"], "favorite": False}
    ]


def test_filtered_results_reflect_favorite_toggle():
    # Integration check after merging task-a (tag filter) with task-b (favorites).
    tag = f"fav-{uuid4().hex}"
    rid = _create("Shakshuka", [tag])
    client.post(f"/recipes/{rid}/favorite")
    body = client.get("/recipes", params={"tag": tag}).json()
    assert [(r["id"], r["favorite"]) for r in body] == [(rid, True)]


def test_query_is_case_insensitive_and_trimmed():
    tag = f"breakfast-{uuid4().hex}"
    rid = _create("Granola", [tag])
    for q in [tag.upper(), f"  {tag}  ", f" {tag.title()} "]:
        assert _ids(client.get("/recipes", params={"tag": q})) == [rid]


def test_stored_tag_case_is_ignored():
    tag = f"Brunch-{uuid4().hex}".upper()
    rid = _create("Eggs Benedict", [tag])
    assert _ids(client.get("/recipes", params={"tag": tag.lower()})) == [rid]


def test_match_is_exact_not_substring():
    base = uuid4().hex
    rid = _create("Exact", [f"tag-{base}"])
    _create("Longer", [f"tag-{base}-extra"])
    assert _ids(client.get("/recipes", params={"tag": f"tag-{base}"})) == [rid]
    assert _ids(client.get("/recipes", params={"tag": base})) == []


def test_unknown_tag_returns_empty_list():
    r = client.get("/recipes", params={"tag": f"nope-{uuid4().hex}"})
    assert r.status_code == 200
    assert r.json() == []


def test_empty_or_blank_tag_behaves_like_no_filter():
    _create(f"Untagged-{uuid4().hex}", [])
    all_ids = _ids(client.get("/recipes"))
    assert _ids(client.get("/recipes?tag=")) == all_ids
    assert _ids(client.get("/recipes", params={"tag": "   "})) == all_ids


def test_no_tag_still_returns_all_recipes_including_untagged():
    tagged = _create("Tagged", [f"t-{uuid4().hex}"])
    untagged = _create("Untagged", [])
    ids = _ids(client.get("/recipes"))
    assert tagged in ids and untagged in ids
    assert ids == sorted(ids)
