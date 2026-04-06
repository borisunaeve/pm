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
    archived: bool = False
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    sprint_id: Optional[str] = None
    sprint_title: Optional[str] = None


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
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    sprint_id: Optional[str] = None


class CreateCardRequest(BaseModel):
    title: str
    details: Optional[str] = ""
    column_id: str
    priority: Optional[str] = "medium"
    due_date: Optional[str] = None
    labels: Optional[str] = ""
    assignee_id: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    sprint_id: Optional[str] = None


# ── Sprints ────────────────────────────────────────────────────────────────────

class Sprint(BaseModel):
    id: str
    board_id: str
    title: str
    goal: Optional[str] = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "planning"   # planning | active | completed
    created_at: str
    card_count: int = 0
    done_count: int = 0


class CreateSprintRequest(BaseModel):
    title: str
    goal: Optional[str] = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class UpdateSprintRequest(BaseModel):
    title: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ── Analytics ──────────────────────────────────────────────────────────────────

class ColumnStats(BaseModel):
    column_id: str
    column_title: str
    total: int
    archived: int


class PriorityStats(BaseModel):
    priority: str
    count: int


class LabelStats(BaseModel):
    label: str
    count: int


class SprintProgress(BaseModel):
    sprint_id: str
    sprint_title: str
    status: str
    total_cards: int
    done_cards: int
    estimated_hours: float
    actual_hours: float


class BoardAnalytics(BaseModel):
    board_id: str
    total_cards: int
    archived_cards: int
    overdue_cards: int
    due_this_week: int
    by_column: List[ColumnStats]
    by_priority: List[PriorityStats]
    by_label: List[LabelStats]
    sprints: List[SprintProgress]
    avg_estimated_hours: float
    avg_actual_hours: float


# ── Card Relations ─────────────────────────────────────────────────────────────

class CardRelation(BaseModel):
    id: int
    card_id: str
    related_card_id: str
    related_card_title: str
    relation_type: str
    created_at: str


class CreateRelationRequest(BaseModel):
    related_card_id: str
    relation_type: str = "relates-to"


# ── Search ─────────────────────────────────────────────────────────────────────

class SearchResultCard(BaseModel):
    id: str
    title: str
    details: Optional[str] = ""
    priority: Optional[str] = "medium"
    labels: Optional[str] = ""
    board_id: str
    board_title: str
    column_title: str
    archived: bool = False


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
    template: Optional[str] = None  # "software" | "marketing" | "personal"


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


# ── Card Activity ──────────────────────────────────────────────────────────────

class CardActivityEntry(BaseModel):
    id: int
    card_id: str
    user_id: str
    username: str
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: str


# ── Notifications ──────────────────────────────────────────────────────────────

class NotificationItem(BaseModel):
    card_id: str
    card_title: str
    board_id: str
    board_title: str
    column_title: str
    due_date: str
    type: str  # "overdue" | "due_soon"


# ── Bulk Operations ────────────────────────────────────────────────────────────

class BulkArchiveRequest(BaseModel):
    card_ids: List[str]


class BulkUpdateRequest(BaseModel):
    card_ids: List[str]
    column_id: Optional[str] = None
    labels: Optional[str] = None


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
