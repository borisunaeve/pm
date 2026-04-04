import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from backend.database import init_db, get_db_connection
from backend.models import BoardData, ColumnModel, CardModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database on startup
    init_db()
    yield

app = FastAPI(title="Project Management API MVP", lifespan=lifespan)

@app.get("/api/board", response_model=BoardData)
def get_board():
    """Returns the full Kanban board state exactly as the React frontend expects."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # We only have 1 board in the MVP ("board-1").
    cursor.execute("SELECT id, title, [order] FROM columns WHERE board_id = 'board-1' ORDER BY [order] ASC")
    columns_rows = cursor.fetchall()
    
    columns = []
    cards_map = {}
    
    for row in columns_rows:
        col_id = row["id"]
        
        # Get cards for this column
        cursor.execute("SELECT id, title, details FROM cards WHERE column_id = ? ORDER BY [order] ASC", (col_id,))
        cards_rows = cursor.fetchall()
        
        card_ids = []
        for c_row in cards_rows:
            card_id = c_row["id"]
            card_ids.append(card_id)
            cards_map[card_id] = CardModel(id=card_id, title=c_row["title"], details=c_row["details"])
            
        columns.append(ColumnModel(id=col_id, title=row["title"], cardIds=card_ids))
        
    conn.close()
    return BoardData(columns=columns, cards=cards_map)

# Serve a basic test endpoint to ensure API works
@app.get("/api/hello")
def hello_world():
    return {"message": "Hello from FastAPI MVP!"}

from backend.models import CreateCardRequest, UpdateCardRequest
import uuid

@app.post("/api/cards")
def create_card(request: CreateCardRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    new_id = f"card-{uuid.uuid4().hex[:8]}"
    
    # Get current max order in column
    cursor.execute("SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?", (request.column_id,))
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0
    
    cursor.execute(
        "INSERT INTO cards (id, column_id, title, details, [order]) VALUES (?, ?, ?, ?, ?)",
        (new_id, request.column_id, request.title, request.details, next_order)
    )
    conn.commit()
    conn.close()
    return {"id": new_id, "title": request.title, "details": request.details, "column_id": request.column_id}

@app.put("/api/cards/{card_id}")
def update_card(card_id: str, request: UpdateCardRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    if request.title is not None:
        updates.append("title = ?")
        params.append(request.title)
    if request.details is not None:
        updates.append("details = ?")
        params.append(request.details)
    
    updates.append("column_id = ?")
    params.append(request.column_id)
    updates.append("[order] = ?")
    params.append(request.order)
    
    params.append(card_id)
    
    query = f"UPDATE cards SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, tuple(params))
    
    # Simple fix for sibling ordering - For MVP, we trust the frontend sends correct orders 
    # and we just update this specific card's order. A real app might resequence the whole column.
    
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/cards/{card_id}")
def delete_card(card_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

from backend.models import UpdateColumnRequest

@app.put("/api/columns/{column_id}")
def update_column(column_id: str, request: UpdateColumnRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE columns SET title = ? WHERE id = ?", (request.title, column_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

from backend.ai import call_openrouter, ChatMessage, ChatRequest
from backend.models import CreateCardRequest, UpdateCardRequest

@app.post("/api/ai/chat")
async def chat_with_ai(request: ChatRequest):
    """Processes chat messages, gets structured output from AI, performs DB actions, and returns response."""
    try:
        # 1. Fetch current board context to inject into AI prompt
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title FROM columns WHERE board_id = 'board-1' ORDER BY [order] ASC")
        columns = cursor.fetchall()
        
        board_context_lines = []
        for col_row in columns:
            col_id = col_row["id"]
            col_title = col_row["title"]
            board_context_lines.append(f"Column '{col_title}' (ID: {col_id}):")
            
            cursor.execute("SELECT id, title FROM cards WHERE column_id = ? ORDER BY [order] ASC", (col_id,))
            cards = cursor.fetchall()
            
            if not cards:
                board_context_lines.append("  - (Empty)")
            else:
                for card in cards:
                    board_context_lines.append(f"  - Card '{card['title']}' (ID: {card['id']})")
        
        conn.close()
        board_context = "\n".join(board_context_lines)
        
        # 2. Call OpenRouter with the live board state
        ai_response = await call_openrouter(request.messages, board_context=board_context)
        actions = ai_response.get("actions", [])
        
        # Perform DB operations for each requested action
        for action_obj in actions:
            action = action_obj.get("action", "NONE")
            
            if action == "CREATE_CARD":
                req = CreateCardRequest(
                    title=action_obj.get("card_title", "New Card") or "New Card",
                    details=action_obj.get("card_details", "") or "",
                    column_id=action_obj.get("target_column") or "col-backlog"
                )
                create_card(req)
                
            elif action == "MOVE_CARD":
                card_id = action_obj.get("card_id")
                target_col = action_obj.get("target_column")
                if card_id and target_col:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?", (target_col,))
                    row = cursor.fetchone()
                    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0
                    conn.close()
                    
                    req = UpdateCardRequest(column_id=target_col, order=next_order)
                    update_card(card_id, req)
                    
            elif action == "DELETE_CARD":
                card_id = action_obj.get("card_id")
                if card_id:
                    delete_card(card_id)
                    
            elif action == "RENAME_COLUMN":
                col_id = action_obj.get("column_id")
                new_title = action_obj.get("new_column_title")
                if col_id and new_title:
                    req = UpdateColumnRequest(title=new_title)
                    update_column(col_id, req)

        return {
            "status": "success", 
            "message": ai_response.get("response_message", "Done."),
            "action": ai_response
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

from fastapi.staticfiles import StaticFiles
from fastapi import Request, Response
from fastapi.responses import HTMLResponse
import mimetypes

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "out")
if os.path.exists(frontend_dir):
    # Mount the _next static assets directly
    next_assets = os.path.join(frontend_dir, "_next")
    if os.path.exists(next_assets):
        app.mount("/_next", StaticFiles(directory=next_assets), name="next-static")
    
    # Catch-all route for all other Next.js pages and public resources
    @app.get("/{full_path:path}")
    def serve_nextjs_routes(full_path: str):
        path_to_serve = None
        
        if not full_path:
            # Root route -> index.html
            path_to_serve = os.path.join(frontend_dir, "index.html")
        else:
            # 1. Try exact file (e.g., favicon.ico, /login.html directly)
            direct_path = os.path.join(frontend_dir, full_path)
            if os.path.isfile(direct_path):
                path_to_serve = direct_path
            else:
                # 2. Try appending .html (e.g., /login -> /login.html)
                html_path = os.path.join(frontend_dir, full_path + ".html")
                if os.path.isfile(html_path):
                    path_to_serve = html_path
                else:
                    # 3. Fallback to index.html (useful for 404s or SPA-like client routing)
                    path_to_serve = os.path.join(frontend_dir, "index.html")
        
        if path_to_serve and os.path.isfile(path_to_serve):
            with open(path_to_serve, "rb") as f:
                content = f.read()
            mime_type, _ = mimetypes.guess_type(path_to_serve)
            if mime_type is None:
                if path_to_serve.endswith(".html"):
                    mime_type = "text/html"
                else:
                    mime_type = "application/octet-stream"
            return Response(content=content, media_type=mime_type)
        
        return HTMLResponse("<h1>404 Not Found - Next.js fallback failed</h1>", status_code=404)

else:
    @app.get("/")
    def read_root():
        return HTMLResponse(content="<h1>Hello World - FastAPI scaffolding works! (No frontend found)</h1>")
