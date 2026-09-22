from fastapi import APIRouter

# Router for health check endpoints.
router = APIRouter()


# Verify that the backend API is running.
@router.get("/")
def home():
    return {
        "status": "success",
        "message": "AI Query Resolution System API is running",
    }
