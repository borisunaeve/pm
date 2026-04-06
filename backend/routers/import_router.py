import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user
from backend.database import get_db_connection

router = APIRouter(prefix="/api/boards", tags=["import"])

VALID_PRIORITIES = {"low", "medium", "high"}


class CSVImportRequest(BaseModel):
    csv_text: str        # raw CSV content
    column_id: str = "" # target column; if empty, use first column


class ImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]


def _assert_access(cursor, board_id: str, user_id: str):
    cursor.execute(
        """SELECT id FROM boards WHERE id = ? AND (
            user_id = ? OR
            id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (board_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Board not found")


@router.post("/{board_id}/import", response_model=ImportResult)
def import_cards(
    board_id: str,
    request: CSVImportRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_access(cursor, board_id, current_user["sub"])

    # Determine target column
    if request.column_id:
        cursor.execute("SELECT id FROM columns WHERE id = ? AND board_id = ?", (request.column_id, board_id))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Column not found in this board")
        col_id = request.column_id
    else:
        cursor.execute("SELECT id FROM columns WHERE board_id = ? ORDER BY [order] ASC LIMIT 1", (board_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=400, detail="Board has no columns")
        col_id = row["id"]

    # Get current max order for the column
    cursor.execute("SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?", (col_id,))
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0

    created = 0
    skipped = 0
    errors: list[str] = []

    try:
        reader = csv.DictReader(io.StringIO(request.csv_text.strip()))
        # Normalize header names (lowercase, strip)
        if reader.fieldnames is None:
            conn.close()
            raise HTTPException(status_code=400, detail="CSV has no header row")
        headers = [h.strip().lower() for h in reader.fieldnames]
        if "title" not in headers:
            conn.close()
            raise HTTPException(status_code=400, detail="CSV must have a 'title' column")

        for i, raw_row in enumerate(reader, start=2):
            row_data = {k.strip().lower(): (v or "").strip() for k, v in raw_row.items() if k}
            title = row_data.get("title", "").strip()
            if not title:
                skipped += 1
                continue

            priority = row_data.get("priority", "medium").lower()
            if priority not in VALID_PRIORITIES:
                priority = "medium"

            due_date = row_data.get("due_date", "") or row_data.get("due date", "")
            labels = row_data.get("labels", "") or row_data.get("label", "")
            details = row_data.get("details", "") or row_data.get("description", "")

            card_id = f"card-{uuid.uuid4().hex[:8]}"
            try:
                cursor.execute(
                    """INSERT INTO cards (id, column_id, title, details, [order], priority, due_date, labels)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (card_id, col_id, title, details, next_order, priority,
                     due_date if due_date else None, labels),
                )
                next_order += 1
                created += 1
                # Auto-watch creator
                cursor.execute(
                    "INSERT OR IGNORE INTO card_watchers (card_id, user_id) VALUES (?, ?)",
                    (card_id, current_user["sub"]),
                )
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")
                skipped += 1

    except csv.Error as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"CSV parse error: {e}")

    conn.commit()
    conn.close()
    return ImportResult(created=created, skipped=skipped, errors=errors)
