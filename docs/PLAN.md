# Comprehensive Project Plan for Project Management MVP

## Part 1: Plan
- [x] Analyze the frontend codebase and document it in `frontend/AGENTS.md`.
- [x] Enrich this `PLAN.md` document with detailed substeps, tests, and success criteria.
- [x] Create an implementation plan artifact and task list.
- [ ] Get user sign-off on the plan.
**Success Criteria:** `PLAN.md` and `AGENTS.md` are updated and approved by the user.

## Part 2: Scaffolding
- [ ] Initialize Python FastAPI in `backend/`.
- [ ] Setup `uv` for package management in the backend.
- [ ] Create a "Hello World" API endpoint.
- [ ] Write `scripts/start.sh`, `scripts/start.bat`, `scripts/stop.sh`, `scripts/stop.bat`.
- [ ] Set up Docker and `docker-compose.yml`.
- [ ] Serve a static 'hello world' HTML file from FastAPI at `/`.
**Tests:** Run start scripts. Check `localhost:8000` for "hello world" HTML. Test `/api/hello` endpoint.
**Success Criteria:** Docker container spins up via scripts, backend serves a basic HTML page and answers a test API call.

## Part 3: Add in Frontend
- [ ] Configure Next.js to output a static export (`output: 'export'`).
- [ ] Update FastAPI to serve the Next.js static `out` directory at `/`.
- [ ] Update Dockerfile to build the Next.js frontend and copy it to the backend for serving.
**Tests:** `npm run test:all` in `frontend/`. Check that the Next.js Kanban demo loads at `localhost:8000/`.
**Success Criteria:** The frontend displays perfectly when accessing the backend server's port.

## Part 4: Fake User Sign-In
- [ ] Add a Login page component in Next.js (`/login`).
- [ ] Implement hardcoded ("user", "password") authentication logic using simple cookies or local state.
- [ ] Protect the Kanban board page so it redirects to `/login` if not authenticated.
- [ ] Add a logout button to the main board.
**Tests:** Unit tests for Auth guard. E2E tests for login flow.
**Success Criteria:** User must log in to see the Kanban board and can successfully log out.

## Part 5: Database Modeling
- [ ] Design the SQLite database schema (Users, Boards, Columns, Cards).
- [ ] Define the JSON structure for the initial Kanban state.
- [ ] Document the database approach in `docs/DB_SCHEMA.md`.
- [ ] Request user sign-off on the DB schema.
**Success Criteria:** User approves the schema document.

## Part 6: Backend API & DB Setup
- [ ] Implement database initialization on startup (create SQLite `pm.db`).
- [ ] Create Pydantic models matching the schema.
- [ ] Implement FastAPI endpoints to `GET`, `POST`, `PUT`, `DELETE` cards and columns.
- [ ] Implement a backend endpoint to fetch the user's board state.
**Tests:** Pytest for backend routes and database operations.
**Success Criteria:** API routes successfully run CRUD operations on the SQLite database.

## Part 7: Frontend + Backend Integration
- [ ] Update frontend API calls to point to the actual backend endpoints instead of using mock local state.
- [ ] Implement React Context or state management to sync board with backend.
**Tests:** E2E Playwright tests verifying full full-stack functionality (creating/moving/editing cards).
**Success Criteria:** The Kanban board is fully persistent across page reloads.

## Part 8: AI Connectivity
- [ ] Integrate OpenRouter API in the backend (`openai/gpt-oss-120b`).
- [ ] Create a simple `/api/ai/test` endpoint that prompts "What is 2+2?".
**Tests:** Call `/api/ai/test` and verify a valid response.
**Success Criteria:** Successful API call to OpenRouter with the specified model.

## Part 9: AI Kanban Logic
- [ ] Extend AI backend to receive the current Kanban state (JSON) + user prompt.
- [ ] Setup OpenAI Structured Outputs or JSON mode to return both a text response and optional Kanban updates.
- [ ] Write logic to apply those updates to the database.
**Tests:** Backend unit tests passing varying user prompts and verifying structured updates.
**Success Criteria:** The AI can reliably suggest updates to cards/columns based on natural language requests.

## Part 10: AI Chat UI Widget
- [ ] Build a collapsible AI chat sidebar in the frontend.
- [ ] Implement chat history and typing indicators.
- [ ] Connect the frontend chat to the new AI endpoint.
- [ ] Ensure that when the AI updates the Kanban, the UI refreshes automatically by having the frontend apply the AI's returned state updates.
**Tests:** E2E test verifying that asking the AI to "create a card" results in a new card appearing on the board.
**Success Criteria:** A beautiful sidebar widget allows users to interact with the AI, and the board updates automatically based on the AI's actions.