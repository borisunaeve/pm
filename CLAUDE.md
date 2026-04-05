# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Project Management MVP: a Kanban board web app with AI chat integration. The AI can create, move, delete cards, and rename columns via natural language. MVP constraints: one hardcoded user (`user`/`password`), one board per user, runs locally in Docker.

## Architecture

- **Backend**: Python FastAPI (`backend/`) — serves the REST API at `/api/*` and the Next.js static export at `/`
- **Frontend**: Next.js App Router (`frontend/`) — static export (`output: 'export'`), served by FastAPI from `frontend/out/`
- **Database**: SQLite at `data/pm.db`, initialized on startup with seed data from `frontend/src/lib/kanban.ts`
- **AI**: OpenRouter API via `backend/ai.py`, model `openai/gpt-oss-120b`, using structured JSON output (`KanbanResponse` Pydantic model) to parse board actions
- **Drag-and-drop**: `@dnd-kit/core` + `@dnd-kit/sortable` — cards are draggable within and across columns

### Request flow
Browser → FastAPI → `/api/board` returns `BoardData` JSON → React renders Kanban  
AI chat: Browser → `POST /api/ai/chat` → FastAPI fetches board state → calls OpenRouter → parses `KanbanAction[]` → executes DB operations → returns updated message

### Key files
- `backend/main.py` — all API routes
- `backend/ai.py` — OpenRouter integration, `KanbanResponse`/`KanbanAction` structured output schema
- `backend/database.py` — SQLite init, seed data, `get_db_connection()`
- `backend/models.py` — Pydantic request/response models
- `frontend/src/lib/kanban.ts` — `BoardData`, `Card`, `Column` types + `initialData` seed + `moveCard()` logic
- `backend/constants.py` — `BOARD_ID` constant (hardcoded `"board-1"` for MVP)
- `frontend/src/components/KanbanBoard.tsx` — main board component, fetches from backend API, orchestrates dnd-kit drag state
- `frontend/src/components/AIChatSidebar.tsx` — collapsible AI chat panel

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
npx vitest run src/components/KanbanBoard.test.tsx  # component tests
```

### Backend dev (without Docker)
```bash
cd backend
uv pip install -r requirements.txt
uv run uvicorn backend.main:app --reload --port 8000
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
