from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import (
    BoardAnalytics,
    ColumnStats,
    LabelStats,
    PriorityStats,
    SprintProgress,
)
from backend.routers.boards import _assert_access

router = APIRouter(prefix="/api/boards", tags=["analytics"])


@router.get("/{board_id}/analytics", response_model=BoardAnalytics)
def get_board_analytics(board_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_access(cursor, board_id, current_user["sub"])

    today = datetime.utcnow().date()
    week_end = today + timedelta(days=7)

    # ── Total & archived card counts ──────────────────────────────────────────
    cursor.execute(
        "SELECT COUNT(*) FROM cards c JOIN columns col ON col.id = c.column_id WHERE col.board_id = ?",
        (board_id,),
    )
    total_cards = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM cards c JOIN columns col ON col.id = c.column_id WHERE col.board_id = ? AND c.archived = 1",
        (board_id,),
    )
    archived_cards = cursor.fetchone()[0]

    # ── Overdue & due this week (non-archived) ────────────────────────────────
    cursor.execute(
        """SELECT COUNT(*) FROM cards c
           JOIN columns col ON col.id = c.column_id
           WHERE col.board_id = ? AND c.archived = 0 AND c.due_date IS NOT NULL AND c.due_date < ?""",
        (board_id, today.isoformat()),
    )
    overdue_cards = cursor.fetchone()[0]

    cursor.execute(
        """SELECT COUNT(*) FROM cards c
           JOIN columns col ON col.id = c.column_id
           WHERE col.board_id = ? AND c.archived = 0
             AND c.due_date IS NOT NULL
             AND c.due_date >= ? AND c.due_date <= ?""",
        (board_id, today.isoformat(), week_end.isoformat()),
    )
    due_this_week = cursor.fetchone()[0]

    # ── Per-column stats ──────────────────────────────────────────────────────
    cursor.execute(
        """SELECT col.id, col.title,
               COUNT(CASE WHEN c.archived = 0 THEN 1 END) as total,
               COUNT(CASE WHEN c.archived = 1 THEN 1 END) as archived
           FROM columns col
           LEFT JOIN cards c ON c.column_id = col.id
           WHERE col.board_id = ?
           GROUP BY col.id
           ORDER BY col.[order] ASC""",
        (board_id,),
    )
    by_column = [
        ColumnStats(
            column_id=r["id"],
            column_title=r["title"],
            total=r["total"] or 0,
            archived=r["archived"] or 0,
        )
        for r in cursor.fetchall()
    ]

    # ── Priority breakdown (non-archived) ─────────────────────────────────────
    cursor.execute(
        """SELECT c.priority, COUNT(*) as cnt
           FROM cards c JOIN columns col ON col.id = c.column_id
           WHERE col.board_id = ? AND c.archived = 0
           GROUP BY c.priority""",
        (board_id,),
    )
    by_priority = [
        PriorityStats(priority=r["priority"] or "medium", count=r["cnt"])
        for r in cursor.fetchall()
    ]

    # ── Label breakdown (non-archived, skip blank) ────────────────────────────
    cursor.execute(
        """SELECT c.labels FROM cards c
           JOIN columns col ON col.id = c.column_id
           WHERE col.board_id = ? AND c.archived = 0 AND c.labels IS NOT NULL AND c.labels != ''""",
        (board_id,),
    )
    label_counts: dict[str, int] = {}
    for row in cursor.fetchall():
        for lbl in (l.strip() for l in row["labels"].split(",") if l.strip()):
            label_counts[lbl] = label_counts.get(lbl, 0) + 1
    by_label = sorted(
        [LabelStats(label=k, count=v) for k, v in label_counts.items()],
        key=lambda x: -x.count,
    )

    # ── Sprint progress ────────────────────────────────────────────────────────
    cursor.execute(
        """SELECT s.id, s.title, s.status,
               COUNT(c.id) as total_cards,
               SUM(CASE WHEN col.title LIKE '%done%' OR col.title LIKE '%complete%' THEN 1 ELSE 0 END) as done_cards,
               COALESCE(SUM(c.estimated_hours), 0) as estimated_hours,
               COALESCE(SUM(c.actual_hours), 0) as actual_hours
           FROM sprints s
           LEFT JOIN cards c ON c.sprint_id = s.id AND c.archived = 0
           LEFT JOIN columns col ON col.id = c.column_id
           WHERE s.board_id = ?
           GROUP BY s.id
           ORDER BY s.created_at DESC""",
        (board_id,),
    )
    sprints = [
        SprintProgress(
            sprint_id=r["id"],
            sprint_title=r["title"],
            status=r["status"],
            total_cards=r["total_cards"] or 0,
            done_cards=r["done_cards"] or 0,
            estimated_hours=r["estimated_hours"] or 0.0,
            actual_hours=r["actual_hours"] or 0.0,
        )
        for r in cursor.fetchall()
    ]

    # ── Average time tracking ─────────────────────────────────────────────────
    cursor.execute(
        """SELECT AVG(c.estimated_hours), AVG(c.actual_hours)
           FROM cards c JOIN columns col ON col.id = c.column_id
           WHERE col.board_id = ? AND c.archived = 0""",
        (board_id,),
    )
    avg_row = cursor.fetchone()
    avg_estimated = round(avg_row[0] or 0.0, 2)
    avg_actual = round(avg_row[1] or 0.0, 2)

    conn.close()
    return BoardAnalytics(
        board_id=board_id,
        total_cards=total_cards,
        archived_cards=archived_cards,
        overdue_cards=overdue_cards,
        due_this_week=due_this_week,
        by_column=by_column,
        by_priority=by_priority,
        by_label=by_label,
        sprints=sprints,
        avg_estimated_hours=avg_estimated,
        avg_actual_hours=avg_actual,
    )
