from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CardLink, CreateLinkRequest

router = APIRouter(prefix="/api/cards", tags=["links"])


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


def _assert_link_owner(cursor, link_id: int, card_id: str):
    cursor.execute("SELECT id FROM card_links WHERE id = ? AND card_id = ?", (link_id, card_id))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Link not found")


@router.get("/{card_id}/links", response_model=List[CardLink])
def list_links(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        "SELECT id, card_id, title, url, created_at FROM card_links WHERE card_id = ? ORDER BY created_at ASC",
        (card_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [CardLink(id=r["id"], card_id=r["card_id"], title=r["title"], url=r["url"], created_at=r["created_at"]) for r in rows]


@router.post("/{card_id}/links", status_code=201, response_model=CardLink)
def create_link(
    card_id: str,
    request: CreateLinkRequest,
    current_user: dict = Depends(get_current_user),
):
    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        "INSERT INTO card_links (card_id, title, url) VALUES (?, ?, ?)",
        (card_id, request.title or "", request.url.strip()),
    )
    link_id = cursor.lastrowid
    cursor.execute("SELECT id, card_id, title, url, created_at FROM card_links WHERE id = ?", (link_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return CardLink(id=row["id"], card_id=row["card_id"], title=row["title"], url=row["url"], created_at=row["created_at"])


@router.delete("/{card_id}/links/{link_id}", status_code=204)
def delete_link(
    card_id: str,
    link_id: int,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    _assert_link_owner(cursor, link_id, card_id)
    cursor.execute("DELETE FROM card_links WHERE id = ?", (link_id,))
    conn.commit()
    conn.close()
