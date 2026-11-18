# Critique, round 2
**Verdict:** REVISE

All 102 tests pass, and every round-1 finding is fixed. The rewrite added a new blocker. Lines that are not covered at all also still produce quantities a cook would follow and get wrong.

## Previous findings
- [blocker] Partly read numbers → **fixed**: `1½` x2 gives `3 cups`, x0.5 gives `3/4 cups`. `1,5 dl` and `1,000 g` come back unchanged. `1 1/2-2` x0.5 gives `3/4-1`.
- [blocker] Ranges with spaces, en dash or "to" → **fixed**: `2 - 3`, `2–3` and `2 to 3` x2 give `4 - 6`, `4–6` and `4 to 6`. x(1/3) gives `0.67 - 1`.
- [major] Unicode fractions → **fixed**: `½ cup sugar` x2 gives `1 cup sugar`.
- [minor] Unreadable factors → **fixed**: factor must be 0.01 to 100 (`0.0000001`, `100.00000000000001` and `1e308` give 422). `1/16 tsp` x(1/1000) gives `0.000062`.
- [minor] Awkward fractions → **fixed**: `1/2` x0.2 gives `0.1`, `2/3` x(1/3) gives `0.22`, `1/16` x0.5 gives `0.031`.
- [minor] repr() untested → **fixed**: `test_scaled_factor_is_read_as_exact_decimal` would fail without it (`2 1/2` would become `0.5`).

## New findings
**[blocker] Mixed numbers written with a hyphen are read as a range**
The new range separator matches the common US form `1-1/2`.
- `"1-1/2 cups flour"` x2 gives `"2-1 cups flour"`. Expected `"3 cups"`.
- x3 gives `"3-1 1/2 cups"`.
- x0.5 gives `"0.5-1/4 cups"`.
- `"1-½ cups"` x3 gives `"3-1 1/2 cups"`.
- Through the endpoint, factor=100 gives `"100-50 cups flour"`.

Why it matters: this line was handled no better in round 1, but the new range logic now produces inverted, nonsense amounts for a very common way of writing quantities. Sometimes it looks right by accident: `2-1/4` x2 gives `4-1/2`.
Fix: when the part after the hyphen is a proper fraction with no whole number (`N-a/b`, a<b, or `N-½`), read it as a mixed number. Add tests.

**[major] Decimals with a leading dot are not scaled**
`".5 cup milk"`, `".75 cup sugar"` and `".25 tsp salt"` come back unchanged at any factor, with no warning. A doubled recipe would get half the milk it needs. Nothing tests this.
Fix: add `\.\d{1,9}` as an alternative in `_NUMBER`.

**[major] Lines with a second quantity are only partly scaled**
The rubric asks for "every quantity multiplied by N". At x2:
- `"1 cup plus 2 tablespoons flour"` gives `"2 cup plus 2 tablespoons flour"`. Expected 2 cups plus 4 tbsp.
- `"1 lb 2 oz beef"` gives `"2 lb 2 oz"`.
- `"200 g (7 oz) butter"` gives `"400 g (7 oz) butter"`, and `"200 g/7 oz butter"` gives `"400 g/7 oz"`. Both now contradict themselves.
- `"1 cup (240 ml) milk"` gives `"2 cup (240 ml)"`.

Why it matters: these forms are common in pasted recipes, and a cook reading the second unit makes the wrong amount.
Fix: also scale a quantity followed by a unit after `plus`, `(`, `/`, or between two units. If that is out of scope, return such lines unchanged and document why.

**[major] Sizes are scaled as if they were counts**
- `"9-inch pie crust"` x2 gives `"18-inch pie crust"`.
- `"1 9-inch pie crust"` x2 comes back unchanged. The lookahead rejects `1 9`, so the count of 1 is silently left unscaled.

(Ginger is fine: `"2-inch piece ginger"` gives `"4-inch piece"`, which is the same amount. `"1 (14 oz) can"` gives `"2 (14 oz) can"` and `"3 x 200 g packs"` gives `"6 x 200 g"`, both correct.)
Fix: treat `N-inch`/`N"`/`N cm` as a size. Do not scale it, and scale the count before it.

**[minor] Ties round to the even digit, so factor=1 can change an amount**
`round()` rounds a half to the even neighbour: `"0.125 g"` gives `"0.12 g"` but `"0.375 g"` gives `"0.38 g"`. `"1.005 g"` x1 gives `"1 g"`.
Fix: round half up with `Fraction` arithmetic, and return the line unchanged when factor == 1.

**[minor] Singular units after scaling**
`"1 cup"` x2 gives `"2 cup"`, and `"2 eggs"` x0.5 gives `"1 eggs"`. This is cosmetic, but now that the factor goes up to 100 it shows more often.

## Rubric check
- Correctness: **fail**. `1-1/2` is scaled to an inverted range, `.5` is never scaled, and second quantities and sizes are scaled wrongly.
- Tests: **fail**. The tests are good at their targets and assert on values, but none covers hyphenated mixed numbers, leading-dot decimals, compound quantities or sizes. `test_scale_ingredient_only_touches_leading_quantity` locks in the partial scaling as intended behaviour.
- Clarity: **pass**. The helpers are small and named, and the regex is commented. The comment "both ends of a range are scaled" hides the fact that `1-1/2` gets treated as a range.
