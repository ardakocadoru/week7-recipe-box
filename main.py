"""Recipe Box — starter app for Week 7.

A tiny FastAPI service for recipes and tags, with a static frontend. Use it as the
playground for concurrent multi-agent work and a generator-critic loop.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
    # open http://localhost:8000/
Test:
    pytest
"""
import json
import re
import sqlite3
from contextlib import closing
from fractions import Fraction
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
DB_PATH = BASE / "recipes.db"

app = FastAPI(title="Recipe Box")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recipes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                ingredients TEXT NOT NULL,  -- JSON list of strings
                tags        TEXT NOT NULL,  -- JSON list of strings
                favorite    INTEGER NOT NULL DEFAULT 0
            )"""
        )
        # In-place upgrade for databases created before the favorite column existed.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(recipes)")}
        if "favorite" not in columns:
            conn.execute(
                "ALTER TABLE recipes ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0"
            )
        conn.commit()


init_db()


class RecipeIn(BaseModel):
    title: str
    ingredients: list[str] = []
    tags: list[str] = []


def _row_to_recipe(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": json.loads(row["ingredients"]),
        "tags": json.loads(row["tags"]),
        "favorite": bool(row["favorite"]),
    }


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/recipes")
def create_recipe(recipe: RecipeIn):
    with closing(get_db()) as conn:
        cur = conn.execute(
            "INSERT INTO recipes (title, ingredients, tags) VALUES (?, ?, ?)",
            (recipe.title, json.dumps(recipe.ingredients), json.dumps(recipe.tags)),
        )
        conn.commit()
        rid = cur.lastrowid
    return {"id": rid, **recipe.model_dump(), "favorite": False}


@app.get("/recipes")
def list_recipes(tag: str | None = None):
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
    recipes = [_row_to_recipe(r) for r in rows]
    # Missing or blank ?tag= means no filter. Otherwise match a stored tag exactly,
    # ignoring case and whitespace around the query value.
    wanted = (tag or "").strip().casefold()
    if not wanted:
        return recipes
    return [rec for rec in recipes if any(t.casefold() == wanted for t in rec["tags"])]


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    with closing(get_db()) as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")
    return _row_to_recipe(row)


@app.post("/recipes/{recipe_id}/favorite")
def toggle_favorite(recipe_id: int):
    with closing(get_db()) as conn:
        # One atomic UPDATE ... RETURNING: concurrent toggles never read the same old
        # value, and the response reflects exactly the value this call wrote.
        row = conn.execute(
            "UPDATE recipes SET favorite = 1 - favorite WHERE id = ? RETURNING *",
            (recipe_id,),
        ).fetchone()
        conn.commit()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")
    return _row_to_recipe(row)


# A leading quantity: mixed number ("1 1/2"), fraction ("1/2"), decimal ("1.5") or
# integer ("200"). The lookahead stops partial matches such as "2" in "2-3 eggs" or
# "1" in "1/0 cup", so anything we cannot read fully is left untouched.
_QUANTITY = re.compile(
    r"^(?P<lead>\s*)"
    r"(?:(?P<whole>\d{1,9})\s+(?P<num>\d{1,9})/(?P<den>\d{1,9})"
    r"|(?P<frac_num>\d{1,9})/(?P<frac_den>\d{1,9})"
    r"|(?P<number>\d{1,9}(?:\.\d{1,9})?))"
    r"(?![\d./-])"
)


def _parse_quantity(match: re.Match) -> tuple[Fraction, bool] | None:
    """Return (value, written_as_fraction), or None for a zero denominator."""
    if match["number"] is not None:
        return Fraction(match["number"]), False
    if match["whole"] is not None:
        whole, num, den = int(match["whole"]), int(match["num"]), int(match["den"])
    else:
        whole, num, den = 0, int(match["frac_num"]), int(match["frac_den"])
    if den == 0:
        return None
    return whole + Fraction(num, den), True


def _format_quantity(value: Fraction, as_fraction: bool) -> str:
    """Readable quantity: "400", "1 1/2" (for fraction inputs) or "2.25"."""
    if value.denominator == 1:
        return str(value.numerator)
    if as_fraction and value.denominator <= 16:
        whole, rest = divmod(value.numerator, value.denominator)
        frac = f"{rest}/{value.denominator}"
        return f"{whole} {frac}" if whole else frac
    # Round to two decimals with exact integer arithmetic (no float overflow or noise).
    whole, cents = divmod(round(value * 100), 100)
    if whole == 0 and cents == 0:
        # Would round to "0"; keep a few significant digits instead.
        return f"{float(value):.3g}"
    return f"{whole}.{cents:02d}".rstrip("0").rstrip(".")


def scale_ingredient(ingredient: str, factor: Fraction) -> str:
    """Multiply the leading quantity of an ingredient line by factor.

    Lines without a readable leading quantity ("salt to taste") are returned as is.
    """
    match = _QUANTITY.match(ingredient)
    if match is None:
        return ingredient
    parsed = _parse_quantity(match)
    if parsed is None:
        return ingredient
    value, as_fraction = parsed
    scaled = _format_quantity(value * factor, as_fraction)
    return match["lead"] + scaled + ingredient[match.end():]


@app.get("/recipes/{recipe_id}/scaled")
def get_scaled_recipe(
    recipe_id: int,
    factor: float = Query(gt=0, allow_inf_nan=False),
):
    recipe = get_recipe(recipe_id)
    # repr() gives the shortest decimal for the float, so 0.1 becomes exactly 1/10.
    exact_factor = Fraction(repr(factor))
    recipe["ingredients"] = [
        scale_ingredient(item, exact_factor) for item in recipe["ingredients"]
    ]
    return recipe
