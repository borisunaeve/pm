# Code Review Notes

Last reviewed: 2026-04-05

## Overall Assessment

The codebase is in good shape. 82 backend integration tests + 24 frontend unit tests all pass. Build is clean. No known critical security issues.

---

## Backend

### Strengths
- All routes protected with `get_current_user` — no unauthenticated data leakage
- Access control consistently enforced at two levels: owner and member (via `board_members`)
- `_migrate()` in `database.py` uses idempotent `ALTER TABLE` pattern — safe to run against an existing production DB
- `bcrypt` used directly (not via passlib) — correct fix for Python 3.13 incompatibility
- Activity logging is transparent to the caller — `_log_activity()` called inside mutation endpoints

### Issues / Risks

**Medium: Column delete/rename allowed for board members**
`_assert_column_access` in `columns.py` allows any board member to delete or rename columns. Destructive column operations should be owner-only (consistent with `_assert_owner` used in boards).

**Low: No rate limiting on auth endpoints**
`/api/auth/login` and `/api/auth/register` have no rate limit. Brute-force or spam-register is possible. Mitigate with `slowapi` middleware or failed-attempt tracking.

**Low: `board_activity` table grows indefinitely**
Append-only with no cleanup. Consider keeping last N rows per board, or adding a background trim job.

**Low: `assignee_id` not validated against board membership**
Cards can be assigned to any user ID without checking the assignee is actually a board member. Add the check in `update_card` and `create_card`.

**Low: Export duplicates the access-check SQL**
`export.py` copy-pastes the `_assert_access` query instead of importing the shared helper from `boards.py`.

---

## Frontend

### Strengths
- All API calls go through the central `apiFetch()` in `api.ts` — JWT injection and 401/403 handling in one place
- `useDarkMode` hook correctly syncs `<html class="dark">` with localStorage
- `dueDateStatus()` is pure and fully tested
- `KanbanCard` edit modal uses tabs (Details / Checklist / Comments) — good separation
- `reorderColumns` calls the backend API — column order is now persistent
- `StatsPanel` + activity feed + share dialog all implemented as self-contained components

### Issues / Risks

**Medium: Column reorder has no rollback on failure**
If `api.reorderColumns()` fails, `fetchBoard()` re-fetches to revert state — but there is a brief window showing the wrong order. Better to revert local state immediately on error, then re-fetch.

**Low: `StatsPanel` "Done" count is heuristic**
Done count checks `col.title.toLowerCase().includes("done")`. A column named "Not Done" would be counted incorrectly. A proper `is_done` boolean flag on columns would be deterministic.

**Low: Dark mode uses `!important` overrides**
`.dark` CSS overrides use `!important` on Tailwind utility classes. Works today but fragile against Tailwind renames. A full CSS variable re-theme in `:root` / `.dark` blocks would be cleaner.

**Low: Activity feed does not auto-refresh**
`ActivityFeed` fetches once on open. Actions by other users won't appear until the panel is closed and reopened. Add polling or WebSocket in a future iteration.

**Low: `ShareDialog` re-fetches all members after each invite**
Calls `api.listMembers()` after each successful add rather than appending the new member to local state — unnecessary round-trip.

---

## Testing Coverage

| Area | Tests | Notes |
|------|-------|-------|
| Backend auth | 14 | register, login, change-password, unauthorized |
| Backend boards | 12 | CRUD + sharing access |
| Backend cards | 10 | CRUD + move |
| Backend columns | 8 | CRUD + reorder |
| Backend comments | 7 | CRUD + auth |
| Backend checklist | 8 | CRUD + board count |
| Backend sharing | 6 | invite, remove, access control |
| Backend export | 5 | JSON, CSV, auth |
| Backend assignments | 3 | create, update, board return |
| Backend activity | 6 | log on create/delete, limit param |
| Frontend unit | 24 | KanbanBoard, KanbanCard, api, kanban lib |
| Playwright e2e | 37 | login, boards, kanban, features |
| ShareDialog unit | **Missing** | no component-level unit test |
| Checklist progress bar | **Missing** | no unit test for render |

---

## Recommendations (Priority Order)

1. Restrict column delete/rename to board owner only
2. Validate `assignee_id` against board membership on card write
3. Deduplicate `_assert_access` — import from `boards.py` into `export.py`
4. Add rate limiting on `/api/auth/login` and `/api/auth/register`
5. Unit test `ShareDialog` component
6. Add `is_done` boolean flag to columns for accurate stats
7. Auto-refresh activity feed with polling interval
