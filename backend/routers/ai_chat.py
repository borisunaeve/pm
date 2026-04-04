from fastapi import APIRouter, HTTPException

from backend.ai import ChatRequest, call_openrouter
from backend.constants import BOARD_ID
from backend.database import get_db_connection
from backend.models import CreateCardRequest, UpdateCardRequest, UpdateColumnRequest
from backend.routers.cards import create_card, delete_card, update_card
from backend.routers.columns import update_column

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """Fetches the live board state, calls the AI, and executes any returned actions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY [order] ASC",
        (BOARD_ID,),
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
            create_card(CreateCardRequest(
                title=action_obj.get("card_title", "New Card") or "New Card",
                details=action_obj.get("card_details", "") or "",
                column_id=action_obj.get("target_column") or "col-backlog",
            ))

        elif action == "MOVE_CARD":
            card_id = action_obj.get("card_id")
            target_col = action_obj.get("target_column")
            if card_id and target_col:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?",
                    (target_col,),
                )
                row = cursor.fetchone()
                next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0
                conn.close()
                update_card(card_id, UpdateCardRequest(column_id=target_col, order=next_order))

        elif action == "DELETE_CARD":
            card_id = action_obj.get("card_id")
            if card_id:
                delete_card(card_id)

        elif action == "RENAME_COLUMN":
            col_id = action_obj.get("column_id")
            new_title = action_obj.get("new_column_title")
            if col_id and new_title:
                update_column(col_id, UpdateColumnRequest(title=new_title))

    return {
        "status": "success",
        "message": ai_response.get("response_message", "Done."),
        "actions": actions,
    }
