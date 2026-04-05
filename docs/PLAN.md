# Project Management App — Build Plan

## Status: All phases complete

---

## Phase 1: Scaffolding
- [x] Python FastAPI backend with `uv` package management
- [x] Docker + `docker-compose.yml`, start/stop scripts (Windows + Mac/Linux)
- [x] FastAPI serves Next.js static export at `/`

## Phase 2: Frontend
- [x] Next.js 16 App Router with `output: 'export'`
- [x] Kanban board with drag-and-drop (`@dnd-kit`)
- [x] Static export served by FastAPI from `frontend/out/`

## Phase 3: Authentication
- [x] JWT auth via `python-jose` + `bcrypt` (direct, not passlib — Python 3.13 compatible)
- [x] `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `PUT /api/auth/password`
- [x] Frontend login/register page, token stored in localStorage, injected on all API calls
- [x] Auth guard: unauthenticated users redirected to `/login`

## Phase 4: Multi-Board Support
- [x] `boards` table with per-user ownership
- [x] Full board CRUD: list, create, rename, delete
- [x] `/boards` dashboard page
- [x] `/board?id=...` per-board Kanban view (query param, not dynamic route — static export constraint)
- [x] Default board created on register

## Phase 5: Card Metadata
- [x] `priority` field: `low | medium | high` with color badges
- [x] `due_date` with overdue (red) / due-soon ≤3 days (amber) highlighting
- [x] `labels` (comma-separated) with purple chips
- [x] `CardEditModal` for editing all fields

## Phase 6: Column Enhancements
- [x] WIP limits: `wip_limit` on columns, red ring when exceeded, inline editor
- [x] Column drag-to-reorder (horizontal DnD) with server persistence via `POST /api/columns/reorder`
- [x] Delete column with confirmation

## Phase 7: Filter & Search
- [x] `FilterBar` component: text search, priority filter, label filter
- [x] `visibleCardIds` memo filters cards client-side

## Phase 8: Board Sharing
- [x] `board_members` junction table (board_id, user_id, role)
- [x] Owner can invite by username, remove members
- [x] Members can read board + write cards/columns/checklist/comments
- [x] `ShareDialog` component in board header

## Phase 9: Card Comments
- [x] `card_comments` table
- [x] Full comment CRUD via `/api/cards/{id}/comments`
- [x] Comments tab in `CardEditModal`

## Phase 10: Card Checklists
- [x] `checklist_items` table with checked/order fields
- [x] Full checklist CRUD via `/api/cards/{id}/checklist`
- [x] Checklist tab in `CardEditModal` with progress bar
- [x] Progress bar shown on card face (`checklist_total` / `checklist_done`)

## Phase 11: Export
- [x] `GET /api/boards/{id}/export?format=json|csv`
- [x] Export dropdown in board header triggers browser download

## Phase 12: Card Assignments
- [x] `assignee_id` on cards (FK to users)
- [x] Assignment picker in `CardEditModal` (populated from board members)
- [x] Assignee avatar + username shown on card face

## Phase 13: Activity Log
- [x] `board_activity` table (board_id, user_id, action, entity_type, entity_title)
- [x] Card create/update/delete events logged automatically
- [x] `GET /api/boards/{id}/activity` endpoint
- [x] `ActivityFeed` floating panel in board UI

## Phase 14: UI/UX Polish
- [x] Stats panel (total cards, high priority, overdue, done, columns)
- [x] Dark mode toggle with CSS variables + localStorage persistence
- [x] Keyboard shortcuts: `/` focus search, `?` toggle help, `Esc` close modals
- [x] AI chat sidebar with board-scoped context

## Phase 15: Testing
- [x] **82 backend integration tests** across 5 test files
  - `test_auth.py` (14), `test_boards.py` (12), `test_cards.py` (10), `test_columns.py` (8)
  - `test_comments_checklist_sharing_export.py` (25), `test_assignments_activity_reorder.py` (13)
- [x] **24 frontend unit tests** (Vitest + React Testing Library)
  - `kanban.test.ts` (3), `api.test.ts` (5), `KanbanCard.test.tsx` (6), `KanbanBoard.test.tsx` (10)
- [x] **Playwright e2e tests** across 3 spec files
  - `login.spec.ts`, `kanban.spec.ts`, `features.spec.ts` (27 tests covering all major features)

---

## DB Schema Summary

```
users          id, username, password_hash, created_at
boards         id, user_id, title, created_at
board_members  board_id, user_id, role, added_at
columns        id, board_id, title, order, wip_limit
cards          id, column_id, title, details, order, priority, due_date, labels, assignee_id
card_comments  id, card_id, user_id, content, created_at
checklist_items id, card_id, title, checked, order
board_activity id, board_id, user_id, action, entity_type, entity_title, created_at
```

All tables use cascade deletes. Schema migrations are idempotent via `_migrate()` in `database.py`.
