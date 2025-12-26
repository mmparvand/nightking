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
2) Build and start the stack:
   ```bash
   docker compose up --build
   ```
3) Access services:
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000 (health at `/health`, readiness at `/ready`)
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
- API base URL is read from `VITE_API_BASE_URL` (defaults to `http://localhost:8000`).

Local development:
```bash
cd frontend
npm install
npm run dev -- --host --port 5173
```
The landing page performs a `/health` check against the backend and displays connectivity status.

## Infrastructure
The `infra/` directory is reserved for future IaC, operational scripts, and deployment manifests beyond the local Docker Compose stack.

## Next steps
- Add authentication and RBAC for admin access.
- Implement VPN gateway/device management workflows.
- Wire readiness checks to real dependencies (PostgreSQL, Redis, background workers).
