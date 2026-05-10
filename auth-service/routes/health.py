from fastapi import APIRouter
from config import get_settings
from schemas import HealthResponse

settings = get_settings()
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENV,
    )
