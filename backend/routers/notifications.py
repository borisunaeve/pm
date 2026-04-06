from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import NotificationItem, PersistentNotification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/due", response_model=List[NotificationItem])
def get_due_notifications(current_user: dict = Depends(get_current_user)):
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


@router.get("", response_model=List[PersistentNotification])
def get_notifications(current_user: dict = Depends(get_current_user)):
    """Return persistent notifications (card updates, comments, assignments)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, user_id, board_id, card_id, type, message, read, created_at
           FROM user_notifications
           WHERE user_id = ?
           ORDER BY created_at DESC LIMIT 100""",
        (current_user["sub"],),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        PersistentNotification(
            id=r["id"], user_id=r["user_id"], board_id=r["board_id"],
            card_id=r["card_id"], type=r["type"], message=r["message"],
            read=bool(r["read"]), created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/unread-count")
def get_unread_count(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM user_notifications WHERE user_id = ? AND read = 0",
        (current_user["sub"],),
    )
    row = cursor.fetchone()
    conn.close()
    return {"count": row["cnt"]}


@router.post("/{notification_id}/read", status_code=200)
def mark_read(notification_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM user_notifications WHERE id = ? AND user_id = ?",
        (notification_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Notification not found")
    cursor.execute(
        "UPDATE user_notifications SET read = 1 WHERE id = ?",
        (notification_id,),
    )
    conn.commit()
    conn.close()
    return {"status": "read"}


@router.post("/read-all", status_code=200)
def mark_all_read(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_notifications SET read = 1 WHERE user_id = ?",
        (current_user["sub"],),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.delete("", status_code=204)
def clear_read_notifications(current_user: dict = Depends(get_current_user)):
    """Delete all read notifications for the current user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_notifications WHERE user_id = ? AND read = 1",
        (current_user["sub"],),
    )
    conn.commit()
    conn.close()
