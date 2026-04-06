from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CardRelation, CreateRelationRequest

router = APIRouter(prefix="/api/cards", tags=["relations"])

VALID_RELATION_TYPES = {"blocks", "blocked-by", "relates-to", "duplicate-of"}


def _assert_card_access(cursor, card_id: str, user_id: str):
    cursor.execute(
        """SELECT c.id, c.title, col.board_id FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (card_id, user_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")
    return row


@router.get("/{card_id}/relations", response_model=List[CardRelation])
def list_relations(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    cursor.execute(
        """SELECT r.id, r.card_id, r.related_card_id, c.title as related_card_title,
                  r.relation_type, r.created_at
           FROM card_relations r
           JOIN cards c ON c.id = r.related_card_id
           WHERE r.card_id = ?
           ORDER BY r.created_at ASC""",
        (card_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        CardRelation(
            id=r["id"],
            card_id=r["card_id"],
            related_card_id=r["related_card_id"],
            related_card_title=r["related_card_title"],
            relation_type=r["relation_type"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/{card_id}/relations", response_model=CardRelation, status_code=201)
def add_relation(
    card_id: str,
    request: CreateRelationRequest,
    current_user: dict = Depends(get_current_user),
):
    if request.relation_type not in VALID_RELATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation type. Must be one of: {', '.join(sorted(VALID_RELATION_TYPES))}",
        )
    if card_id == request.related_card_id:
        raise HTTPException(status_code=400, detail="A card cannot relate to itself")

    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    # Verify the related card exists and is accessible
    cursor.execute(
        """SELECT c.id, c.title FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (request.related_card_id, current_user["sub"], current_user["sub"]),
    )
    related = cursor.fetchone()
    if not related:
        conn.close()
        raise HTTPException(status_code=404, detail="Related card not found")

    try:
        cursor.execute(
            """INSERT INTO card_relations (card_id, related_card_id, relation_type)
               VALUES (?, ?, ?)""",
            (card_id, request.related_card_id, request.relation_type),
        )
        conn.commit()
        relation_id = cursor.lastrowid
        cursor.execute("SELECT created_at FROM card_relations WHERE id = ?", (relation_id,))
        created_at = cursor.fetchone()["created_at"]
    except Exception:
        conn.close()
        raise HTTPException(status_code=409, detail="Relation already exists")

    conn.close()
    return CardRelation(
        id=relation_id,
        card_id=card_id,
        related_card_id=request.related_card_id,
        related_card_title=related["title"],
        relation_type=request.relation_type,
        created_at=created_at,
    )


@router.delete("/{card_id}/relations/{relation_id}", status_code=204)
def delete_relation(
    card_id: str,
    relation_id: int,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    cursor.execute(
        "DELETE FROM card_relations WHERE id = ? AND card_id = ?",
        (relation_id, card_id),
    )
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Relation not found")

    conn.commit()
    conn.close()
