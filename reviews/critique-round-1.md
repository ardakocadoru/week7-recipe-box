# Critique, round 1
**Verdict:** REVISE

## Findings

**[blocker] Numbers the parser reads only partly get scaled to wrong values**
Recipe with these lines, `GET /recipes/{id}/scaled?factor=2` and `?factor=0.5`:
- `"1½ cups flour"`: x2 gives `"2½ cups flour"` (should be 3 cups). x0.5 gives `"0.5½ cups flour"`, which is unreadable.
- `"1,5 dl milk"` (decimal comma): x2 gives `"2,5 dl milk"` (should be 3 dl). x0.5 gives `"0.5,5 dl milk"`.
- `"1,000 g flour"`: x0.5 gives `"0.5,000 g flour"`.
- `"1 1/2-2 cups stock"`: x0.5 gives `"0.5 1/2-2 cups stock"`. The mixed-number branch fails the lookahead, so the regex falls back to the integer branch and matches just `"1"`.

Why it matters: the code comment says "anything we cannot read fully is left untouched". That is false. These are wrong results for lines people really type or paste. None of them is tested.
Fix: widen the negative lookahead to reject `,`, Unicode fraction characters (U+00BC–U+00BE, U+2150–U+215E) and a trailing `\s*\d+/`, so a partly read token leaves the whole line unchanged.

**[blocker] Ranges written with spaces, an en dash or "to" scale only the first number**
x2: `"2 - 3 eggs"` gives `"4 - 3 eggs"`, `"2–3 eggs"` gives `"4–3 eggs"`, `"2 to 3 eggs"` gives `"4 to 3 eggs"`. x(1/3): `"2 - 3 eggs"` gives `"0.67 - 3 eggs"`.
Why it matters: the output is an inverted range, which is wrong and confusing. The test comment "ranges are not understood, so left alone" holds only for the exact ASCII form `2-3`.
Fix: either scale both ends of a range (`N\s*(-|–|to)\s*M`) or detect the range and leave the line unchanged. Add tests for each spelling.

**[major] Unicode fractions are silently not scaled**
`"½ cup sugar"` at factor=2 returns `"½ cup sugar"` unchanged, but it should be `"1 cup sugar"`. Recipes pasted from the web often use these characters. The user gets a doubled recipe with half the sugar it needs, and nothing tells them.
Fix: map the Unicode fraction characters to `n/d` before parsing, and add a test.

**[minor] Small or huge factors give unreadable output**
- `factor=0.0000001` gives `"2e-05 g flour"`.
- `scale_ingredient("1/16 tsp cayenne", 1/1000)` gives `"6.25e-05 tsp cayenne"`.
- `factor=1.7976931348623157e308` gives a quantity 309 digits long.

The rubric requires readable output. The `:.3g` fallback produces scientific notation, and nothing caps the factor.
Fix: cap the factor (for example `le=100`) and format the fallback with fixed-point output instead of `g`.

**[minor] Awkward or lossy fractions**
- `"1/2 cup water"` at factor=0.2 gives `"1/10 cup"`.
- `"2/3 cup milk"` x(1/3) gives `"2/9 cup"`.
- `"1/16 tsp"` x0.5 gives `"0.03 tsp"`, which loses 1/32.

A denominator limit of 16 still lets through 9ths, 10ths and 7ths, which no one measures.
Fix: allow only kitchen denominators (2, 3, 4, 8, 16) and use decimals for everything else.

**[minor] The repr() claim is untested**
`Fraction(repr(0.2))` gives `"1/10 cup water"` but `Fraction(0.2)` gives `"0.1 cup water"`. Every endpoint test uses factors that are exact in binary (2, 3, 4, 0.5), so swapping out `repr()` would break no test.
Fix: add an endpoint test with `factor=0.2` on a fraction line.

## Rubric check
Correctness: **fail**. Wrong values for `1½`, `1,5`, `2 - 3`, `2–3`, `2 to 3` and `1 1/2-2`, and `½` is not scaled at all.
Tests: **fail**. All 58 pass, but none covers the cases above, and the range test generalises from a single spelling.
Clarity: **pass**. The helpers are small and well named, with no dead code. Two comments overclaim, though ("anything we cannot read fully is left untouched", "ranges ... left alone").

## What is good
- `Fraction` arithmetic keeps decimal results clean: `0.1 x 3` gives `"0.3"`, and there is no `400.0`.
- Bad factors (`0`, `-2`, `-0`, `abc`, `nan`, `inf`, `1e400`, `1e-400`, `2,5`) all return 422, and I could not trigger any 500.
- The stored recipe stays unchanged. The tests create their own rows and assert on the scaled values, not just the status code.
- ASCII integers, decimals, fractions and mixed numbers scale correctly. A fraction written as a fraction stays a fraction (`1/2` x3 gives `1 1/2`).
