import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.auth import get_current_user
from backend.database import get_db_connection

router = APIRouter(prefix="/api/boards", tags=["export"])


@router.get("/{board_id}/export")
def export_board(
    board_id: str,
    format: str = "json",
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id FROM boards WHERE id = ? AND (
            user_id = ? OR
            id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (board_id, current_user["sub"], current_user["sub"]),
    )
    board_row = cursor.fetchone()
    if not board_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Board not found")

    cursor.execute("SELECT id, title FROM boards WHERE id = ?", (board_id,))
    board = cursor.fetchone()

    cursor.execute(
        "SELECT id, title, [order], wip_limit FROM columns WHERE board_id = ? ORDER BY [order]",
        (board_id,),
    )
    columns = cursor.fetchall()

    result = {"board": dict(board), "columns": []}
    for col in columns:
        cursor.execute(
            "SELECT id, title, details, priority, due_date, labels, [order] FROM cards WHERE column_id = ? ORDER BY [order]",
            (col["id"],),
        )
        cards = [dict(c) for c in cursor.fetchall()]
        result["columns"].append({**dict(col), "cards": cards})

    conn.close()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["board", "column", "card_title", "details", "priority", "due_date", "labels"])
        for col_data in result["columns"]:
            for card in col_data["cards"]:
                writer.writerow([
                    result["board"]["title"],
                    col_data["title"],
                    card["title"],
                    card.get("details", ""),
                    card.get("priority", ""),
                    card.get("due_date", ""),
                    card.get("labels", ""),
                ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="board-{board_id}.csv"'},
        )

    # Default: JSON
    json_str = json.dumps(result, indent=2)
    return StreamingResponse(
        iter([json_str]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="board-{board_id}.json"'},
    )
