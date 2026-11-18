# Part II: the generator's brief (round 1)

Sent at 2026-11-18 10:44 (+03). The generator worked in `../recipe-task-c` on branch
`task-c`, created from `main` after Part I was merged.

> You are the GENERATOR in a generator–critic loop. You write the solution; a separate critic
> agent (who did not write it) will review your work against a rubric, and you will then
> revise based on its review. Expect several rounds.
>
> YOUR TASK (Task 3, Ingredient scaling): `GET /recipes/{id}/scaled?factor=2` returns the
> recipe with ingredient quantities scaled by the factor (assume ingredients like
> "200 g flour").
>
> EDIT BOUNDARY: in main.py, add the new endpoint and any small helper functions it needs; do
> not change existing endpoints, the schema, or other helpers. Tests go in a new
> `test_scaling.py`. Tests share a real SQLite file, so never assume the database is empty.
>
> Read main.py, the existing tests, docs/TASKS.md and docs/RUBRIC.md first. The critic will
> use docs/RUBRIC.md. Implement, run the full suite until it passes, commit as
> "Scaling round 1: add GET /recipes/{id}/scaled". Do not merge, rebase, push or touch other
> directories.

The generator kept the same session for every round, so it remembered its own earlier work.
Each critic was a new session.
