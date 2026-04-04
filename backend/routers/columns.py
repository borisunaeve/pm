from fastapi import APIRouter

from backend.database import get_db_connection
from backend.models import UpdateColumnRequest

router = APIRouter(prefix="/api/columns", tags=["columns"])


@router.put("/{column_id}")
def update_column(column_id: str, request: UpdateColumnRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE columns SET title = ? WHERE id = ?", (request.title, column_id))
    conn.commit()
    conn.close()
    return {"status": "success"}
