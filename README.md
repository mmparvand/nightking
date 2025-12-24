# Nightking VPN Panel Monorepo

A production-ready skeleton for a self-hosted VPN management panel. The stack includes a FastAPI backend, React + Vite + Tailwind frontend, PostgreSQL, Redis, and Docker Compose orchestration.

## Repository structure
```
/
  backend/        # FastAPI service
  frontend/       # React + Vite + Tailwind client
  infra/          # Infra and ops stubs
  docker-compose.yml
  .env.example
```

## Prerequisites
- Docker and Docker Compose
- Node.js 20+ and npm (for local frontend development)
- Python 3.12+ (for local backend development)

## Quickstart (Docker)
1) Copy environment defaults and adjust as needed:
   ```bash
   cp .env.example .env
   ```
2) Set initial credentials (used to seed ADMIN and RESELLER accounts):
   ```bash
   # .env
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=changeme
   RESELLER_USERNAME=reseller
   RESELLER_PASSWORD=changeme
   ```
3) Build and start the stack:
   ```bash
   docker compose up --build
   ```
4) Access services:
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000 (health at `/health`, readiness at `/ready`)
   - Subscription link base: https://localhost:2053/sub/{token}
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

Stop services with `docker compose down`. Persistent volumes are defined for Postgres and Redis.

## Backend (FastAPI)
- Entrypoint: `backend/app/main.py`
- Logging: structured console logging via `backend/app/logging_config.py` honoring `LOG_LEVEL`.
- Configuration: `backend/app/config.py` uses environment variables (see `.env.example`).
- Health endpoints:
  - `GET /health` → `{ "status": "ok" }`
  - `GET /ready` → `{ "status": "ready" }` (placeholder for dependency checks)
- Subscription endpoints (Marzban-compatible):
  - `GET /sub/{token}` → returns VLESS subscription payload (text)
  - `GET /sub/{token}/qr` → returns a PNG QR for the subscription link
- Auth endpoints:
  - `POST /auth/login` → issues JWT, sets HttpOnly cookie, validates role tab (`ADMIN` | `RESELLER`)
  - `GET /auth/me` → returns authenticated user/role
- Roles: `ADMIN` and `RESELLER`; the initial admin user is seeded from env vars.
- Database: PostgreSQL via SQLAlchemy + Alembic; models include Users, Resellers, Services, SubscriptionTokens (Xray VLESS).
- API CRUD:
  - `/api/users` (list/create) with pagination via `limit/offset`
  - `/api/users/{id}` (read/update/delete)
  - `/api/services` (list/create) with subscription token auto-generation
  - `/api/services/{id}` (read/update/delete)
  - `/api/services/{id}/token` (ensure/return stable token)
- Reseller scope: reseller logins are restricted to their own users/services.
- Subscription links stay stable and match `https://<domain>:2053/sub/<token>`; configure via `SUBSCRIPTION_DOMAIN`, `SUBSCRIPTION_PORT`, and `SUBSCRIPTION_SCHEME`.

Local development:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend (React + Vite + Tailwind)
- Entrypoint: `frontend/src/App.tsx`
- Tailwind is configured via `tailwind.config.ts` and `postcss.config.js`.
- API base URL is read from `VITE_API_BASE_URL` (defaults to `http://localhost:8000`). Subscription link base is configurable via `VITE_SUBSCRIPTION_DOMAIN`, `VITE_SUBSCRIPTION_PORT`, and `VITE_SUBSCRIPTION_SCHEME`.
- Routing (React Router):
  - `/login` → tabbed Admin/Reseller login; uses HttpOnly cookie-based JWT
  - `/admin/dashboard` and `/reseller/dashboard` → protected routes that call `/auth/me`
  - Admin/reseller dashboards list Services, allow creating new ones, and display subscription tokens with a copy-to-clipboard link that follows `https://<domain>:2053/sub/<token>`.

Local development:
```bash
cd frontend
npm install
npm run dev -- --host --port 5173
```
The login page performs a `/health` check against the backend and displays connectivity status. HttpOnly cookies are preferred for JWT storage; storing tokens in JavaScript-accessible storage increases XSS risk.

## Testing
Run backend tests inside Docker (pytest is installed in the backend image):
```bash
docker compose exec backend pytest
```

## Infrastructure
The `infra/` directory is reserved for future IaC, operational scripts, and deployment manifests beyond the local Docker Compose stack.

## Next steps
- Add authentication and RBAC for admin access.
- Implement VPN gateway/device management workflows.
- Wire readiness checks to real dependencies (PostgreSQL, Redis, background workers).
