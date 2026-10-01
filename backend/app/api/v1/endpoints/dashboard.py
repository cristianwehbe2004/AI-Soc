from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.dashboard import DashboardSummaryResponse
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    dependencies=[Depends(require_permission(Permission.SOC_READ))],
)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_db_session),
) -> DashboardSummaryResponse:
    return await DashboardService(session).summary()