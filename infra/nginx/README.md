# Nginx Gateway

Nginx exposes the browser application and API through one origin:

- `/api/` is forwarded to FastAPI.
- Every other path is forwarded to Next.js.
- Forwarded host, protocol, request IP, and request ID headers are preserved.

Docker Compose exposes the gateway at `http://localhost:8080`. Production should
terminate HTTPS at this gateway or an upstream load balancer, set
`AUTH_COOKIE_SECURE=true`, and avoid exposing the backend and frontend containers
directly.
