# Starter — Recipe Box

A tiny FastAPI + SQLite service with a static frontend. Your playground for concurrent
agents and a generator–critic loop.

## Setup
```bash
pip install -r requirements.txt
pytest                      # 3 tests should pass
uvicorn main:app --reload   # http://localhost:8000  (UI at /, docs at /docs)
```

## Endpoints
- `POST /recipes` `{ "title": ..., "ingredients": [...], "tags": [...] }`
- `GET /recipes`, `GET /recipes/{id}`
- `GET /recipes?tag=breakfast`: only recipes with that tag (case-insensitive)
- `POST /recipes/{id}/favorite`: toggle the `favorite` flag
- `GET /recipes/{id}/scaled?factor=2`: ingredient quantities scaled (factor 0.01–100)

See [`writeup.md`](writeup.md) for how these were built with concurrent agents and a
generator–critic loop.

## Parallel work with git worktrees
```bash
git worktree add ../recipe-task-a -b task-a
git worktree add ../recipe-task-b -b task-b
```

## Files
- `main.py` — the app
- `static/index.html` — minimal UI
- `test_main.py` — pytest suite
- `docs/TASKS.md` — independent tasks (safe to run in parallel)
