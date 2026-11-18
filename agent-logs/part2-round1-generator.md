# Round 1: generator report (commit `d54c65c`, 10:46:29)

Summary of the generator's report, in its own terms.

- `GET /recipes/{recipe_id}/scaled?factor=N` returns the same shape as `GET /recipes/{id}`
  with the ingredients scaled. It reuses `get_recipe()`, so an unknown id gives 404.
- `factor` is a float with `Query(gt=0, allow_inf_nan=False)`: zero, negative, non-numeric,
  empty, missing, `nan`, `inf`, `1e400` and `1/2` are rejected with 422.
- The factor is converted with `Fraction(repr(factor))`; all maths uses `Fraction`, so no float
  noise. The stored recipe is never written to.
- Helpers: `_QUANTITY` (pattern), `_parse_quantity`, `_format_quantity`, `scale_ingredient`.
- Formats: integers (`200 g` → `400 g`, also `200g`), decimals (`1.5 cups` ×2 → `3 cups`),
  fractions (`1/2 tsp` ×3 → `1 1/2 tsp`), mixed numbers (`1 1/2 cups` ×3 → `4 1/2 cups`).
  Only the leading quantity changes.
- Left unchanged: no leading number (`salt to taste`), ranges (`2-3 eggs`), malformed numbers
  (`1.2.3`), zero denominators (`1/0`), digit runs over 9 digits.
- Output: whole results print as integers; fraction inputs stay mixed fractions when the
  denominator is 16 or less; everything else is rounded to 2 decimals; results too small for 2
  decimals keep 3 significant digits.
- Tests: `test_scaling.py`, 41 cases. Full suite: **58 passed**.
- Known gaps the generator reported itself: unicode fractions (`½`) and ranges are not
  scaled; a factor of `1e-300` returns scientific notation such as `1.7e-300 g`; no upper or
  lower limit on the factor.
