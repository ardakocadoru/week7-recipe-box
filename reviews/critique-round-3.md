# Critique, round 3
**Verdict:** REVISE

All 146 tests pass, and every round-2 input now gives the right answer. Two common US ways of writing amounts still produce quantities a cook would follow and get wrong.

## Previous findings
- [blocker] `1-1/2` read as a range → **fixed**: x2 gives `3 cups`, x3 `4 1/2`, x0.5 `3/4`, factor=100 `150`. `1-½` x3 gives `4 1/2`.
- [major] Leading-dot decimals → **fixed**: `.5 cup` x2 gives `1 cup`, `.75` gives `1.5`, `.25 tsp` gives `0.5 tsp`.
- [major] Second quantities → **partly fixed**: `1 cup plus 2 tablespoons`, `1 lb 2 oz`, `200 g (7 oz)`, `200 g/7 oz` and `1 cup (240 ml)` are all scaled correctly. Spellings that are still missed are listed under New findings.
- [major] Sizes → **fixed** for inch/cm/mm/`"`: `9-inch pie crust` stays unchanged, and `1 9-inch pie crust` x2 gives `2 9-inch`.
- [minor] Half-even rounding → **fixed**: factor 1 returns the line unchanged, and `0.075 g` x5 gives `0.38`.
- [minor] Singular units → out of scope (supervisor decision).
- Round 1: no regressions. `1½`, `1,5 dl`, `1,000 g`, `1 1/2-2`, `2 - 3`, `2–3`, `2 to 3`, `½`, `1/16`x1/1000 (`0.000063`), `1/2`x0.2 and `2/3`x1/3 all behave as round 2 reported. Bad factors give 422, an unknown id gives 404, and the stored recipe is unchanged.

## New findings
**[major] The count before a weight-sized pack is not scaled at all**
- At x2, `"1 8-oz package cream cheese"` → unchanged. Expected `2 8-oz package`.
- Also unchanged at x2: `"2 15-ounce cans black beans"`, `"1 28 oz can tomatoes"`, `"2 400 g tins chickpeas"` and `"2 14.5-ounce cans"`. Unchanged at x0.5 too.
- Confirmed through the endpoint.
- Cause: `_CONTINUES` sees `" 8"` and gives up, because `_SIZED_ITEM` only knows inch, cm, mm and `"`.
- Why it matters: a doubled cheesecake gets half the cream cheese, and nothing warns the cook. This is the very common US form of the `1 9-inch` case that was fixed. The supervisor's rule says the count before a size should be scaled. The docstring claims it is, and it is not. No test covers it.
- Fix: let `_SIZED_ITEM` also accept a weight or volume unit (`-?\s*(oz|ounces?|g|ml|lb)\.?`), so the count is scaled and the size stays. Add tests.

**[major] Second quantity still not scaled for common spellings, so lines contradict themselves**
- At x2:
  - `"12 oz. (340 g) chocolate chips"` → `"24 oz. (340 g)"`.
  - `"2 tbsp. (30 ml) oil"` → `"4 tbsp. (30 ml)"`.
  - `"1 lb. 2 oz. beef"` → `"2 lb. 2 oz."`.
  - `"1 cup (2 sticks) butter"` → `"2 cup (2 sticks)"`.
  - `"1 stick (1/2 cup) butter"` → `"2 stick (1/2 cup)"`.
  - `"2 cups (about 500 ml) stock"` → `"4 cups (about 500 ml)"`.
- Endpoint at x2 confirmed for `12 oz. (340 g)` and `(2 sticks)`.
- Why it matters: this is the same harm as the round-2 major. A cook who weighs in grams, or counts butter sticks, uses half. Abbreviations with a period and butter sticks are everywhere in US recipes. The round-2 fix only works when the unit has no period and is in `_UNIT`.
- Fix:
  - Allow an optional `\.` after `_UNIT`.
  - Add `sticks?` to `_UNIT`.
  - If a parenthesised second amount has a unit that is not recognised or is preceded by `about`, return the line unchanged instead of scaling only half of it.
  - Add tests.

**[minor] A leading size that is the amount is no longer scaled (regression from round 2)**
- `"2-inch piece ginger"` x2 → unchanged. Round 2 gave `4-inch`, which was correct.
- Also unchanged: `"2 cm ginger"`.
- This follows from the supervisor's size rule, and the test comment acknowledges it. Flagged only because the cook ends up with half the ginger. Fix: note the limitation in the docstring.

## Rubric check
- **Correctness: fail.** `1 8-oz package` and `2 15-ounce cans` are not scaled. `12 oz. (340 g)` and `1 cup (2 sticks)` are only half scaled.
- **Tests: fail.** The tests assert on values and do not assume an empty database, but none covers sized cans or packages, units with a period, or sticks.
- **Clarity: pass.** The helpers are small and named, and the regexes are commented. One docstring overclaims: it says the count before an item size is scaled, which holds only for inch, cm, mm and `"`.
