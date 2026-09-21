# Authentication and Authorization

## Browser contract

Human users authenticate with `POST /api/v1/auth/login` using OAuth2 form fields.
The `username` field contains the user's email address. The response contains a
15-minute bearer access token; the rotating refresh token is sent only as an
HttpOnly cookie scoped to `/api/v1/auth`.

The frontend must keep access tokens in memory, send them in the `Authorization`
header, and call `POST /api/v1/auth/refresh` with credentials after a page reload.
It must never put access or refresh tokens in local storage.

Authentication failures return `401`, insufficient permissions return `403`, and
login throttling returns `429`. All responses include `X-Request-ID`.

## Routes

- `POST /api/v1/auth/login`: public login
- `POST /api/v1/auth/refresh`: rotate the refresh session
- `POST /api/v1/auth/logout`: revoke the refresh-session family
- `GET /api/v1/auth/me`: current user
- `POST /api/v1/auth/change-password`: update password and revoke every session
- `/api/v1/users`: administrator user management
- `/api/v1/api-keys`: administrator service-key management
- `GET /api/v1/audit-logs`: administrator audit history

Event ingestion uses `X-API-Key` with the `events:write` scope. Service keys are
not accepted by human-facing routes.

## Local bootstrap

After migrations are applied, create the first administrator interactively:

```bash
python scripts/create_admin.py --email admin@example.com --full-name "SOC Admin"
```

For Docker Compose, run the same command with `docker compose exec backend`.

## Deployment contract

Development permits credentialed requests only from configured `CORS_ORIGINS`,
which defaults to `http://localhost:3000`. Production will route the frontend and
`/api` through the same HTTPS Nginx origin, set `AUTH_COOKIE_SECURE=true`, and use
a randomly generated `SECRET_KEY` of at least 32 characters.
