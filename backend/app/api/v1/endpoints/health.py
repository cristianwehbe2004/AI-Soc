from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter()


def get_health_service() -> HealthService:
    return HealthService()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    health_service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    health = await health_service.check()
    if health.status != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health.model_dump(),
        )
    return health
