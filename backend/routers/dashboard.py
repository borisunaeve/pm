from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import DashboardCard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/my-cards", response_model=List[DashboardCard])
def get_my_cards(current_user: dict = Depends(get_current_user)):
    """Return all non-archived cards assigned to the current user across all accessible boards."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT c.id, c.title, c.priority, c.due_date, c.labels,
               b.id as board_id, b.title as board_title,
               col.id as column_id, col.title as column_title,
               (SELECT COUNT(*) FROM checklist_items WHERE card_id = c.id) as checklist_total,
               (SELECT COUNT(*) FROM checklist_items WHERE card_id = c.id AND checked = 1) as checklist_done
        FROM cards c
        JOIN columns col ON col.id = c.column_id
        JOIN boards b ON b.id = col.board_id
        WHERE c.assignee_id = ?
          AND c.archived = 0
          AND (b.user_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))
        ORDER BY c.due_date ASC NULLS LAST, c.priority DESC
        """,
        (current_user["sub"], current_user["sub"], current_user["sub"]),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        DashboardCard(
            id=r["id"], title=r["title"], priority=r["priority"],
            due_date=r["due_date"], labels=r["labels"],
            board_id=r["board_id"], board_title=r["board_title"],
            column_id=r["column_id"], column_title=r["column_title"],
            checklist_total=r["checklist_total"], checklist_done=r["checklist_done"],
        )
        for r in rows
    ]


@router.get("/summary")
def get_dashboard_summary(current_user: dict = Depends(get_current_user)):
    """High-level summary: board count, assigned cards, overdue, due this week."""
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = current_user["sub"]

    today = date.today()
    week_end = today + timedelta(days=7)

    cursor.execute(
        """SELECT COUNT(DISTINCT b.id) as board_count
           FROM boards b
           WHERE b.user_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?)""",
        (user_id, user_id),
    )
    board_count = cursor.fetchone()["board_count"]

    cursor.execute(
        """SELECT COUNT(*) as cnt FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.assignee_id = ? AND c.archived = 0
             AND (b.user_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (user_id, user_id, user_id),
    )
    assigned_count = cursor.fetchone()["cnt"]

    cursor.execute(
        """SELECT COUNT(*) as cnt FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.assignee_id = ? AND c.archived = 0 AND c.due_date < ?
             AND (b.user_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (user_id, today.isoformat(), user_id, user_id),
    )
    overdue_count = cursor.fetchone()["cnt"]

    cursor.execute(
        """SELECT COUNT(*) as cnt FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.assignee_id = ? AND c.archived = 0
             AND c.due_date >= ? AND c.due_date <= ?
             AND (b.user_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (user_id, today.isoformat(), week_end.isoformat(), user_id, user_id),
    )
    due_this_week = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM user_notifications WHERE user_id = ? AND read = 0",
        (user_id,),
    )
    unread_notifications = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "board_count": board_count,
        "assigned_cards": assigned_count,
        "overdue_cards": overdue_count,
        "due_this_week": due_this_week,
        "unread_notifications": unread_notifications,
    }
