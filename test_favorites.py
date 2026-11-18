import json
import sqlite3
from contextlib import closing

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def _create(title="Fav test"):
    r = client.post("/recipes", json={"title": title, "ingredients": ["x"], "tags": ["t"]})
    assert r.status_code == 200
    return r.json()


def test_new_recipe_defaults_to_not_favorite():
    rec = _create("Default fav")
    assert rec["favorite"] is False
    assert client.get(f"/recipes/{rec['id']}").json()["favorite"] is False
    listed = {r["id"]: r for r in client.get("/recipes").json()}
    assert listed[rec["id"]]["favorite"] is False
    assert all(isinstance(r["favorite"], bool) for r in listed.values())


def test_create_ignores_client_supplied_favorite():
    r = client.post("/recipes", json={"title": "Sneaky", "favorite": True})
    assert r.status_code == 200
    assert r.json()["favorite"] is False
    assert client.get(f"/recipes/{r.json()['id']}").json()["favorite"] is False


def test_toggle_favorite_flips_and_persists():
    rid = _create("Toggle me")["id"]
    r1 = client.post(f"/recipes/{rid}/favorite")
    assert r1.status_code == 200
    assert r1.json()["id"] == rid
    assert r1.json()["favorite"] is True
    assert r1.json()["title"] == "Toggle me"
    assert client.get(f"/recipes/{rid}").json()["favorite"] is True

    r2 = client.post(f"/recipes/{rid}/favorite")
    assert r2.status_code == 200
    assert r2.json()["favorite"] is False
    assert client.get(f"/recipes/{rid}").json()["favorite"] is False


def test_toggle_only_affects_target_recipe():
    a = _create("A")["id"]
    b = _create("B")["id"]
    client.post(f"/recipes/{a}/favorite")
    assert client.get(f"/recipes/{a}").json()["favorite"] is True
    assert client.get(f"/recipes/{b}").json()["favorite"] is False


def test_toggle_unknown_recipe_404():
    r = client.post("/recipes/99999999/favorite")
    assert r.status_code == 404


def test_old_schema_database_is_upgraded_in_place(tmp_path, monkeypatch):
    old_db = tmp_path / "old_recipes.db"
    with closing(sqlite3.connect(old_db)) as conn:
        conn.execute(
            """CREATE TABLE recipes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                tags        TEXT NOT NULL
            )"""
        )
        conn.executemany(
            "INSERT INTO recipes (title, ingredients, tags) VALUES (?, ?, ?)",
            [
                ("Old Soup", json.dumps(["water", "salt"]), json.dumps(["dinner"])),
                ("Old Bread", json.dumps(["flour"]), json.dumps([])),
            ],
        )
        conn.commit()

    monkeypatch.setattr(main, "DB_PATH", old_db)
    main.init_db()
    main.init_db()  # running the upgrade twice must be a no-op

    with closing(sqlite3.connect(old_db)) as conn:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(recipes)")]
        assert cols.count("favorite") == 1
        rows = conn.execute("SELECT id, title, favorite FROM recipes ORDER BY id").fetchall()
    assert rows == [(1, "Old Soup", 0), (2, "Old Bread", 0)]

    # The API, now pointed at the upgraded file, serves the old rows with favorite = false.
    listed = client.get("/recipes").json()
    assert [(r["id"], r["title"], r["favorite"]) for r in listed] == [
        (1, "Old Soup", False),
        (2, "Old Bread", False),
    ]
    assert client.get("/recipes/1").json()["ingredients"] == ["water", "salt"]
    toggled = client.post("/recipes/2/favorite").json()
    assert toggled["favorite"] is True and toggled["title"] == "Old Bread"
