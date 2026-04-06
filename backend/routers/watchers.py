from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import WatcherItem

router = APIRouter(prefix="/api/cards", tags=["watchers"])


def _assert_card_access(cursor, card_id: str, user_id: str):
    cursor.execute(
        """SELECT c.id FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (card_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Card not found")


@router.get("/{card_id}/watchers", response_model=List[WatcherItem])
def list_watchers(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        """SELECT cw.user_id, u.username, u.display_name, cw.created_at
           FROM card_watchers cw JOIN users u ON u.id = cw.user_id
           WHERE cw.card_id = ? ORDER BY cw.created_at ASC""",
        (card_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        WatcherItem(
            user_id=r["user_id"], username=r["username"],
            display_name=r["display_name"] or "",
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/{card_id}/watch", status_code=201)
def watch_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        "INSERT OR IGNORE INTO card_watchers (card_id, user_id) VALUES (?, ?)",
        (card_id, current_user["sub"]),
    )
    conn.commit()
    conn.close()
    return {"status": "watching"}


@router.delete("/{card_id}/watch", status_code=204)
def unwatch_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        "DELETE FROM card_watchers WHERE card_id = ? AND user_id = ?",
        (card_id, current_user["sub"]),
    )
    conn.commit()
    conn.close()


@router.get("/{card_id}/watch/status")
def watch_status(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        "SELECT 1 FROM card_watchers WHERE card_id = ? AND user_id = ?",
        (card_id, current_user["sub"]),
    )
    watching = cursor.fetchone() is not None
    conn.close()
    return {"watching": watching}
