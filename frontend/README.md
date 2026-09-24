# AI-SOC Frontend

Next.js App Router foundation for the AI-SOC analyst console.

## Local Development

```bash
cp .env.example .env.local
npm ci
npm run dev
```

The browser application runs at `http://localhost:3000` and uses relative
`/api/v1` requests. Next.js proxies these requests to FastAPI during direct local
development. Docker Compose also provides the same-origin Nginx gateway at
`http://localhost:8080`.

## Authentication

- Access tokens exist only in application memory.
- Refresh tokens are backend-owned HttpOnly cookies.
- Page reloads restore the session through `POST /auth/refresh`.
- Protected API calls retry once after a coordinated refresh.
- `401`, `403`, and `429` remain distinct UI states.
- Frontend role checks improve navigation, but FastAPI remains authoritative.

## API Contract

`openapi/openapi.json` is exported from FastAPI and
`src/lib/api/schema.d.ts` is generated with `openapi-typescript`.

```bash
npm run api:generate
npm run api:check
```

To refresh the snapshot while Docker Compose is running:

```bash
docker compose -f ../infra/docker-compose.yml exec -T backend \
  python scripts/export_openapi.py - > openapi/openapi.json
npm run api:generate
```

## Verification

```bash
npm run lint
npm run typecheck
npm run test:run
npm run test:e2e
npm run build
```

The credential-free Playwright smoke test always runs. The real-stack
authentication flow additionally requires `E2E_EMAIL` and `E2E_PASSWORD` for a
CLI-created administrator.
