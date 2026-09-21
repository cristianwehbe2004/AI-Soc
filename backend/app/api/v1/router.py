from fastapi import APIRouter

from app.api.v1.endpoints.api_keys import router as api_keys_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.events import router as events_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.incidents import router as incidents_router
from app.api.v1.endpoints.investigations import router as investigations_router
from app.api.v1.endpoints.mitre import router as mitre_router
from app.api.v1.endpoints.users import router as users_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, tags=["authentication"])
router.include_router(events_router, tags=["events"])
router.include_router(incidents_router, tags=["incidents"])
router.include_router(investigations_router, tags=["investigations"])
router.include_router(mitre_router, tags=["mitre"])
router.include_router(users_router, tags=["users"])
router.include_router(api_keys_router, tags=["api-keys"])
router.include_router(audit_router, tags=["audit"])
