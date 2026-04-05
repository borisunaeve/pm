import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.ai import ChatRequest, call_openrouter
from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CreateCardRequest, UpdateCardRequest, UpdateColumnRequest

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat/{board_id}")
async def chat_with_ai(
    board_id: str,
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Fetches the live board state, calls the AI, and executes returned actions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify board ownership
    cursor.execute(
        "SELECT id FROM boards WHERE id = ? AND user_id = ?",
        (board_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Board not found")

    cursor.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY [order] ASC",
        (board_id,),
    )
    columns = cursor.fetchall()

    board_context_lines = []
    for col_row in columns:
        col_id = col_row["id"]
        board_context_lines.append(f"Column '{col_row['title']}' (ID: {col_id}):")
        cursor.execute(
            "SELECT id, title FROM cards WHERE column_id = ? ORDER BY [order] ASC",
            (col_id,),
        )
        cards = cursor.fetchall()
        if not cards:
            board_context_lines.append("  - (Empty)")
        else:
            for card in cards:
                board_context_lines.append(f"  - Card '{card['title']}' (ID: {card['id']})")

    conn.close()

    try:
        ai_response = await call_openrouter(request.messages, board_context="\n".join(board_context_lines))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    actions = ai_response.get("actions", [])

    for action_obj in actions:
        action = action_obj.get("action", "NONE")

        if action == "CREATE_CARD":
            target_col = action_obj.get("target_column") or _first_column(board_id)
            conn = get_db_connection()
            cursor = conn.cursor()
            new_id = f"card-{uuid.uuid4().hex[:8]}"
            cursor.execute(
                "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?", (target_col,)
            )
            row = cursor.fetchone()
            next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0
            cursor.execute(
                "INSERT INTO cards (id, column_id, title, details, [order]) VALUES (?, ?, ?, ?, ?)",
                (new_id, target_col, action_obj.get("card_title", "New Card"), action_obj.get("card_details", ""), next_order),
            )
            conn.commit()
            conn.close()

        elif action == "MOVE_CARD":
            card_id = action_obj.get("card_id")
            target_col = action_obj.get("target_column")
            if card_id and target_col:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?", (target_col,)
                )
                row = cursor.fetchone()
                next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0
                cursor.execute(
                    "UPDATE cards SET column_id = ?, [order] = ? WHERE id = ?",
                    (target_col, next_order, card_id),
                )
                conn.commit()
                conn.close()

        elif action == "DELETE_CARD":
            card_id = action_obj.get("card_id")
            if card_id:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
                conn.commit()
                conn.close()

        elif action == "RENAME_COLUMN":
            col_id = action_obj.get("column_id")
            new_title = action_obj.get("new_column_title")
            if col_id and new_title:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE columns SET title = ? WHERE id = ?", (new_title, col_id))
                conn.commit()
                conn.close()

    return {
        "status": "success",
        "message": ai_response.get("response_message", "Done."),
        "actions": actions,
    }


def _first_column(board_id: str) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM columns WHERE board_id = ? ORDER BY [order] ASC LIMIT 1", (board_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else ""
