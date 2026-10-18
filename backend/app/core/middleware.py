from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import actor_context, request_id_context


from starlette.responses import JSONResponse
from app.db.redis import redis_client


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. IP Denylist enforcement (autonomous containment)
        client_ip = request.client.host if request.client else None
        if client_ip:
            try:
                blocked = await redis_client.get(f"ai_soc:denylist:ip:{client_ip}")
                if blocked:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Access denied: IP is temporarily blocked by SOC containment policy."},
                    )
            except Exception:
                pass  # Fall through gracefully if Redis is momentarily unreachable

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

