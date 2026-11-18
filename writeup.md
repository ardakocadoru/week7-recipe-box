# Week 7 Write-up: Agent Orchestration (Recipe Box Sprint)

| Part | Task | Branch | Result |
|---|---|---|---|
| I | 2. Tag filter, built by Agent A | `task-a` | merged |
| I | 4. Favorites, built by Agent B, at the same time | `task-b` | merged |
| II | 3. Ingredient scaling, generator–critic loop | `task-c` | accepted in round 4, merged |

The final suite has **185 passing tests** (3 from the starter). The commit history on `main`
keeps every branch and merge, and every critic round is a separate commit.

The agents were coding-agent sessions that I started and supervised from one orchestrating
session. Each one got a written brief, worked only in its own worktree, and reported back to
me. I did the merging, made the scope decisions and checked every finding myself before
acting on it.

## Part I: Concurrent agents

### Which two tasks, and why

All four tasks in `docs/TASKS.md` are independent features, but they are not equally
independent in the code. I picked **tag filter** and **favorites** because they touch the same
area: the tag filter changes `list_recipes`, and favorites changes the schema and
`_row_to_recipe`, which `list_recipes` uses to build every response. Picking two tasks that
never meet (such as the shopping list and the tag filter) would have avoided the interesting
part of running agents in parallel.

### Worktree setup

```bash
git worktree add ../recipe-task-a -b task-a   # Agent A: tag filter
git worktree add ../recipe-task-b -b task-b   # Agent B: favorites
```

I launched both agents in the same step, right after creating the worktrees. Their own start
and end times, and their commit times, show that they ran at the same time:

| | Started | Committed | Commit |
|---|---|---|---|
| Agent A (tag filter) | 10:42:22 | 10:42:53 | `9838136` |
| Agent B (favorites) | 10:42:23 | 10:43:07 | `c7b1466` |

### How I kept them from colliding

Before starting them I wrote down an edit boundary for each agent
([`agent-logs/part1-boundaries.md`](agent-logs/part1-boundaries.md)):

- **Function-level ownership of `main.py`.** Agent A could change only `list_recipes`. Agent B
  could change the schema, `init_db`, `_row_to_recipe` and the `create_recipe` response, and
  had to append its new route at the end of the file. Neither was allowed to touch the other's
  functions.
- **Separate test files** (`test_tag_filter.py`, `test_favorites.py`) so they could not both
  edit `test_main.py`.
- **No shared state at run time.** `DB_PATH` is relative to the code, so each worktree had its
  own `recipes.db`.
- **One merger.** The agents could commit only on their own branch. Merging was my job.

### Collisions and risks

**The merge was clean, and the merged code was still broken.** Both branches merged with no
textual conflict, because the agents had stayed inside their boundaries. Running the full
suite on `main` then failed: Agent A had written a test comparing the whole recipe dictionary,
and Agent B's new `favorite` field made it fail. Agent A had predicted exactly this in its
report ("that test would need updating after the merge"). I updated the expected shape and
added a test that uses both features together: a favorited recipe has to come back with
`favorite: true` through the tag filter (`d374338`). A conflict-free merge only shows that
the text fits together. Only the tests show the behaviour does.

Other risks I planned for in the briefs:

- **Tests share one real SQLite file.** Both agents had to create their own recipes and assert
  on those ids or on unique tags, never on counts. Without that rule, each agent's tests would
  have passed alone and failed once both sets ran against the same file.
- **Existing databases.** `CREATE TABLE IF NOT EXISTS` does not add a column to a table that
  already exists. With an old `recipes.db`, every read would have crashed on the missing
  `favorite` key, and the toggle would have failed with "no such column: favorite" (I checked
  both against an old-schema file). Agent B upgrades the table in place on startup and has a
  test that builds an old-schema file and checks its rows survive.
- **Two quick toggles.** The favorite toggle is one `UPDATE … SET favorite = 1 - favorite`,
  so two requests cannot both read the same old value.

## Part II: Generator–critic loop

### Setup

- **Rubric:** [`docs/RUBRIC.md`](docs/RUBRIC.md), written before the loop started. It turns
  the brief's three areas (correctness, tests, clarity) into concrete checks with severities.
  The sign-off rule is that the critic accepts only when no blocker and no major remains.
- **Generator:** one session for the whole loop, so it remembered its own earlier choices
  ([brief](agent-logs/part2-generator-prompt.md)).
- **Critic:** a **new session in every round**, read-only (it could run tests and probes but
  could not edit or commit), told that it had not written the code and should assume it had
  bugs ([brief](agent-logs/part2-critic-prompt.md)). Week 6 showed that a reviewer who wrote
  the code mostly agrees with itself, so the critic never saw the code being written.
- **Me:** I passed each critique to the generator, reproduced the main findings before doing
  so, and decided scope whenever a finding could be fixed in more than one way.

### The rounds

| Round | Generator commit | Tests | Critic verdict | Findings |
|---|---|---|---|---|
| 1 | `d54c65c` first version | 58 | **REVISE** | 2 blockers, 1 major, 3 minor |
| 2 | `047275e` revision 1 | 102 | **REVISE** | 1 new blocker, 3 major, 2 minor |
| 3 | `2947078` revision 2 | 146 | **REVISE** | 2 major, 1 minor |
| 4 | `fef9174` revision 3 | 185 | **ACCEPT** | 1 minor, documented |

Three revision rounds before sign-off. The full critiques are in [`reviews/`](reviews/), and
the generator's report for each round is in [`agent-logs/`](agent-logs/).

### Transcript, condensed

**Round 1.** The generator handled integers, decimals, fractions and mixed numbers with exact
`Fraction` arithmetic, rejected bad factors with 422, and wrote 41 tests. All 58 tests passed.
The critic still found that numbers the parser only partly read were scaled to wrong values:
`1½ cups flour` ×2 became `2½ cups`, and `1,5 dl milk` ×0.5 became `0.5,5 dl`. It also found
that ranges written with spaces or "to" scaled only their first number (`2 to 3 eggs` →
`4 to 3 eggs`), and that `½ cup sugar` was not scaled at all. I reproduced these myself and
sent them back. On scope, I asked for decimal commas to be left unchanged rather than guessed,
and for the factor to be capped.

**Round 2.** The generator rewrote the parser, and every round-1 finding was confirmed fixed.
But the new range rule introduced a regression: `1-1/2 cups flour`, a common US way to write
1½, was now read as the range "1 to 1/2" and ×2 became `2-1 cups`. The critic also found that
`.5 cup` was never scaled, and that lines with a second quantity contradicted themselves
(`200 g (7 oz) butter` ×2 → `400 g (7 oz)`). I made the scope calls: second amounts with a
unit get scaled, an item size like `9-inch` is not scaled but the count before it is, and
pluralising units ("2 cup") is out of scope.

**Round 3.** All round-2 findings were confirmed fixed. The critic now found pack sizes
(`1 8-oz package cream cheese` was left unscaled, so a doubled cheesecake gets half the cream
cheese) and units written with a period (`12 oz. (340 g)` → `24 oz. (340 g)`). At this point
the pattern was clear: each round fixed the spellings the critic listed, and the next critic
found new ones. Instead of sending another list, I asked the generator for **general rules**:
an optional period after every unit, one rule for any count followed by a sized amount, and a
safety rule. If a second amount cannot be fully read, the line is returned unchanged, because
a half-scaled line that contradicts itself is worse than an unscaled one.

**Round 4.** The critic confirmed every earlier finding fixed, re-ran the inputs from all
rounds without finding a regression, and tried about 60 further real-world lines. It found one
rare spelling (`1 cup / about 240 ml`) that does not block. **ACCEPT.**

### What the loop caught that tests did not

All tests passed in every round. Each REVISE was about behaviour that no test covered yet,
and every finding became a new test with the critic's exact input. That is why the suite grew
from 58 to 185 tests. The regression in round 2 is the clearest case: the fix for one finding
broke a different input, and only a fresh reviewer, checking the change from the outside,
noticed.

### Known limitations (accepted on purpose)

- Units are not pluralised: `1 cup` ×2 → `2 cup`.
- `2-inch piece ginger` is not scaled, because a leading length is treated as an item size.
- Decimal commas, thousands separators and second amounts that cannot be fully read are
  returned unchanged rather than guessed.
- `1 cup / about 240 ml` and `1 cup or 240 ml` scale only the first amount (the critic's last
  minor).

## Autonomy and supervision

| Agent | Allowed | Not allowed | How I supervised |
|---|---|---|---|
| Agent A, Agent B | Edit inside its own worktree, within its function boundary; run tests; commit on its own branch | Merge, rebase, push, change git config, touch the other worktree or shared files | Written boundary before starting; read each report and diff; ran the full suite after each merge |
| Generator | Edit `main.py` (new endpoint and helpers only) and its own test file; commit on `task-c` | Change existing endpoints, other tests, `reviews/`; merge | Forwarded each critique with explicit scope decisions; checked the commit and test count each round |
| Critic | Read files, run tests and throwaway probes | Edit, create or delete files; commit; change branches | New session each round; I reproduced findings before passing them on and committed its review unedited |

Autonomy went down as the risk went up, as in the Week 2 lecture: the agents could do anything
inside their sandbox, only I could merge into `main`, and the critic could only read.

## What I learned

Running agents in parallel is mostly a planning problem. The time I spent splitting `main.py`
by function before starting is the reason both branches merged without a conflict, but a
clean merge still hid a broken test, so running the full suite after every merge is not
optional. The generator–critic loop worked because the critic was a separate, read-only
session that did not trust the code. A strict rubric was not enough to make the loop end,
though: on open-ended input like recipe text, a fresh critic always finds one more spelling,
and the loop only converged once I changed the instruction from "fix these cases" to "make the
rule general, and leave a line unchanged when you cannot read it safely". The most valuable
part of my role was not writing code but deciding scope and checking that each finding was
real before passing it on.
