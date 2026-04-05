# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A comprehensive multi-user Project Management application: JWT authentication, multiple Kanban boards per user, full card metadata, checklists, comments, board sharing, activity log, AI chat integration, and export.

## Architecture

- **Backend**: Python FastAPI (`backend/`) — serves the REST API at `/api/*` and the Next.js static export at `/`
- **Frontend**: Next.js 16 App Router (`frontend/`) — static export (`output: 'export'`), served by FastAPI from `frontend/out/`
- **Auth**: JWT tokens via `python-jose`, bcrypt password hashing. `backend/auth.py` contains `get_current_user` FastAPI dependency.
- **Database**: SQLite at `data/pm.db`, initialized on startup with idempotent `_migrate()`. Schema: `users`, `boards`, `board_members`, `columns`, `cards`, `card_comments`, `checklist_items`, `board_activity` with cascade deletes.
- **AI**: OpenRouter API via `backend/ai.py`, model `openai/gpt-oss-120b`, using structured JSON output (`KanbanResponse` Pydantic model)
- **Drag-and-drop**: `@dnd-kit/core` + `@dnd-kit/sortable` (cards vertical, columns horizontal)

## API Routes

### Auth
- `POST /api/auth/register` — register new user (creates default board)
- `POST /api/auth/login` — returns JWT token
- `GET /api/auth/me` — current user profile
- `PUT /api/auth/password` — change password

### Boards
- `GET /api/boards` — list user's boards (owner + shared)
- `POST /api/boards` — create board
- `GET /api/boards/{id}` — full board data (columns + cards with assignee, checklist counts)
- `PUT /api/boards/{id}` — rename board (owner only)
- `DELETE /api/boards/{id}` — delete board (owner only, cascades)
- `GET /api/boards/{id}/activity?limit=50` — audit log (recent 50 events)

### Columns
- `POST /api/columns` — create column `{title, board_id, wip_limit?}`
- `PUT /api/columns/{id}` — rename + set wip_limit
- `DELETE /api/columns/{id}` — delete column (cascades cards)
- `POST /api/columns/reorder` — persist new column order `{column_ids: [...]}`

### Cards
- `POST /api/cards` — create card `{title, column_id, priority?, due_date?, labels?, assignee_id?}`
- `PUT /api/cards/{id}` — update card (move + metadata + assignee)
- `DELETE /api/cards/{id}` — delete card

### Comments
- `GET /api/cards/{id}/comments` — list comments
- `POST /api/cards/{id}/comments` — post comment `{content}`
- `DELETE /api/cards/{id}/comments/{comment_id}` — delete own comment

### Checklist
- `GET /api/cards/{id}/checklist` — list items
- `POST /api/cards/{id}/checklist` — add item `{title}`
- `PUT /api/cards/{id}/checklist/{item_id}` — update `{title?, checked?}`
- `DELETE /api/cards/{id}/checklist/{item_id}` — delete item

### Sharing
- `GET /api/boards/{id}/members` — list board members
- `POST /api/boards/{id}/members` — invite by username `{username}`
- `DELETE /api/boards/{id}/members/{user_id}` — remove member (owner only)

### Export
- `GET /api/boards/{id}/export?format=json|csv` — download board data

### AI
- `POST /api/ai/chat/{board_id}` — AI chat for a specific board

## Frontend Routes
- `/` — redirects to `/boards` or `/login`
- `/login` — login + register (same page, toggle)
- `/boards` — board dashboard (list, create, rename, delete)
- `/board?id=<boardId>` — single board Kanban view
- `/profile` — user profile + change password

## Key Files

### Backend
- `backend/auth.py` — JWT utilities, `hash_password`, `verify_password`, `get_current_user`
- `backend/main.py` — FastAPI app + all router registrations
- `backend/ai.py` — OpenRouter integration, `KanbanResponse` schema
- `backend/database.py` — SQLite init + `_migrate()` (idempotent ALTER TABLE) + seed data
- `backend/models.py` — all Pydantic models
- `backend/routers/auth.py` — auth endpoints
- `backend/routers/boards.py` — board CRUD + activity endpoint
- `backend/routers/columns.py` — column CRUD + reorder
- `backend/routers/cards.py` — card CRUD (logs activity)
- `backend/routers/comments.py` — comment CRUD
- `backend/routers/checklist.py` — checklist CRUD
- `backend/routers/sharing.py` — board member management
- `backend/routers/export.py` — CSV/JSON export
- `backend/routers/ai_chat.py` — AI chat handler

### Frontend
- `frontend/src/lib/api.ts` — typed API client with JWT injection; all API functions
- `frontend/src/lib/kanban.ts` — `BoardData`, `Card`, `Column` types + `moveCard()` logic
- `frontend/src/components/KanbanBoard.tsx` — board view: stats panel, header buttons, DnD, activity feed, dark mode, shortcuts
- `frontend/src/components/KanbanCard.tsx` — card face (assignee, checklist progress, priority, due date, labels) + edit modal with Details/Checklist/Comments tabs
- `frontend/src/components/KanbanColumn.tsx` — column with WIP limit display/editor, drag handle
- `frontend/src/components/KanbanCardPreview.tsx` — drag overlay card
- `frontend/src/components/AIChatSidebar.tsx` — AI chat (accepts `boardId` prop)
- `frontend/src/components/FilterBar.tsx` — text search + priority + label filters
- `frontend/src/components/ShareDialog.tsx` — invite user + list/remove members
- `frontend/src/components/NewCardForm.tsx` — inline add-card form

## Card Fields
- `title`, `details`, `order`, `column_id`
- `priority`: `"low" | "medium" | "high"` (default: `"medium"`)
- `due_date`: ISO date string or null — overdue = red, due ≤3 days = amber
- `labels`: comma-separated string (e.g. `"frontend,urgent"`)
- `assignee_id` / `assignee_username`: optional user assignment
- `checklist_total` / `checklist_done`: read-only counts from subqueries

## Column Fields
- `title`, `order`, `wip_limit` (optional int — exceeded = red ring on column)

## Access Control
- Board owner can do everything
- Board members (via `board_members` table) can read board + write cards/columns/checklist/comments
- Only owner can rename/delete the board, manage sharing, set WIP limits

## Development Commands

### Run with Docker (primary)
```bash
./scripts/start.sh       # Mac/Linux
scripts\start.bat        # Windows
# App available at http://localhost:8000
./scripts/stop.sh        # Mac/Linux
scripts\stop.bat         # Windows
```

### Frontend dev (standalone)
```bash
cd frontend
npm install
npm run dev              # dev server at http://localhost:3000
npm run build            # static export to frontend/out/
npm run lint
npm run test             # vitest unit tests (24 tests)
npm run test:e2e         # playwright e2e tests
npm run test:all         # unit + e2e
```

### Backend dev (without Docker)
```bash
cd C:/Users/NUC/Documents/AI_projects/pm
uv pip install -r backend/requirements.txt
uv run uvicorn backend.main:app --reload --port 8000
```

### Run backend tests
```bash
python -m pytest backend/tests/ -v    # all 82 integration tests
python -m pytest backend/tests/test_auth.py    # auth tests only
```

## Environment

Requires a `.env` file in the project root:
```
OPENROUTER_API_KEY=your_key_here
```

## Color Scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`

## Coding Standards

- Latest library versions, idiomatic approaches
- Keep it simple — no over-engineering, no unnecessary defensive programming, no extra features
- No emojis anywhere in code or UI
- When debugging: identify root cause with evidence before fixing
- bcrypt used directly (not passlib) — Python 3.13 compatibility
- Static export constraint: use query params (`/board?id=...`) not dynamic routes for board detail
