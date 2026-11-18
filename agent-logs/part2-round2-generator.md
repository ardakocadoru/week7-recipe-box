# Round 2: generator report (commit `047275e`)

Summary of the generator's report after critique round 1. Full suite: **102 passed**.

| Critique finding | What the generator changed |
|---|---|
| [blocker] partly read numbers | One pattern now reads the whole leading amount (a number or a range); a final check rejects a match still followed by part of a number. `1,5 dl` and `1,000 g` are left unchanged (no guessing). `1½ cups` ×2 → `3 cups`; `1 1/2-2 cups` ×0.5 → `3/4-1 cups`. |
| [blocker] ranges | Both ends are scaled and the separator is kept as written: `-`, `–`, `—`, `to`, `or`. `2 - 3 eggs` ×2 → `4 - 6 eggs`. |
| [major] Unicode fractions | `¼ ½ ¾ ⅓ ⅔ ⅛ …` mapped to exact values, alone, after a whole number (`1½`) and with the fraction slash (`1⁄2`). `½ cup sugar` ×2 → `1 cup sugar`. |
| [minor] unreadable output | Factor limited to 0.01–100 (cap requested by me; the minimum is the generator's choice, so tiny factors don't print long zero runs). No scientific notation any more. |
| [minor] awkward fractions | Fractions only with denominators 2, 3, 4, 8, 16; anything else becomes a decimal. `2/3 cup` ×1/3 → `0.22 cup`. |
| [minor] repr() untested | New endpoint test with `factor=0.2` on a line where dropping `repr()` changes the result. |
| over-claiming comments | Both removed and replaced with comments that describe the actual behaviour. |

Still not handled, by the generator's own account (left unchanged, never mangled): leading-dot
decimals such as `.5 cup`, decimal commas, thousands separators. Known semantic limit it
reported itself: `2-inch piece ginger` becomes `4-inch piece ginger`, because the parser cannot
tell a size from a count.
