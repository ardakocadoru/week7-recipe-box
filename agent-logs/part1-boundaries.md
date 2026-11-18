# Part I: the brief each agent received

Both agents were started at 2026-11-18 10:41:50 (+03), each in its own git worktree, and ran
at the same time. They could edit files and run tests inside their own worktree and commit
on their own branch. They could not merge, rebase, push, change git config, or touch the
other worktree. Merging was my job.

| | Agent A | Agent B |
|---|---|---|
| Task | 2. Tag filter: `GET /recipes?tag=breakfast` | 4. Favorites: `favorite` flag + `POST /recipes/{id}/favorite` toggle |
| Worktree / branch | `../recipe-task-a` / `task-a` | `../recipe-task-b` / `task-b` |
| May change in `main.py` | only `list_recipes` | schema and `init_db`, `_row_to_recipe`, `create_recipe` response, new route appended at the end of the file |
| Must not touch | schema, `_row_to_recipe`, `create_recipe`, `get_recipe` | `list_recipes`, `get_recipe`, `RecipeIn` |
| Tests | new file `test_tag_filter.py` | new file `test_favorites.py` |
| Off limits for both | `test_main.py`, `static/`, `README.md`, `docs/`, `requirements.txt` | same |

Extra requirements I gave on purpose:

- **Both:** the test suite shares one real SQLite file, so tests must never assume an empty
  database. Each test creates its own recipes and asserts on their ids or unique tags.
- **Agent A:** match tags case-insensitively and ignore surrounding whitespace in the query;
  an empty `?tag=` means no filter; an unknown tag returns `[]` with 200; do not change how
  tags are stored.
- **Agent B:** an existing `recipes.db` from the old schema must be upgraded in place on
  startup (add the column only if missing, keep every row), with a test that proves it. The
  toggle must be one SQL statement (`SET favorite = 1 - favorite`) so two quick toggles
  cannot read the same old value.
