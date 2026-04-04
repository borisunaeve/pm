from pydantic import BaseModel
from typing import List, Dict, Optional

# Standard Pydantic representation matching the frontend shape
class CardModel(BaseModel):
    id: str
    title: str
    details: Optional[str] = ""

class ColumnModel(BaseModel):
    id: str
    title: str
    cardIds: List[str]

class BoardData(BaseModel):
    columns: List[ColumnModel]
    cards: Dict[str, CardModel]

# Request models for updating the DB
class UpdateCardRequest(BaseModel):
    column_id: str
    order: int
    title: str = None
    details: str = None

class CreateCardRequest(BaseModel):
    title: str
    details: Optional[str] = ""
    column_id: str

class UpdateColumnRequest(BaseModel):
    title: str
