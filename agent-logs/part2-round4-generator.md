# Round 4: generator report (commit `fef9174`)

Summary of the generator's report after critique round 3. Full suite: **185 passed**. On my
instruction it replaced spelling-by-spelling patches with three general rules.

1. **Units:** one list of weight/volume units and one of length units; every unit may end with
   a period (`oz.`, `tbsp.`, `lb.`, `in.`); `stick`/`sticks` added.
2. **Pack sizes:** a count followed by a sized amount (weight, volume or length, hyphenated or
   not) scales the count and keeps the size. Critic inputs at ×2: `1 8-oz package` →
   `2 8-oz package`, `2 15-ounce cans` → `4 15-ounce cans`, `2 400 g tins` → `4 400 g tins`.
   New spellings it added to prove the rule is general: `1 10-oz. bag`, `3 1-lb packages`,
   `1 750 ml bottle`, `1 9-in. crust`.
3. **Second amounts:** scaled after the first amount+unit via `plus`, `(`, `/` or a space, also
   inside `(about …)`, `(approx. …)`, `(~…)`. `12 oz. (340 g)` → `24 oz. (680 g)`,
   `1 cup (2 sticks)` → `2 cup (4 sticks)`, `1 lb. 2 oz. (510 g)` → `2 lb. 4 oz. (1020 g)`.
   **Safety rule:** if a second amount cannot be fully read, the whole line is returned
   unchanged rather than half scaled (`200 g (7,5 oz)`, `1 cup (2 large)`).
4. **Ginger:** the size rule stays; the docstring states that `2-inch piece ginger` is left
   unchanged and a test records it.
5. The over-claiming docstring is gone; it now lists exactly what is scaled, what is not, and
   when a line is returned unchanged. No earlier test had to change.
