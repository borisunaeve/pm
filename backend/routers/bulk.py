from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import BulkArchiveRequest, BulkUpdateRequest

router = APIRouter(prefix="/api/cards/bulk", tags=["bulk"])


def _assert_card_bulk_access(cursor, card_ids: list, user_id: str):
    """Validate access for all cards before any writes.  Raises 404 if any card is inaccessible."""
    for card_id in card_ids:
        cursor.execute(
            """SELECT c.id FROM cards c
               JOIN columns col ON col.id = c.column_id
               JOIN boards b ON b.id = col.board_id
               WHERE c.id = ? AND (b.user_id = ? OR
                   b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
            (card_id, user_id, user_id),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Card {card_id} not found")


@router.post("/archive")
def bulk_archive(request: BulkArchiveRequest, current_user: dict = Depends(get_current_user)):
    """Archive multiple cards at once."""
    if not request.card_ids:
        return {"archived": 0}

    conn = get_db_connection()
    cursor = conn.cursor()

    # Validate ALL cards before writing any
    _assert_card_bulk_access(cursor, request.card_ids, current_user["sub"])

    placeholders = ",".join("?" * len(request.card_ids))
    cursor.execute(
        f"UPDATE cards SET archived = 1 WHERE id IN ({placeholders})",
        request.card_ids,
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return {"archived": count}


@router.post("/update")
def bulk_update(request: BulkUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Bulk update cards: move to column and/or assign labels."""
    if not request.card_ids:
        return {"updated": 0}
    if request.column_id is None and request.labels is None:
        return {"updated": 0}

    conn = get_db_connection()
    cursor = conn.cursor()

    # Validate ALL cards before writing any
    _assert_card_bulk_access(cursor, request.card_ids, current_user["sub"])

    # Validate target column if provided
    if request.column_id:
        cursor.execute(
            """SELECT col.id FROM columns col JOIN boards b ON b.id = col.board_id
               WHERE col.id = ? AND (b.user_id = ? OR
                   b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
            (request.column_id, current_user["sub"], current_user["sub"]),
        )
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Target column not found")

    placeholders = ",".join("?" * len(request.card_ids))
    updates = []
    params = []

    if request.column_id is not None:
        updates.append("column_id = ?")
        params.append(request.column_id)
    if request.labels is not None:
        updates.append("labels = ?")
        params.append(request.labels)

    params.extend(request.card_ids)
    cursor.execute(
        f"UPDATE cards SET {', '.join(updates)} WHERE id IN ({placeholders})",
        params,
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return {"updated": count}
