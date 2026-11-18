# Agent B report (Task 4, favorites, branch `task-b`)

Final report from the agent, unedited apart from shortened file paths.

- START: 2026-11-18 10:42:23 +03 · END: 2026-11-18 10:43:07 +03
- Commit: `c7b1466` "Add favorite flag and toggle endpoint"

**Files changed:** `main.py`, `test_favorites.py` (new).

**Design**
- The new `favorite INTEGER NOT NULL DEFAULT 0` column is in the CREATE TABLE statement.
  `_row_to_recipe` returns `"favorite": bool(row["favorite"])`, so GET /recipes and
  GET /recipes/{id} include the field without touching those two functions. `create_recipe`
  adds `"favorite": False` to its response.
- `RecipeIn` is unchanged. A client that sends `favorite: true` on create is ignored, and a
  test checks this.
- `POST /recipes/{id}/favorite` sits at the end of the file. It runs one statement,
  `UPDATE recipes SET favorite = 1 - favorite WHERE id = ? RETURNING *`, which toggles and
  returns the new row together, so two quick toggles can't read the same old value.
  (SQLite here is 3.43.1; `RETURNING` needs 3.35 or later.) No row → 404 "unknown recipe".

**In-place upgrade:** on startup `init_db` reads `PRAGMA table_info(recipes)` and only if
`favorite` is missing runs `ALTER TABLE recipes ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0`.
Existing rows get 0, and running it again does nothing.

**How the tests prove it:** `test_old_schema_database_is_upgraded_in_place` builds an
old-schema file in `tmp_path` with two rows, points `main.DB_PATH` at it and calls `init_db()`
twice, then checks the column exists exactly once and the rows survive as
`[(1,'Old Soup',0),(2,'Old Bread',0)]`, and that the API lists both with `favorite: false` and
toggles row 2 to true. Before the first test run the agent also created an old-schema
`recipes.db` in its worktree with one row ("Legacy Omelette"); importing the app upgraded it in
place and the row became `(1, 'Legacy Omelette', 0)`.

Other tests: default false on create/get/list; client-supplied flag ignored; toggling twice
goes true then false and persists; a toggle only affects its target; unknown id → 404.

**Final `pytest -q`:** 9 passed, 1 warning (existing Starlette/httpx deprecation).

**Possible collisions (agent's own words)**
- "`_row_to_recipe` is shared. If their `list_recipes` change builds dicts some other way
  (custom SELECT columns), their responses may lack `favorite`. Whoever merges second should
  check that `list_recipes` still uses `SELECT *` and `_row_to_recipe`."
- "My endpoint is appended at the end of the file. If they also append an endpoint there,
  git will report a trivial conflict at end of file."
- "Their tests in test_main.py assert on titles and tags only, so the extra `favorite` key
  shouldn't break them."
