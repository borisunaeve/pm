from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/hello")
def hello_world():
    return {"message": "Hello from FastAPI!"}
