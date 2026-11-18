from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from main import app, scale_ingredient

client = TestClient(app)

INGREDIENTS = [
    "200 g flour",
    "1.5 cups milk",
    "1/2 tsp salt",
    "1 1/2 cups sugar",
    "salt to taste",
    "a pinch of nutmeg",
]


def _create(ingredients=INGREDIENTS, title="Scaling test"):
    r = client.post(
        "/recipes", json={"title": title, "ingredients": ingredients, "tags": ["bake"]}
    )
    assert r.status_code == 200
    return r.json()


# --- endpoint -----------------------------------------------------------------


def test_scaled_doubles_every_quantity():
    rec = _create()
    r = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 2})
    assert r.status_code == 200
    assert r.json()["ingredients"] == [
        "400 g flour",
        "3 cups milk",
        "1 tsp salt",
        "3 cups sugar",
        "salt to taste",
        "a pinch of nutmeg",
    ]


def test_scaled_keeps_other_fields():
    rec = _create(title="Keep my fields")
    client.post(f"/recipes/{rec['id']}/favorite")
    body = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 3}).json()
    assert body["id"] == rec["id"]
    assert body["title"] == "Keep my fields"
    assert body["tags"] == ["bake"]
    assert body["favorite"] is True


def test_scaled_with_fractional_factor():
    rec = _create()
    body = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 0.5}).json()
    assert body["ingredients"] == [
        "100 g flour",
        "0.75 cups milk",
        "1/4 tsp salt",
        "3/4 cups sugar",
        "salt to taste",
        "a pinch of nutmeg",
    ]


def test_scaling_does_not_change_stored_recipe():
    rec = _create()
    client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 4})
    assert client.get(f"/recipes/{rec['id']}").json()["ingredients"] == INGREDIENTS
    # Scaling twice from the stored recipe gives the same answer (no compounding).
    again = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 4}).json()
    assert again["ingredients"][0] == "800 g flour"


def test_scaled_unknown_recipe_404():
    r = client.get("/recipes/99999999/scaled", params={"factor": 2})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "factor",
    ["0", "-2", "abc", "", "nan", "inf", "1/2", "2,5", "0.0000001", "0.009", "100.5", "1e308"],
)
def test_scaled_rejects_bad_factor(factor):
    rec = _create()
    r = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": factor})
    assert r.status_code == 422


@pytest.mark.parametrize("factor, expected", [("0.01", "2 g flour"), ("100", "20000 g flour")])
def test_scaled_accepts_factor_limits(factor, expected):
    rec = _create(ingredients=["200 g flour"])
    r = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": factor})
    assert r.status_code == 200
    assert r.json()["ingredients"] == [expected]


def test_scaled_factor_is_read_as_exact_decimal():
    # 0.2 is not exact in binary; it must still act as exactly 1/5.
    rec = _create(ingredients=["2 1/2 cups flour", "1/2 cup water"])
    body = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 0.2}).json()
    assert body["ingredients"] == ["1/2 cups flour", "0.1 cup water"]


def test_scaled_endpoint_handles_critique_inputs():
    lines = ["1½ cups flour", "1,5 dl milk", "1,000 g flour", "1 1/2-2 cups stock",
             "2 - 3 eggs", "2–3 eggs", "2 to 3 eggs", "½ cup sugar"]
    rec = _create(ingredients=lines)
    body = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 2}).json()
    assert body["ingredients"] == [
        "3 cups flour", "1,5 dl milk", "1,000 g flour", "3-4 cups stock",
        "4 - 6 eggs", "4–6 eggs", "4 to 6 eggs", "1 cup sugar",
    ]
    assert client.get(f"/recipes/{rec['id']}").json()["ingredients"] == lines


def test_scaled_requires_factor():
    rec = _create()
    r = client.get(f"/recipes/{rec['id']}/scaled")
    assert r.status_code == 422


def test_scaled_recipe_without_ingredients():
    rec = _create(ingredients=[])
    body = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 2}).json()
    assert body["ingredients"] == []


# --- scale_ingredient ---------------------------------------------------------


@pytest.mark.parametrize(
    "ingredient, factor, expected",
    [
        # integers
        ("200 g flour", 2, "400 g flour"),
        ("3 eggs", 1, "3 eggs"),
        ("200g flour", 2, "400g flour"),
        # decimals: no "400.0", no float noise
        ("1.5 cups milk", 2, "3 cups milk"),
        ("0.1 cups oil", 3, "0.3 cups oil"),
        ("2.5 dl cream", 1.5, "3.75 dl cream"),
        ("100 g butter", Fraction(1, 3), "33.33 g butter"),
        # fractions
        ("1/2 tsp salt", 2, "1 tsp salt"),
        ("1/2 tsp salt", 3, "1 1/2 tsp salt"),
        ("1/3 cup cream", 2, "2/3 cup cream"),
        ("3/4 cup oats", Fraction(1, 2), "3/8 cup oats"),
        # mixed numbers
        ("1 1/2 cups sugar", 2, "3 cups sugar"),
        ("1 1/2 cups sugar", 3, "4 1/2 cups sugar"),
        ("2 1/4 cups flour", Fraction(1, 2), "1 1/8 cups flour"),
        # fractions whose result would be an awkward fraction fall back to decimals
        ("1/2 cup stock", Fraction(3, 10), "0.15 cup stock"),
        ("1/2 cup water", Fraction(1, 5), "0.1 cup water"),
        ("2/3 cup milk", Fraction(1, 3), "0.22 cup milk"),
        # small results keep two significant digits, in fixed-point notation
        ("1/16 tsp", Fraction(1, 2), "0.031 tsp"),
        ("1 g saffron", Fraction(1, 1000), "0.001 g saffron"),
        ("1/16 tsp cayenne", Fraction(1, 1000), "0.000063 tsp cayenne"),  # half up
        # Unicode fraction characters, alone or after a whole number
        ("½ cup sugar", 2, "1 cup sugar"),
        ("½ cup sugar", 3, "1 1/2 cup sugar"),
        ("1½ cups flour", 2, "3 cups flour"),
        ("1½ cups flour", Fraction(1, 2), "3/4 cups flour"),
        ("1 ¼ cups oats", 2, "2 1/2 cups oats"),
        ("⅓ cup oil", 3, "1 cup oil"),
        ("¾ tsp cumin", Fraction(1, 5), "0.15 tsp cumin"),
        ("1⁄2 cup rice", 3, "1 1/2 cup rice"),  # U+2044 fraction slash
    ],
)
def test_scale_ingredient_quantities(ingredient, factor, expected):
    assert scale_ingredient(ingredient, Fraction(factor)) == expected


@pytest.mark.parametrize(
    "ingredient",
    [
        "salt to taste",
        "a pinch of nutmeg",
        "",
        "   ",
        "1/0 cup water",  # zero denominator
        "1 1/0 cup water",
        "1/0-2 cups water",
        "1.2.3 mystery",
        "1.5.",
        # decimal commas and thousands separators: not guessed at
        "1,5 dl milk",
        "1,000 g flour",
        # numbers that continue past what we read
        "1 2 eggs",
        "2-3-4 eggs",
        "1/2½ cup",
        "12345678901 g flour",
    ],
)
def test_scale_ingredient_leaves_unreadable_lines_unchanged(ingredient):
    assert scale_ingredient(ingredient, Fraction(2)) == ingredient


@pytest.mark.parametrize("factor", [Fraction(2), Fraction(1, 2)])
@pytest.mark.parametrize(
    "ingredient", ["1½ cups flour", "1,5 dl milk", "1,000 g flour", "1 1/2-2 cups stock"]
)
def test_partly_readable_numbers_are_never_mangled(ingredient, factor):
    # From the round-1 critique: x2 and x0.5 used to give e.g. "2½" or "0.5,5".
    expected = {
        ("1½ cups flour", 2): "3 cups flour",
        ("1½ cups flour", Fraction(1, 2)): "3/4 cups flour",
        ("1 1/2-2 cups stock", 2): "3-4 cups stock",
        ("1 1/2-2 cups stock", Fraction(1, 2)): "3/4-1 cups stock",
    }.get((ingredient, factor), ingredient)
    assert scale_ingredient(ingredient, factor) == expected


@pytest.mark.parametrize(
    "ingredient, factor, expected",
    [
        ("2-3 eggs", 2, "4-6 eggs"),
        ("2 - 3 eggs", 2, "4 - 6 eggs"),
        ("2–3 eggs", 2, "4–6 eggs"),  # en dash
        ("2 to 3 eggs", 2, "4 to 6 eggs"),
        ("2 To 3 eggs", 2, "4 To 6 eggs"),
        ("2 or 3 eggs", 2, "4 or 6 eggs"),
        ("2 - 3 eggs", Fraction(1, 3), "0.67 - 1 eggs"),
        ("1/2-1 cup milk", 2, "1-2 cup milk"),
        ("1 1/2-2 cups stock", Fraction(1, 2), "3/4-1 cups stock"),
    ],
)
def test_scale_ingredient_scales_both_ends_of_a_range(ingredient, factor, expected):
    assert scale_ingredient(ingredient, Fraction(factor)) == expected


@pytest.mark.parametrize(
    "ingredient, expected",
    [
        ("2 eggs, beaten for 5 minutes", "4 eggs, beaten for 5 minutes"),
        ("eggs: 2", "eggs: 2"),
        ("2 cups 2% milk", "4 cups 2% milk"),
        ("1 lb 2 eggs", "2 lb 2 eggs"),
        # pack sizes are part of the item, not an amount to scale
        ("1 (14 oz) can tomatoes", "2 (14 oz) can tomatoes"),
        ("3 x 200 g packs", "6 x 200 g packs"),
    ],
)
def test_scale_ingredient_leaves_other_numbers_alone(ingredient, expected):
    assert scale_ingredient(ingredient, Fraction(2)) == expected


# --- round-2 critique ---------------------------------------------------------


@pytest.mark.parametrize(
    "ingredient, factor, expected",
    [
        ("1-1/2 cups flour", 2, "3 cups flour"),
        ("1-1/2 cups flour", 3, "4 1/2 cups flour"),
        ("1-1/2 cups flour", Fraction(1, 2), "3/4 cups flour"),
        ("1-1/2 cups flour", 100, "150 cups flour"),
        ("1-½ cups", 3, "4 1/2 cups"),
        ("2-1/4 cups", 2, "4 1/2 cups"),
        ("1-1/2-2 cups stock", 2, "3-4 cups stock"),
    ],
)
def test_hyphenated_mixed_numbers(ingredient, factor, expected):
    assert scale_ingredient(ingredient, Fraction(factor)) == expected


@pytest.mark.parametrize(
    "ingredient, expected",
    [
        # true ranges keep working
        ("2-3 eggs", "4-6 eggs"),
        ("1/2-1 cup milk", "1-2 cup milk"),
        ("1 1/2-2 cups stock", "3-4 cups stock"),
        # ambiguous: improper fraction after the hyphen, or a descending "range"
        ("1-3/2 cups", "1-3/2 cups"),
        ("1 - 1/2 cups", "1 - 1/2 cups"),
        ("3 to 2 eggs", "3 to 2 eggs"),
    ],
)
def test_hyphen_ranges_versus_mixed_numbers(ingredient, expected):
    assert scale_ingredient(ingredient, Fraction(2)) == expected


@pytest.mark.parametrize(
    "ingredient, factor, expected",
    [
        (".5 cup milk", 2, "1 cup milk"),
        (".75 cup sugar", 2, "1.5 cup sugar"),
        (".25 tsp salt", 2, "0.5 tsp salt"),
        (".5 cup milk", 3, "1.5 cup milk"),
        (".5-1 cup water", 2, "1-2 cup water"),
    ],
)
def test_leading_dot_decimals(ingredient, factor, expected):
    assert scale_ingredient(ingredient, Fraction(factor)) == expected


@pytest.mark.parametrize(
    "ingredient, expected",
    [
        ("1 cup plus 2 tablespoons flour", "2 cup plus 4 tablespoons flour"),
        ("1 lb 2 oz beef", "2 lb 4 oz beef"),
        ("200 g (7 oz) butter", "400 g (14 oz) butter"),
        ("200 g/7 oz butter", "400 g/14 oz butter"),
        ("1 cup (240 ml) milk", "2 cup (480 ml) milk"),
        ("200g/7oz butter", "400g/14oz butter"),
        ("2-3 cups (480-720 ml) stock", "4-6 cups (960-1440 ml) stock"),
        # a second quantity we can read only partly leaves the whole line alone
        ("200 g (7,5 oz) butter", "200 g (7,5 oz) butter"),
    ],
)
def test_second_quantities_are_scaled(ingredient, expected):
    assert scale_ingredient(ingredient, Fraction(2)) == expected


@pytest.mark.parametrize(
    "ingredient, expected",
    [
        ("9-inch pie crust", "9-inch pie crust"),
        ("1 9-inch pie crust", "2 9-inch pie crust"),
        ('1 9" pie crust', '2 9" pie crust'),
        ("1 9 inch pie crust", "2 9 inch pie crust"),
        ("1 20 cm tart tin", "2 20 cm tart tin"),
        ("20 cm tart tin", "20 cm tart tin"),
        # a leading size is never scaled, even when it measures the ingredient
        ("2-inch piece ginger", "2-inch piece ginger"),
    ],
)
def test_sizes_are_not_scaled(ingredient, expected):
    assert scale_ingredient(ingredient, Fraction(2)) == expected


def test_decimals_round_half_up():
    assert scale_ingredient("0.025 g yeast", Fraction(5)) == "0.13 g yeast"
    assert scale_ingredient("0.075 g yeast", Fraction(5)) == "0.38 g yeast"
    assert scale_ingredient("1.0025 g salt", Fraction(2)) == "2.01 g salt"


@pytest.mark.parametrize("ingredient", ["1.005 g salt", "0.125 g yeast", "1 3/2 cups", "2 cup"])
def test_factor_one_returns_line_unchanged(ingredient):
    assert scale_ingredient(ingredient, Fraction(1)) == ingredient


def test_scaled_endpoint_handles_round_2_inputs():
    lines = ["1-1/2 cups flour", ".5 cup milk", "1 lb 2 oz beef", "200 g (7 oz) butter",
             "1 9-inch pie crust", "9-inch pie crust", "1.005 g salt"]
    rec = _create(ingredients=lines)
    body = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 2}).json()
    assert body["ingredients"] == [
        "3 cups flour", "1 cup milk", "2 lb 4 oz beef", "400 g (14 oz) butter",
        "2 9-inch pie crust", "9-inch pie crust", "2.01 g salt",
    ]
    same = client.get(f"/recipes/{rec['id']}/scaled", params={"factor": 1}).json()
    assert same["ingredients"] == lines
