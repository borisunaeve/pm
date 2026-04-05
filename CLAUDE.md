# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A comprehensive Project Management application: multi-user, multi-board Kanban with AI chat integration. Features real JWT authentication, user registration, multiple boards per user, column CRUD, and card metadata (priority, labels, due dates).

## Architecture

- **Backend**: Python FastAPI (`backend/`) — serves the REST API at `/api/*` and the Next.js static export at `/`
- **Frontend**: Next.js App Router (`frontend/`) — static export (`output: 'export'`), served by FastAPI from `frontend/out/`
- **Auth**: JWT tokens via `python-jose`, bcrypt password hashing. `backend/auth.py` contains `get_current_user` FastAPI dependency.
- **Database**: SQLite at `data/pm.db`, initialized on startup. Schema: `users`, `boards`, `columns`, `cards` with cascade deletes.
- **AI**: OpenRouter API via `backend/ai.py`, model `openai/gpt-oss-120b`, using structured JSON output (`KanbanResponse` Pydantic model)
- **Drag-and-drop**: `@dnd-kit/core` + `@dnd-kit/sortable`

### API Routes
- `POST /api/auth/register` — register new user (creates default board)
- `POST /api/auth/login` — returns JWT token
- `GET /api/auth/me` — current user profile
- `PUT /api/auth/password` — change password
- `GET /api/boards` — list user's boards (auth required)
- `POST /api/boards` — create board
- `GET /api/boards/{id}` — get full board data (columns + cards)
- `PUT /api/boards/{id}` — rename board
- `DELETE /api/boards/{id}` — delete board (cascades)
- `POST /api/columns` — create column `{title, board_id}`
- `PUT /api/columns/{id}` — rename column
- `DELETE /api/columns/{id}` — delete column (cascades cards)
- `POST /api/cards` — create card `{title, column_id, priority?, due_date?, labels?}`
- `PUT /api/cards/{id}` — update card (move + metadata)
- `DELETE /api/cards/{id}` — delete card
- `POST /api/ai/chat/{board_id}` — AI chat for a specific board

### Frontend Routes
- `/` — redirects to `/boards` or `/login`
- `/login` — login + register (same page, toggle)
- `/boards` — board dashboard (list, create, rename, delete)
- `/board?id=<boardId>` — single board Kanban view

### Key files
- `backend/auth.py` — JWT utilities, `hash_password`, `verify_password`, `get_current_user`
- `backend/main.py` — FastAPI app + router registration
- `backend/ai.py` — OpenRouter integration, `KanbanResponse` schema
- `backend/database.py` — SQLite init, migration, seed data
- `backend/models.py` — all Pydantic models
- `backend/routers/auth.py` — auth endpoints
- `backend/routers/boards.py` — board CRUD
- `backend/routers/columns.py` — column CRUD
- `backend/routers/cards.py` — card CRUD
- `backend/routers/ai_chat.py` — AI chat handler
- `frontend/src/lib/api.ts` — typed API client with JWT injection
- `frontend/src/lib/kanban.ts` — `BoardData`, `Card`, `Column` types + `moveCard()` logic
- `frontend/src/components/KanbanBoard.tsx` — board view (accepts `boardId` prop)
- `frontend/src/components/KanbanCard.tsx` — card with edit modal, priority/labels badges
- `frontend/src/components/AIChatSidebar.tsx` — AI chat (accepts `boardId` prop)

### Card fields
- `title`, `details`, `order`, `column_id` (existing)
- `priority`: `"low" | "medium" | "high"` (default: `"medium"`)
- `due_date`: ISO date string or null
- `labels`: comma-separated string (e.g. `"frontend,urgent"`)

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
npm run test             # vitest unit tests
npm run test:e2e         # playwright e2e tests
npm run test:all         # unit + e2e
```

### Run a single unit test
```bash
cd frontend
npx vitest run src/lib/kanban.test.ts      # lib tests
npx vitest run src/lib/api.test.ts         # API client tests
npx vitest run src/components/KanbanBoard.test.tsx  # component tests
```

### Backend dev (without Docker)
```bash
cd backend
uv pip install -r requirements.txt
uv run uvicorn backend.main:app --reload --port 8000
```

### Run backend tests
```bash
python -m pytest backend/tests/ -v    # all 44 integration tests
python -m pytest backend/tests/test_auth.py    # auth tests only
```

### Run backend smoke test (live OpenRouter call, requires OPENROUTER_API_KEY)
```bash
cd backend
python smoke_test_ai.py
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
