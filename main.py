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
import unicodedata
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


# --- Ingredient scaling --------------------------------------------------------

MIN_FACTOR = 0.01
MAX_FACTOR = 100

# Single-character fractions such as "½", mapped to their exact values.
_UNICODE_FRACTIONS = {
    ch: Fraction(unicodedata.numeric(ch)).limit_denominator(10)
    for ch in "¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞"
}
_VULGAR = "".join(_UNICODE_FRACTIONS)

# Denominators people actually measure with; other fractions are shown as decimals.
_KITCHEN_DENOMINATORS = {2, 3, 4, 8, 16}

# One number. Digit runs are capped at 9 so int() never sees an absurdly long string.
_NUMBER = rf"""
      \d{{1,9}} \s+ \d{{1,9}} [/⁄] \d{{1,9}}   # mixed number: 1 1/2
    | \d{{1,9}} \s* [{_VULGAR}]                # whole plus fraction character: 1½
    | [{_VULGAR}]                              # fraction character: ½
    | \d{{1,9}} [/⁄] \d{{1,9}}                 # fraction: 1/2
    | \d{{1,9}} (?: \. \d{{1,9}} )?            # integer or decimal: 200, 1.5
"""
_RANGE_SEPARATOR = r"\s*[-–—]\s* | \s+(?i:to|or)\s+"

# A leading amount: one number or a range ("2-3", "2 - 3", "2–3", "2 to 3").
# The final lookahead rejects a match that is followed by more of a number
# ("1,5", "1,000", "1.2.3", "2-3-4", "1 2"), so a number we only partly read
# never gets scaled; the line is returned unchanged instead.
_AMOUNT = re.compile(
    rf"""
    ^ (?P<lead> \s* )
    (?P<low> {_NUMBER} )
    (?: (?P<sep> {_RANGE_SEPARATOR} ) (?P<high> {_NUMBER} ) )?
    (?! [\d.,/⁄{_VULGAR}] | (?: {_RANGE_SEPARATOR} | \s+ ) [\d{_VULGAR}] )
    """,
    re.VERBOSE,
)


def _parse_number(text: str) -> tuple[Fraction, bool] | None:
    """Return (value, written_as_fraction) for a _NUMBER match.

    Returns None for a zero denominator such as "1/0".
    """
    text = text.replace("⁄", "/")
    if text[-1] in _UNICODE_FRACTIONS:
        whole = text[:-1].strip()
        return int(whole or 0) + _UNICODE_FRACTIONS[text[-1]], True
    if "/" not in text:
        return Fraction(text), False
    whole, _, frac = text.rpartition(" ")
    num, den = (int(part) for part in frac.split("/"))
    if den == 0:
        return None
    return int(whole or 0) + Fraction(num, den), True


def _format_decimal(value: Fraction) -> str:
    """Fixed-point text: two decimals, more for small values ("0.031", not "0.03")."""
    places = 2
    while round(value * 10**places) < 10:  # keep at least two significant digits
        places += 1
    whole, rest = divmod(round(value * 10**places), 10**places)
    return f"{whole}.{rest:0{places}d}".rstrip("0").rstrip(".")


def _format_quantity(value: Fraction, as_fraction: bool) -> str:
    """Readable quantity: "400", "1 1/2" (for fraction inputs) or "2.25"."""
    if value.denominator == 1:
        return str(value.numerator)
    if as_fraction and value.denominator in _KITCHEN_DENOMINATORS:
        whole, rest = divmod(value.numerator, value.denominator)
        frac = f"{rest}/{value.denominator}"
        return f"{whole} {frac}" if whole else frac
    return _format_decimal(value)


def scale_ingredient(ingredient: str, factor: Fraction) -> str:
    """Multiply the leading amount of an ingredient line by factor.

    Both ends of a range are scaled. A line whose start is not a number we can read
    in full ("salt to taste", "1,5 dl milk", "1/0 cup") is returned unchanged.
    """
    match = _AMOUNT.match(ingredient)
    if match is None:
        return ingredient
    ends = [match["low"]] + ([match["high"]] if match["high"] else [])
    parsed = [_parse_number(end) for end in ends]
    if None in parsed:
        return ingredient
    scaled = [_format_quantity(value * factor, as_fraction) for value, as_fraction in parsed]
    amount = (match["sep"] or "").join(scaled)
    return match["lead"] + amount + ingredient[match.end():]


@app.get("/recipes/{recipe_id}/scaled")
def get_scaled_recipe(
    recipe_id: int,
    factor: float = Query(ge=MIN_FACTOR, le=MAX_FACTOR, allow_inf_nan=False),
):
    recipe = get_recipe(recipe_id)
    # repr() gives the shortest decimal for the float, so 0.1 becomes exactly 1/10.
    exact_factor = Fraction(repr(factor))
    recipe["ingredients"] = [
        scale_ingredient(item, exact_factor) for item in recipe["ingredients"]
    ]
    return recipe
