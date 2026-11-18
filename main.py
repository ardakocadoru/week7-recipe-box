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
import math
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
#
# Known limitation: units are not re-inflected, so "1 cup" x2 gives "2 cup" and
# "2 eggs" x0.5 gives "1 eggs".

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
    (?: \d{{1,9}} \s+ \d{{1,9}} [/⁄] \d{{1,9}}   # mixed number: 1 1/2
      | \d{{1,9}} - \d{{1,9}} [/⁄] \d{{1,9}}     # hyphenated mixed number: 1-1/2
      | \d{{1,9}} (?: \s* | - ) [{_VULGAR}]      # whole plus fraction character: 1½, 1-½
      | [{_VULGAR}]                              # fraction character: ½
      | \d{{1,9}} [/⁄] \d{{1,9}}                 # fraction: 1/2
      | \d{{0,9}} \. \d{{1,9}}                   # decimal: 1.5, .5
      | \d{{1,9}}                                # integer: 200
    )
"""
_RANGE_SEPARATOR = r"(?: \s*[-–—]\s* | \s+(?i:to|or)\s+ )"

# An amount: one number or a range ("2-3", "2 - 3", "2–3", "2 to 3").
_AMOUNT = re.compile(
    rf"(?P<low> {_NUMBER} ) (?: (?P<sep> {_RANGE_SEPARATOR} ) (?P<high> {_NUMBER} ) )?",
    re.VERBOSE,
)
# Text right after an amount that means the number goes on ("1,5", "1,000", "2-3-4",
# "1 2"): we read it only partly, so the line must not be scaled.
_CONTINUES = re.compile(
    rf"[\d.,/⁄{_VULGAR}] | (?: {_RANGE_SEPARATOR} | \s+ ) (?: [\d{_VULGAR}] | \.\d )",
    re.VERBOSE,
)
# Units. Each may end with a period ("oz.", "tbsp."). Volume and weight units measure
# an ingredient; length units only ever describe an item's size.
_MEASURE_UNIT = r"""(?i: cups? | tablespoons? | tbsps? | tbs | teaspoons? | tsps?
                       | pounds? | lbs? | ounces? | oz | fl \s? oz
                       | kilograms? | kgs? | grams? | g | milligrams? | mg
                       | millilit(?:er|re)s? | ml | lit(?:er|re)s? | l | dl | cl
                       | pints? | pt | quarts? | qt | gallons? | gal | sticks? ) \b \.?"""
_LENGTH_UNIT = r"""(?: (?i: (?: inch(?:es)? | cm | mm ) \b \.? | in\. ) | ["″] )"""
_UNIT_AHEAD = re.compile(rf"\s* {_MEASURE_UNIT}", re.VERBOSE)

# A leading length is an item size, not an amount: "9-inch pie crust", "20 cm tin".
_SIZE = re.compile(rf"\s*-?\s* {_LENGTH_UNIT}", re.VERBOSE)
# A pack or item size between a count and the item: "1 8-oz package",
# "2 400 g tins", "2 14.5-ounce cans", "1 9-inch crust". The count is scaled, the
# size is not.
_PACK_SIZE = re.compile(
    rf"\s+ {_NUMBER} \s*-?\s* (?: {_MEASURE_UNIT} | {_LENGTH_UNIT} )", re.VERBOSE
)

# A unit and a connector that lead to a second amount of the same ingredient:
# "1 cup plus 2 tbsp", "1 lb 2 oz", "200 g (about 7 oz)", "200 g/7 oz".
# A plain space is a weak link: "2 cups 2% milk" has no second amount, it just names
# the ingredient. The others always introduce one.
_SECOND_AMOUNT_LINK = re.compile(
    rf"""\s* {_MEASURE_UNIT}
         (?: (?P<strong> \s+ (?i:plus) \s+
                       | \s* \( \s* (?: (?i: about | approx\.? | approximately | roughly
                                            | around ) \s+ | ~ \s* )?
                       | \s* / \s* )
           | \s+ )
         (?= [\d{_VULGAR}] | \.\d )""",
    re.VERBOSE,
)


def _parse_number(text: str) -> tuple[Fraction, bool] | None:
    """Return (value, written_as_fraction) for a _NUMBER match.

    Returns None for a zero denominator ("1/0") or a mixed number whose fraction is
    not proper ("1-3/2"), since neither has one clear meaning.
    """
    text = text.replace("⁄", "/")
    frac = re.search(rf"(\d+)/(\d+)$|[{_VULGAR}]$", text)
    if frac is None:
        return Fraction(text), False
    whole = int(text[: frac.start()].strip().rstrip("-") or 0)
    if frac[0] in _UNICODE_FRACTIONS:
        return whole + _UNICODE_FRACTIONS[frac[0]], True
    num, den = int(frac[1]), int(frac[2])
    if den == 0 or (whole and num >= den):
        return None
    return whole + Fraction(num, den), True


def _round_half_up(value: Fraction) -> int:
    return math.floor(value + Fraction(1, 2))


def _format_decimal(value: Fraction) -> str:
    """Fixed-point text: two decimals, more for small values ("0.031", not "0.03")."""
    places = 2
    while _round_half_up(value * 10**places) < 10:  # keep two significant digits
        places += 1
    whole, rest = divmod(_round_half_up(value * 10**places), 10**places)
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


def _read_amount(line: str, pos: int) -> re.Match | None:
    """The amount starting at pos, or None if there is none or it is only partly read."""
    amount = _AMOUNT.match(line, pos)
    if amount is None:
        return None
    end = amount.end()
    if _CONTINUES.match(line, end) and not _PACK_SIZE.match(line, end):
        return None
    return amount


def _scale_amount(amount: re.Match, factor: Fraction) -> str | None:
    """Scaled text for an amount, or None if it cannot be read safely."""
    ends = [_parse_number(amount["low"])]
    if amount["high"]:
        ends.append(_parse_number(amount["high"]))
    if None in ends:
        return None
    if len(ends) == 2 and ends[1][0] < ends[0][0]:
        return None  # a descending "range" such as "1 - 1/2" is not a real range
    return (amount["sep"] or "").join(
        _format_quantity(value * factor, as_fraction) for value, as_fraction in ends
    )


def scale_ingredient(ingredient: str, factor: Fraction) -> str:
    """Multiply the quantities of an ingredient line by factor.

    Scaled:
    - the leading amount, including both ends of a range ("2-3 eggs"). A leading
      weight or volume is an amount even when hyphenated: "8-oz package" becomes
      "16-oz package", the same total;
    - second amounts of the same ingredient that follow the first amount's unit
      via "plus", "(", "/" or a space and carry a unit of their own:
      "1 cup plus 2 tbsp", "1 lb. 2 oz.", "12 oz. (340 g)", "2 cups (about 500 ml)".

    Not scaled:
    - a pack or item size after the count ("1 8-oz package", "2 400 g tins",
      "1 9-inch crust"): only the count changes;
    - pack sizes in brackets after a bare count ("1 (14 oz) can") or after "x"
      ("3 x 200 g packs");
    - a leading length ("9-inch pie crust", "20 cm tart tin"), which is read as an
      item size. Limitation: this also leaves "2-inch piece ginger" and "2 cm
      ginger" unchanged, although there the length is the amount to scale.

    Returned unchanged: lines with no readable leading amount ("salt to taste",
    "1,5 dl milk", "1/0 cup"); lines with a second amount that cannot be fully
    read, or whose unit is not recognised ("200 g (7,5 oz)", "1 cup (2 large)"),
    so a line is never half scaled; and every line when factor is 1.
    """
    if factor == 1:
        return ingredient
    first = _read_amount(ingredient, len(ingredient) - len(ingredient.lstrip()))
    if first is None or _SIZE.match(ingredient, first.end()):
        return ingredient
    amounts = [first]
    if not _PACK_SIZE.match(ingredient, first.end()):
        while link := _SECOND_AMOUNT_LINK.match(ingredient, amounts[-1].end()):
            amount = _read_amount(ingredient, link.end())
            if amount is None:
                return ingredient  # second amount only partly readable: "(7,5 oz)"
            if not _UNIT_AHEAD.match(ingredient, amount.end()):
                if link["strong"] is not None:
                    return ingredient  # unknown unit: "(2 large)"
                break  # a number in the name, not an amount: "2 cups 2% milk"
            amounts.append(amount)

    parts, last = [], 0
    for amount in amounts:
        scaled = _scale_amount(amount, factor)
        if scaled is None:
            return ingredient
        parts += [ingredient[last : amount.start()], scaled]
        last = amount.end()
    return "".join(parts) + ingredient[last:]


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
