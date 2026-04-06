from fastapi import APIRouter, Depends

from backend.auth import get_current_user

router = APIRouter(prefix="/api/templates", tags=["templates"])

# Built-in board templates
_TEMPLATES = [
    {
        "id": "software",
        "name": "Software Development",
        "description": "Agile workflow with backlog, in-progress, review, testing and done.",
        "color": "#209dd7",
        "columns": ["Backlog", "In Progress", "In Review", "Testing", "Done"],
    },
    {
        "id": "marketing",
        "name": "Marketing Campaign",
        "description": "Content pipeline from ideas through production to publishing.",
        "color": "#ecad0a",
        "columns": ["Ideas", "Planning", "In Production", "Review", "Published"],
    },
    {
        "id": "personal",
        "name": "Personal Tasks",
        "description": "Simple to-do / doing / done board for personal productivity.",
        "color": "#753991",
        "columns": ["To Do", "Doing", "Done"],
    },
    {
        "id": "bug_tracker",
        "name": "Bug Tracker",
        "description": "Track issues from triage through fixing to verification.",
        "color": "#e55a5a",
        "columns": ["Reported", "Triaged", "In Progress", "In Review", "Verified"],
    },
    {
        "id": "hiring",
        "name": "Hiring Pipeline",
        "description": "Manage candidates from application to offer.",
        "color": "#2ecc71",
        "columns": ["Applied", "Phone Screen", "Interview", "Offer", "Hired"],
    },
]


@router.get("")
def list_templates(current_user: dict = Depends(get_current_user)):
    return _TEMPLATES
