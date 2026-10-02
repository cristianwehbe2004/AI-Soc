from pydantic import BaseModel


class RealtimeTicketResponse(BaseModel):
    ticket: str
    expires_in: int