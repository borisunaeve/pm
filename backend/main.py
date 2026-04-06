import os
import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.routers import ai_chat, analytics, board, boards, bulk, cards, columns
from backend.routers import auth as auth_router
from backend.routers import checklist, comments, export, notifications, relations, search, sharing, sprints


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Project Management API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(board.router)
app.include_router(boards.router)
app.include_router(cards.router)
app.include_router(columns.router)
app.include_router(ai_chat.router)
app.include_router(analytics.router)
app.include_router(bulk.router)      # Must be before cards.router
app.include_router(checklist.router)
app.include_router(comments.router)
app.include_router(export.router)
app.include_router(notifications.router)
app.include_router(relations.router)
app.include_router(search.router)
app.include_router(sharing.router)
app.include_router(sprints.router)


frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "out")
if os.path.exists(frontend_dir):
    next_assets = os.path.join(frontend_dir, "_next")
    if os.path.exists(next_assets):
        app.mount("/_next", StaticFiles(directory=next_assets), name="next-static")

    @app.get("/{full_path:path}")
    def serve_nextjs_routes(full_path: str):
        if not full_path:
            path_to_serve = os.path.join(frontend_dir, "index.html")
        else:
            direct_path = os.path.join(frontend_dir, full_path)
            html_path = os.path.join(frontend_dir, full_path + ".html")
            if os.path.isfile(direct_path):
                path_to_serve = direct_path
            elif os.path.isfile(html_path):
                path_to_serve = html_path
            else:
                path_to_serve = os.path.join(frontend_dir, "index.html")

        if os.path.isfile(path_to_serve):
            with open(path_to_serve, "rb") as f:
                content = f.read()
            mime_type, _ = mimetypes.guess_type(path_to_serve)
            if mime_type is None:
                mime_type = "text/html" if path_to_serve.endswith(".html") else "application/octet-stream"
            return Response(content=content, media_type=mime_type)

        return HTMLResponse("<h1>404 Not Found</h1>", status_code=404)

else:
    @app.get("/")
    def read_root():
        return HTMLResponse(content="<h1>Hello World - FastAPI scaffolding works! (No frontend found)</h1>")
