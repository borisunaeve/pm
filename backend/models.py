from pydantic import BaseModel
from typing import List, Dict, Optional


# ── Cards ──────────────────────────────────────────────────────────────────────

class CardModel(BaseModel):
    id: str
    title: str
    details: Optional[str] = ""
    priority: Optional[str] = "medium"
    due_date: Optional[str] = None
    labels: Optional[str] = ""


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
    priority: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[str] = None


class CreateCardRequest(BaseModel):
    title: str
    details: Optional[str] = ""
    column_id: str
    priority: Optional[str] = "medium"
    due_date: Optional[str] = None
    labels: Optional[str] = ""


# ── Columns ────────────────────────────────────────────────────────────────────

class UpdateColumnRequest(BaseModel):
    title: str


class CreateColumnRequest(BaseModel):
    title: str
    board_id: str


# ── Boards ─────────────────────────────────────────────────────────────────────

class BoardSummary(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    card_count: Optional[int] = 0


class CreateBoardRequest(BaseModel):
    title: str


class UpdateBoardRequest(BaseModel):
    title: str


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


class UserProfile(BaseModel):
    id: str
    username: str
    created_at: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
