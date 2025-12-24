from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .logging_config import configure_logging
from .auth import router as auth_router, user_store
from .schemas import Role

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting application", extra={"environment": settings.environment})
    try:
        user_store.add_user(settings.admin_username, settings.admin_password, Role(settings.admin_role))
    except ValueError:
        logger.warning("Invalid admin role provided; defaulting to ADMIN")
        user_store.add_user(settings.admin_username, settings.admin_password, Role.ADMIN)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    # Placeholder for real dependency checks (database, redis, etc.)
    return {"status": "ready"}


app.include_router(auth_router)
