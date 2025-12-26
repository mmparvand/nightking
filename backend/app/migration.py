from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ServiceProtocol, User
from . import crud


def preview_json(file_bytes: bytes) -> dict[str, Any]:
    try:
        data = json.loads(file_bytes.decode())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    users = data.get("users", [])
    services = data.get("services", [])
    tokens = data.get("tokens", [])
    return {"users": len(users), "services": len(services), "tokens": len(tokens)}


def run_json_import(db: Session, file_bytes: bytes) -> dict[str, Any]:
    data = json.loads(file_bytes.decode())
    created_users = 0
    created_services = 0
    skipped_tokens = 0
    users_map: dict[str, int] = {}
    for u in data.get("users", []):
        email = u.get("email")
        full_name = u.get("full_name") or email
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            users_map[email] = existing.id
            continue
        user = crud.create_user(db, email=email, full_name=full_name, reseller_id=None)
        users_map[email] = user.id
        created_users += 1
    for svc in data.get("services", []):
        email = svc.get("user_email")
        user_id = users_map.get(email)
        if not user_id:
            continue
        token_val = svc.get("token")
        if token_val and crud.get_subscription_by_token(db, token_val):
            skipped_tokens += 1
            continue
        service = crud.create_service(
            db,
            name=svc.get("name") or "Imported",
            user_id=user_id,
            reseller_id=None,
            protocol=ServiceProtocol.XRAY_VLESS,
            endpoint=svc.get("endpoint"),
            traffic_limit_bytes=svc.get("traffic_limit_bytes"),
            expires_at=svc.get("expires_at"),
            ip_limit=svc.get("ip_limit"),
            concurrent_limit=svc.get("concurrent_limit"),
            is_active=svc.get("is_active", True),
        )
        created_services += 1
        if token_val:
            try:
                crud.ensure_subscription_token(db, service)
                service.subscription_token.token = token_val  # type: ignore
                db.commit()
            except Exception:
                skipped_tokens += 1
    return {"created_users": created_users, "created_services": created_services, "skipped_tokens": skipped_tokens}


def preview_db(connection_url: str) -> dict[str, Any]:
    # Stub: real implementation would query Marzban DB; here we fail gracefully
    raise HTTPException(status_code=400, detail="DB preview not supported in this environment; use JSON import")


def run_db_import(connection_url: str) -> dict[str, Any]:
    raise HTTPException(status_code=400, detail="DB import not supported in this environment; export JSON instead")
