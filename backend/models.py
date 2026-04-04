from pydantic import BaseModel
from typing import List, Dict, Optional


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


class UpdateCardRequest(BaseModel):
    column_id: str
    order: int
    title: Optional[str] = None
    details: Optional[str] = None


class CreateCardRequest(BaseModel):
    title: str
    details: Optional[str] = ""
    column_id: str


class UpdateColumnRequest(BaseModel):
    title: str
