from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import actor_context, request_id_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", "")[:128] or str(uuid.uuid4())
        request.state.request_id = request_id
        request_token = request_id_context.set(request_id)
        actor_token = actor_context.set(None)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            actor_context.reset(actor_token)
            request_id_context.reset(request_token)
