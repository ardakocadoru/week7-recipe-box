# Critic rubric (Part II, Task 3: ingredient scaling)

The critic reviews the generator's diff and gives one verdict: **ACCEPT** or **REVISE**.
It reviews from a fresh session, without having written the code, and it starts from the
assumption that the change has bugs.

A change is accepted only when all three areas pass. Every finding needs a reproducible
example (a request, an input string, or a failing test) and a severity:
**blocker** (wrong result, crash, or missing required behaviour), **major** (likely to bite a
real user or untested behaviour), **minor** (clarity or style).

## 1. Correctness

- `GET /recipes/{id}/scaled?factor=N` returns the recipe with every quantity multiplied by N.
- The stored recipe is not changed; `GET /recipes/{id}` still returns the original.
- An unknown id returns 404. A factor that is zero, negative, or not a number is rejected
  with a 4xx status, never a 500.
- Quantities the app should understand: integers (`200 g flour`), decimals (`1.5 cups milk`),
  fractions (`1/2 tsp salt`) and mixed numbers (`1 1/2 cups sugar`).
- Ingredients with no leading quantity (`salt to taste`, `a pinch of nutmeg`) come back
  unchanged instead of being mangled or causing an error.
- Results are readable: no `400.0 g`, no `0.30000000000000004 cups`.

## 2. Tests

- Every behaviour above has a test that would fail if the behaviour broke.
- Tests assert on the scaled values, not only on the status code.
- Tests do not assume an empty database.

## 3. Clarity

- The parsing and formatting logic is small, named, and readable on its own.
- No dead code, debug output, or unrelated changes outside the task.

**Sign-off rule:** ACCEPT only if there are no blockers and no majors left.
