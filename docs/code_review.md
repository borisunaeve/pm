# Code Review

Date: 2026-04-04

## Summary

The codebase is clean and well-structured for an MVP. The architecture is sound, the component decomposition is sensible, and the AI integration works correctly. The items below are grouped by severity.

---

## Bugs

### 1. Column rename fires an API call on every keystroke
**File:** `frontend/src/components/KanbanBoard.tsx:92-105`, `frontend/src/components/KanbanColumn.tsx:43`

`handleRenameColumn` is wired directly to `onChange` on the column title input. Every character typed triggers a `PUT /api/columns/:id` network request. This causes unnecessary load and risks race conditions where slow responses overwrite a later, correct title.

**Fix:** Debounce the API call, or switch to `onBlur` so the save only fires when the user leaves the field.

---

### 2. Board never shows an error if the initial fetch fails
**File:** `frontend/src/components/KanbanBoard.tsx:29-43`

If `GET /api/board` fails (network error, server down), `board` stays `null` and the UI shows "Loading Kanban Board..." indefinitely. The user has no indication that something went wrong.

**Fix:** Add an `error` state. Show a message and a retry button if the fetch fails.

---

### 3. AI sidebar board-refresh condition is logically wrong (accidentally works)
**File:** `frontend/src/components/AIChatSidebar.tsx:64`

```ts
if (data.action && data.action.action !== "NONE") {
    onRefreshBoard();
}
```

`data.action` is the full `KanbanResponse` object `{ response_message, actions }`. It has no `.action` property, so `data.action.action` is always `undefined`. `undefined !== "NONE"` is always `true`, so `onRefreshBoard()` is called on every AI response — including pure conversational replies with no board changes. The board refreshes unnecessarily but never fails to refresh after a real action, so the bug is invisible in practice.

**Fix:** Check whether any actions were returned:
```ts
if (data.action?.actions?.length > 0) {
    onRefreshBoard();
}
```

---

## Code Quality

### 4. Duplicate import and scattered imports in `main.py`
**File:** `backend/main.py:52,127`

`from backend.models import CreateCardRequest, UpdateCardRequest` appears twice. More broadly, imports are scattered throughout the file — each new section of routes adds its own imports inline. All imports should be consolidated at the top of the file.

---

### 5. `UpdateCardRequest` uses bare `str = None` instead of `Optional[str]`
**File:** `backend/models.py:22-23`

```python
title: str = None
details: str = None
```

Pydantic v2 accepts this but the type annotations are incorrect — `str` should be `Optional[str]`. This causes static analysis tools to flag type errors.

**Fix:**
```python
title: Optional[str] = None
details: Optional[str] = None
```

---

### 6. Magic string `'board-1'` repeated across `main.py`
**File:** `backend/main.py:23,137`

`'board-1'` is hardcoded in at least two separate queries. If the board ID ever changes or a constant is needed for tests, all occurrences need updating manually.

**Fix:** Define `BOARD_ID = "board-1"` at the top of `main.py` and reference it.

---

### 7. `/api/ai/chat` returns HTTP 200 on error
**File:** `backend/main.py:205-207`

```python
except Exception as e:
    return {"status": "error", "message": str(e)}
```

A 200 response with an error body is misleading. Clients (and monitoring) should see a 5xx status code on failure.

**Fix:** Raise an `HTTPException(status_code=500, detail=str(e))` instead.

---

### 8. AI model does not match the specification
**File:** `backend/ai.py:99`

```python
"model": "openai/gpt-4o-mini",  # Testing a faster / high reliability model
```

`AGENTS.md` specifies `openai/gpt-oss-120b`. The comment suggests this was a temporary testing change that was never reverted.

**Fix:** Change back to `openai/gpt-oss-120b`, or make the model name an environment variable so it can be overridden without a code change.

---

## Infrastructure & Configuration

### 9. `backend/` contains npm artefacts that should not exist
**Files:** `backend/package.json`, `backend/package-lock.json`, `backend/node_modules/`

These appear to be the result of accidentally running `npm install httpx python-dotenv` in the backend directory (`httpx` and `python-dotenv` are Python packages, not npm packages). None of these files belong in the Python backend.

**Fix:** Delete all three. Add `backend/node_modules/` to `.gitignore` as a safeguard.

---

### 10. `.gitignore` is missing several important entries
**File:** `.gitignore`

The following should be added:
- `data/` — prevents the SQLite database from being committed
- `frontend/out/` — prevents the Next.js build output from being committed
- `backend/node_modules/` — see item 9

---

### 11. `uvicorn[standard]` has no version pin in `requirements.txt`
**File:** `backend/requirements.txt`

All other packages have version pins. `uvicorn[standard]` does not, making builds non-reproducible. Relatedly, there is no `uv.lock` file committed, which means the exact resolved dependency tree is not in source control.

**Fix:** Pin `uvicorn[standard]` to a specific version. Consider committing `uv.lock`.

---

### 12. `docker-compose.yml` uses an obsolete `version` attribute
**File:** `docker-compose.yml:2`

`version: '3.8'` is deprecated in modern Compose and produces a warning on every command. Remove the line.

---

### 13. `docker-compose.yml` mixes dev and prod behaviour
**File:** `docker-compose.yml:16`

The compose override command runs uvicorn with `--reload`, but the `Dockerfile` CMD does not. The volume mount (`./backend:/app/backend`) also means the container image's backend code is bypassed at runtime — local source files are used instead. This is useful in development but means `docker-compose up` does not test the built image.

This is not necessarily wrong, but the distinction should be documented so it is not misunderstood.

---

### 14. `database.py` default DB path only works inside Docker
**File:** `backend/database.py:4`

```python
DB_FILE = os.environ.get("DB_FILE", "/app/data/pm.db")
```

Running the backend directly on the host (outside Docker) will attempt to create `/app/data/` which typically does not exist. The fallback path should work in both contexts.

**Fix:** Use a relative path as the default fallback, e.g. `os.path.join(os.path.dirname(__file__), "..", "data", "pm.db")`.

---

## Testing

### 15. `test_ai.py` is a script, not a pytest test
**File:** `backend/test_ai.py`

The file uses `asyncio.run(test())` under `if __name__ == "__main__"`. It will not be discovered or run by `pytest`. This is fine for a live integration smoke test, but it should be documented as such in `CLAUDE.md` and named accordingly (e.g. `smoke_test_ai.py`) to avoid confusion.

---

### 16. No e2e test coverage for login/logout or AI chat
**File:** `frontend/tests/kanban.spec.ts`

The e2e suite covers loading the board, adding a card, and dragging. The login flow (including invalid credentials) and the AI chat sidebar have no e2e coverage.
