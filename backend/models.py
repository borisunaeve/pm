from pydantic import BaseModel
from typing import List, Dict, Optional


# ── Checklist ──────────────────────────────────────────────────────────────────

class ChecklistItem(BaseModel):
    id: str
    title: str
    checked: bool
    order: int


# ── Comments ───────────────────────────────────────────────────────────────────

class Comment(BaseModel):
    id: str
    card_id: str
    user_id: str
    username: str
    content: str
    created_at: str


class CreateCommentRequest(BaseModel):
    content: str


# ── Cards ──────────────────────────────────────────────────────────────────────

class CardModel(BaseModel):
    id: str
    title: str
    details: Optional[str] = ""
    priority: Optional[str] = "medium"
    due_date: Optional[str] = None
    labels: Optional[str] = ""
    checklist_total: Optional[int] = 0
    checklist_done: Optional[int] = 0
    assignee_id: Optional[str] = None
    assignee_username: Optional[str] = None


class ColumnModel(BaseModel):
    id: str
    title: str
    cardIds: List[str]
    wip_limit: Optional[int] = None


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
    assignee_id: Optional[str] = None


class CreateCardRequest(BaseModel):
    title: str
    details: Optional[str] = ""
    column_id: str
    priority: Optional[str] = "medium"
    due_date: Optional[str] = None
    labels: Optional[str] = ""
    assignee_id: Optional[str] = None


# ── Columns ────────────────────────────────────────────────────────────────────

class UpdateColumnRequest(BaseModel):
    title: str
    wip_limit: Optional[int] = None


class CreateColumnRequest(BaseModel):
    title: str
    board_id: str
    wip_limit: Optional[int] = None


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


# ── Activity ───────────────────────────────────────────────────────────────────

class ActivityEntry(BaseModel):
    id: int
    board_id: str
    user_id: str
    username: str
    action: str
    entity_type: str
    entity_title: Optional[str] = None
    created_at: str


# ── Column reorder ─────────────────────────────────────────────────────────────

class ReorderColumnsRequest(BaseModel):
    column_ids: List[str]


# ── Checklist ──────────────────────────────────────────────────────────────────

class CreateChecklistItemRequest(BaseModel):
    title: str


class UpdateChecklistItemRequest(BaseModel):
    title: Optional[str] = None
    checked: Optional[bool] = None


# ── Sharing ────────────────────────────────────────────────────────────────────

class ShareBoardRequest(BaseModel):
    username: str


class BoardMember(BaseModel):
    user_id: str
    username: str
    role: str
    added_at: str
