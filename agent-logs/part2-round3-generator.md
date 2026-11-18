# Round 3: generator report (commit `2947078`)

Summary of the generator's report after critique round 2. Full suite: **146 passed**.

| Critique finding | What the generator changed |
|---|---|
| [blocker] `1-1/2` read as a range | `N-a/b` and `N-½` are read as mixed numbers before a range is tried. `1-1/2 cups` ×2 → `3 cups`; true ranges still work (`2-3` → `4-6`, `1/2-1` → `1-2`). Ambiguous lines (`1-3/2`, downward ranges such as `3 to 2`) are left unchanged. |
| [major] leading-dot decimals | `.5 cup milk` ×2 → `1 cup milk`; `.5-1` → `1-2`. |
| [major] second quantities | Scaled only when the first amount has a unit: `1 cup plus 2 tablespoons` → `2 cup plus 4 tablespoons`, `1 lb 2 oz` → `2 lb 4 oz`, `200 g (7 oz)` → `400 g (14 oz)`, `200 g/7 oz` → `400 g/14 oz`. Pack sizes unchanged as before: `1 (14 oz) can` → `2 (14 oz) can`. |
| [major] sizes | `N-inch`, `N"`, `N cm`, `N mm` are item sizes and never scaled; the count before them is: `1 9-inch pie crust` ×2 → `2 9-inch pie crust`. |
| [minor] rounding | Half up with exact `Fraction` maths; factor 1 returns the line exactly as stored. |
| [minor] plural units | Not implemented, as I decided; recorded as a known limitation. |

Matching rules are now separate named patterns (`_NUMBER`, `_AMOUNT`, `_CONTINUES`, `_SIZE`,
`_SIZED_ITEM`, `_UNIT`, `_SECOND_QUANTITY_LINK`) with two helpers, `_read_amount` and
`_scale_amount`. Behaviour change the generator flagged itself: `2-inch piece ginger` is no
longer scaled under my size rule, because the code cannot tell a ginger piece from a pie size.
