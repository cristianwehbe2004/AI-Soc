from datetime import datetime

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    events_total: int
    incidents_open: int
    alerts_active: int
    investigations_active: int
    model_status: str
    model_version: str | None
    as_of: datetime