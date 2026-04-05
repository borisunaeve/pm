import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import ChecklistItem, CreateChecklistItemRequest, UpdateChecklistItemRequest

router = APIRouter(prefix="/api/cards", tags=["checklist"])


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


@router.get("/{card_id}/checklist", response_model=List[ChecklistItem])
def list_checklist(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        "SELECT id, title, checked, [order] FROM checklist_items WHERE card_id = ? ORDER BY [order] ASC",
        (card_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [ChecklistItem(id=r["id"], title=r["title"], checked=bool(r["checked"]), order=r["order"])
            for r in rows]


@router.post("/{card_id}/checklist", response_model=ChecklistItem, status_code=201)
def create_checklist_item(
    card_id: str,
    request: CreateChecklistItemRequest,
    current_user: dict = Depends(get_current_user),
):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    cursor.execute(
        "SELECT MAX([order]) as max_o FROM checklist_items WHERE card_id = ?", (card_id,)
    )
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0

    item_id = f"chk-{uuid.uuid4().hex[:10]}"
    cursor.execute(
        "INSERT INTO checklist_items (id, card_id, title, checked, [order]) VALUES (?, ?, ?, 0, ?)",
        (item_id, card_id, request.title.strip(), next_order),
    )
    conn.commit()
    conn.close()
    return ChecklistItem(id=item_id, title=request.title.strip(), checked=False, order=next_order)


@router.put("/{card_id}/checklist/{item_id}", response_model=ChecklistItem)
def update_checklist_item(
    card_id: str,
    item_id: str,
    request: UpdateChecklistItemRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    cursor.execute(
        "SELECT id, title, checked, [order] FROM checklist_items WHERE id = ? AND card_id = ?",
        (item_id, card_id),
    )
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Checklist item not found")

    new_title = request.title if request.title is not None else existing["title"]
    new_checked = int(request.checked) if request.checked is not None else existing["checked"]

    cursor.execute(
        "UPDATE checklist_items SET title = ?, checked = ? WHERE id = ?",
        (new_title, new_checked, item_id),
    )
    conn.commit()
    conn.close()
    return ChecklistItem(id=item_id, title=new_title, checked=bool(new_checked), order=existing["order"])


@router.delete("/{card_id}/checklist/{item_id}", status_code=204)
def delete_checklist_item(
    card_id: str,
    item_id: str,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        "SELECT id FROM checklist_items WHERE id = ? AND card_id = ?", (item_id, card_id)
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")
    cursor.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
