import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.database import get_db_connection
from backend.models import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfile,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (request.username,))
    row = cursor.fetchone()
    conn.close()

    if not row or not verify_password(request.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(row["id"], row["username"])
    return TokenResponse(access_token=token, user_id=row["id"], username=row["username"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(request: RegisterRequest):
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (request.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Username already taken")

    user_id = f"user-{uuid.uuid4().hex[:12]}"
    cursor.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        (user_id, request.username, hash_password(request.password)),
    )

    # Create a default board for the new user
    board_id = f"board-{uuid.uuid4().hex[:12]}"
    cursor.execute(
        "INSERT INTO boards (id, user_id, title) VALUES (?, ?, ?)",
        (board_id, user_id, "My First Board"),
    )

    default_columns = [
        (f"col-{uuid.uuid4().hex[:8]}", board_id, "Backlog", 0),
        (f"col-{uuid.uuid4().hex[:8]}", board_id, "In Progress", 1),
        (f"col-{uuid.uuid4().hex[:8]}", board_id, "Done", 2),
    ]
    cursor.executemany(
        "INSERT INTO columns (id, board_id, title, [order]) VALUES (?, ?, ?, ?)",
        default_columns,
    )

    conn.commit()
    conn.close()

    token = create_access_token(user_id, request.username)
    return TokenResponse(access_token=token, user_id=user_id, username=request.username)


@router.get("/me", response_model=UserProfile)
def me(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, display_name, created_at FROM users WHERE id = ?", (current_user["sub"],))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfile(
        id=row["id"], username=row["username"],
        display_name=row["display_name"] or "",
        created_at=row["created_at"],
    )


@router.put("/me", response_model=UserProfile)
def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET display_name = ? WHERE id = ?",
        (request.display_name.strip(), current_user["sub"]),
    )
    conn.commit()
    cursor.execute("SELECT id, username, display_name, created_at FROM users WHERE id = ?", (current_user["sub"],))
    row = cursor.fetchone()
    conn.close()
    return UserProfile(
        id=row["id"], username=row["username"],
        display_name=row["display_name"] or "",
        created_at=row["created_at"],
    )


@router.put("/password")
def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["sub"],))
    row = cursor.fetchone()

    if not row or not verify_password(request.current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(request.new_password), current_user["sub"]),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}
