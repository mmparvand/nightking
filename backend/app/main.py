from __future__ import annotations

import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import get_settings
from .logging_config import configure_logging
from .auth import router as auth_router, user_store
from .schemas import Role
from .db import get_db, engine
from .models import Base, Reseller
from .api import router as api_router
from .subscription import router as subscription_router

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
    Base.metadata.create_all(bind=engine)
    try:
        user_store.add_user(settings.admin_username, settings.admin_password, Role(settings.admin_role))
    except ValueError:
        logger.warning("Invalid admin role provided; defaulting to ADMIN")
        user_store.add_user(settings.admin_username, settings.admin_password, Role.ADMIN)
    if settings.reseller_username and settings.reseller_password:
        try:
            user_store.add_user(settings.reseller_username, settings.reseller_password, Role.RESELLER)
        except ValueError:
            logger.warning("Reseller seed failed")
    # Ensure reseller mapping exists for seeded reseller
    from sqlalchemy.orm import Session

    with Session(bind=engine, future=True) as session:
        if settings.reseller_username:
            reseller = session.query(Reseller).filter(Reseller.auth_username == settings.reseller_username).first()
            if not reseller:
                session.add(Reseller(name="Seed Reseller", auth_username=settings.reseller_username))
                session.commit()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    # Placeholder for real dependency checks (database, redis, etc.)
    return {"status": "ready"}


app.include_router(auth_router)
app.include_router(api_router)
app.include_router(subscription_router)
