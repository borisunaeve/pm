from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import NotificationItem

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationItem])
def get_notifications(current_user: dict = Depends(get_current_user)):
    """Return overdue and due-soon cards from all boards the user has access to."""
    conn = get_db_connection()
    cursor = conn.cursor()

    today = date.today()
    soon = today + timedelta(days=3)

    cursor.execute(
        """
        SELECT c.id as card_id, c.title as card_title, c.due_date,
               b.id as board_id, b.title as board_title,
               col.title as column_title
        FROM cards c
        JOIN columns col ON col.id = c.column_id
        JOIN boards b ON b.id = col.board_id
        WHERE c.archived = 0
          AND c.due_date IS NOT NULL
          AND c.due_date <= ?
          AND (b.user_id = ? OR b.id IN (
              SELECT board_id FROM board_members WHERE user_id = ?
          ))
        ORDER BY c.due_date ASC
        """,
        (soon.isoformat(), current_user["sub"], current_user["sub"]),
    )
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        due = r["due_date"]
        ntype = "overdue" if due < today.isoformat() else "due_soon"
        items.append(
            NotificationItem(
                card_id=r["card_id"],
                card_title=r["card_title"],
                board_id=r["board_id"],
                board_title=r["board_title"],
                column_title=r["column_title"],
                due_date=due,
                type=ntype,
            )
        )
    return items
