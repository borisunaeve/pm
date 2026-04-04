from fastapi import APIRouter

from backend.constants import BOARD_ID
from backend.database import get_db_connection
from backend.models import BoardData, CardModel, ColumnModel

router = APIRouter(prefix="/api", tags=["board"])


@router.get("/hello")
def hello_world():
    return {"message": "Hello from FastAPI MVP!"}


@router.get("/board", response_model=BoardData)
def get_board():
    """Returns the full Kanban board state exactly as the React frontend expects."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, [order] FROM columns WHERE board_id = ? ORDER BY [order] ASC",
        (BOARD_ID,),
    )
    columns_rows = cursor.fetchall()

    columns = []
    cards_map = {}

    for row in columns_rows:
        col_id = row["id"]

        cursor.execute(
            "SELECT id, title, details FROM cards WHERE column_id = ? ORDER BY [order] ASC",
            (col_id,),
        )
        cards_rows = cursor.fetchall()

        card_ids = []
        for c_row in cards_rows:
            card_id = c_row["id"]
            card_ids.append(card_id)
            cards_map[card_id] = CardModel(id=card_id, title=c_row["title"], details=c_row["details"])

        columns.append(ColumnModel(id=col_id, title=row["title"], cardIds=card_ids))

    conn.close()
    return BoardData(columns=columns, cards=cards_map)
