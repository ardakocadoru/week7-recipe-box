# Critique, round 4
**Verdict:** ACCEPT

All 185 tests pass. I ran every input below through `scale_ingredient` directly, and the starred ones also through the endpoint.

## Previous findings
**Round 3**
- [major] Count before a pack size → **fixed**. At x2, `1 8-oz package`* gives `2 8-oz`, `2 15-ounce cans` gives `4`, `1 28 oz can` gives `2`, `2 400 g tins` gives `4` and `2 14.5-ounce cans` gives `4`. At x0.5, `1 8-oz` gives `0.5`. Tested at test_scaling.py lines 369-374.
- [major] Second amounts after units with a period, or in sticks → **fixed**. At x2:
  - `12 oz. (340 g)`* gives `24 oz. (680 g)`
  - `2 tbsp. (30 ml)` gives `4 tbsp. (60 ml)`
  - `1 lb. 2 oz.` gives `2 lb. 4 oz.`
  - `1 cup (2 sticks)`* gives `2 cup (4 sticks)`
  - `1 stick (1/2 cup)` gives `2 stick (1 cup)`
  - `2 cups (about 500 ml)` gives `4 cups (about 1000 ml)`
  - All are tested (lines 396-409).
- [minor] Ginger limitation → **documented** in the docstring and in a test (line 437).

**Rounds 1-2 (no regressions)**
- These behave as before: `1-1/2` (x2 `3`, x3 `4 1/2`, x0.5 `3/4`), `.5` and `.75`, `1 cup plus 2 tablespoons`, `1 lb 2 oz`, `200 g (7 oz)`, `200 g/7 oz`, `1 cup (240 ml)`, `9-inch` and `1 9-inch`, `1½`, `1,5 dl`, `1,000 g`, `1 1/2-2` and the range spellings `2 - 3`, `2–3`, `2 to 3`.
- Also unchanged: `½`, `1/16`x1/1000 gives `0.000063`, `0.075 g`x5 gives `0.38`, and `1.005 g`x1 is unchanged.
- Bad factors (`0`, `-1`, `abc`, `nan`, `inf`, `1e400`, `0.001`, `101`) give 422. An unknown id gives 404. The stored recipe is unchanged, and `factor=0.2` turns `1/2 cup` into `0.1 cup`.

## New findings
**[minor] Second amount after `/ about` or `or` is not scaled**
- At x2, `"1 cup / about 240 ml milk"`* gives `"2 cup / about 240 ml"`. Expected: `480 ml`, or the line unchanged.
- At x2, `"1 cup or 240 ml milk"`* gives `"2 cup or 240 ml"`.
- Why it matters: the line contradicts itself. Both spellings are rare (the common `(about 240 ml)` works), so this does not block.
- Fix: allow the optional "about" prefix after `/` as well. For `or`, either add it as a strong link or return the line unchanged.

I tried about 60 other real-world forms and they were all correct or safely left unchanged. They include:
- ranges followed by a pack size (`2-3 14-oz cans` gives `4-6`) and second-amount ranges (`(480-720 ml)`)
- `2 1-inch pieces`, `1 12 oz bag (340 g)`, `3 x 200 g packs`, `1 (8 oz) package`
- `1 lb. 80/20 beef`, `2 cups 2% milk`, `4 oz 70% chocolate`
- `1 cup (8 fl. oz)` (unchanged)
- full-width digits

I could not trigger a 500.

## Rubric check
- **Correctness: pass.** Every listed quantity type, both range spellings, second amounts and pack counts scale correctly. Unparseable lines come back unchanged, and nothing gives a 500.
- **Tests: pass.** 185 tests assert on scaled values, create their own rows, and cover each round-3 input, including x0.5 and endpoint cases.
- **Clarity: pass.** The helpers are small and named, the regexes are commented, and the docstring matches the behaviour. One small point: `_read_amount` only works because `_CONTINUES` and `_PACK_SIZE` fit together, and nothing in the code says so.

## Sign-off note
No blockers or majors remain. Every earlier finding is fixed and tested, and the generalised unit, pack-size and second-amount rules introduce no wrong amounts on common recipe lines. Remaining limitations:
- Units are not pluralised.
- `2-inch piece ginger` and `2 cm ginger` are not scaled.
- Decimal commas and lines with a second amount the code cannot fully read come back unchanged on purpose.
- Rare `/ about` and `or` second amounts are not scaled (minor, above).
