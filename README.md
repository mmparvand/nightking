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
   - Xray inbound (local testing): tls VLESS on port 8443
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
- Service limits:
  - Fields include traffic_limit_bytes/traffic_used_bytes, expires_at, ip_limit, concurrent_limit, is_active.
  - `/sub/{token}` rejects expired/disabled/traffic-exceeded services and applies best-effort IP/concurrent windows via Redis.
  - Admin endpoint `/api/services/{id}/usage` lets admins/resellers adjust usage manually; traffic collector stub defined for future agent integration.
- Reseller scope: reseller logins are restricted to their own users/services.
- Subscription links stay stable and match `https://<domain>:2053/sub/<token>`; configure via `SUBSCRIPTION_DOMAIN`, `SUBSCRIPTION_PORT`, and `SUBSCRIPTION_SCHEME`.
- Xray config management:
  - `POST /xray/render` → render xray-core JSON config from DB services (ADMIN only)
  - `POST /xray/apply` → write config to the shared volume, optionally reload xray (ADMIN only)
  - `GET /xray/status` → report xray TCP reachability and last apply result (ADMIN only)
  - Configure paths/ports via `XRAY_CONFIG_PATH`, `XRAY_INBOUND_PORT`, `XRAY_STATUS_HOST`, and optional `XRAY_RELOAD_COMMAND` (e.g., `docker compose exec xray kill -HUP 1`).
- Reseller business system:
  - Admin: manage plans, credit/debit wallets, view reports, and handle support tickets.
  - Reseller: view wallet/plan/report, buy/renew plan from wallet, create tickets, and enforce quotas on users/services.
- Backup & restore (admin only):
  - `POST /api/backups/create`, `GET /api/backups`, `GET /api/backups/{id}/download`, `POST /api/backups/{id}/restore` (requires `{"confirm": true}`), `POST /api/backups/upload`.
  - Backups store `db.dump`, `settings.json` (non-secret), and `version.json` inside `.tar.gz` under `BACKUP_DIR`.
- Marzban migration wizard (admin only):
  - `POST /api/migration/marzban/preview` and `POST /api/migration/marzban/run` for JSON imports (DB import rejected with guidance). Tokens are preserved so `/sub/{token}` keeps working.
- Multi-node (locations) support:
  - Models for Nodes and ServiceNode mapping; services can target multiple nodes/locations.
  - Endpoints: `/api/nodes` CRUD, `/api/nodes/{id}/enable|disable|apply-config|status`, `/api/services/{id}/nodes`.
  - `/sub/{token}` now emits one VLESS link per node/location (labels appended) without changing the base token/link format.

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
- Admin dashboard adds “Render config”/“Apply config” actions for xray; status and last apply info are shown inline.
- Service forms expose limit fields (traffic, expiry, IP/concurrent caps, active flag) and display current usage/status.
- Reseller dashboard surfaces wallet/plan info and allows plan purchase; admin dashboard lists plans.
- Admin dashboard includes Backup and Marzban migration widgets (JSON upload).
- Admin dashboard includes a Nodes section (list/add) and simple service-to-node assignment helpers.
- Security hardening:
  - Optional IP allowlist for node agents via `NODE_AGENT_ALLOWED_IPS`.
  - HMAC-signed master→node apply-config with timestamp/nonce replay protection.
  - Redis-backed rate limits for `/auth/login` and `/sub/*`.
  - Security headers (CSP, X-Frame-Options, Referrer-Policy, X-Content-Type-Options); adjust CSP for custom frontends if needed.

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
Backups in Docker (example):
```bash
curl -X POST http://localhost:8000/api/backups/create
```

## Multi-node architecture (text)
- Master panel: FastAPI + DB manages services, tokens, nodes, and renders configs.
- Nodes: lightweight agents apply configs sent by master and run xray; authenticated via per-node tokens.
- Services map to one or more nodes (locations); subscription links include a line per node so clients can select a location.

## Install scripts
- Master: `scripts/master-install.sh` (idempotent) installs Docker/Compose, clones repo, and runs `docker compose up -d`.
- Node: `scripts/node-install.sh` installs Docker/Compose, spins up the node agent + xray, and prompts for master URL, token, name, and location to register.

## Infrastructure
The `infra/` directory is reserved for future IaC, operational scripts, and deployment manifests beyond the local Docker Compose stack.

## Next steps
- Add authentication and RBAC for admin access.
- Implement VPN gateway/device management workflows.
- Wire readiness checks to real dependencies (PostgreSQL, Redis, background workers).
