from fastapi import APIRouter

from app.api.v1.endpoints.events import router as events_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.incidents import router as incidents_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(events_router, tags=["events"])
router.include_router(incidents_router, tags=["incidents"])
