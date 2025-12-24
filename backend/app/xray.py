from __future__ import annotations

import json
import logging
import socket
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import get_current_user
from .config import Settings, get_settings
from .crud import ensure_subscription_token
from .db import get_db
from .models import Service, ServiceProtocol, XrayConfigSnapshot
from .schemas import Role, UserPublic, XrayApplyResponse, XrayRenderResponse, XrayStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/xray", tags=["xray"])


def _collect_vless_clients(db: Session) -> list[dict]:
    stmt = (
        select(Service)
        .where(Service.protocol == ServiceProtocol.XRAY_VLESS)
        .options(selectinload(Service.subscription_token), selectinload(Service.user))
    )
    services = db.scalars(stmt).all()
    clients: list[dict] = []
    for service in services:
        token = service.subscription_token or ensure_subscription_token(db, service)
        user = service.user
        if not user:
            continue
        client_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, token.token))
        clients.append(
            {
                "id": client_uuid,
                "email": f"{user.email}:{service.id}",
            }
        )
    return clients


def _render_xray_config(db: Session, settings: Settings) -> dict:
    clients = _collect_vless_clients(db)
    inbound_port = settings.xray_inbound_port or settings.subscription_port
    config = {
        "log": {"loglevel": "info"},
        "inbounds": [
            {
                "tag": "vless-tls",
                "listen": "0.0.0.0",
                "port": inbound_port,
                "protocol": "vless",
                "settings": {"clients": clients, "decryption": "none"},
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {"serverName": settings.subscription_domain},
                },
            }
        ],
        "outbounds": [{"protocol": "freedom", "tag": "direct"}],
        "api": {"services": ["HandlerService", "StatsService", "LoggerService"], "tag": "api"},
        "policy": {"system": {"statsInboundUplink": True, "statsInboundDownlink": True}},
        "stats": {},
    }
    try:
        json.loads(json.dumps(config))
    except (TypeError, ValueError) as exc:
        logger.error("Rendered Xray config is not valid JSON", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid Xray config")
    return config


def _write_snapshot(db: Session, config_json: str, status_text: str, error_text: str | None) -> XrayConfigSnapshot:
    snapshot = XrayConfigSnapshot(
        config_json=config_json,
        applied=True,
        apply_status=status_text,
        apply_error=error_text[:255] if error_text else None,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _check_xray_health(settings: Settings) -> bool:
    try:
        with socket.create_connection((settings.xray_status_host, settings.subscription_port), timeout=2):
            return True
    except OSError:
        return False


@router.post("/render", response_model=XrayRenderResponse)
def render_config(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: UserPublic = Depends(get_current_user),
) -> XrayRenderResponse:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    config = _render_xray_config(db, settings)
    logger.info("Rendered Xray config", extra={"services": len(config.get("inbounds", []))})
    return XrayRenderResponse(generated_at=datetime.now(timezone.utc).isoformat(), config=config)


@router.post("/apply", response_model=XrayApplyResponse)
def apply_config(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: UserPublic = Depends(get_current_user),
) -> XrayApplyResponse:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    config = _render_xray_config(db, settings)
    serialized = json.dumps(config, indent=2)

    config_path = Path(settings.xray_config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(serialized)

    reload_error = None
    status_text = "written"
    if settings.xray_reload_command:
        proc = subprocess.run(
            settings.xray_reload_command,
            shell=True,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            status_text = "reload_failed"
            reload_error = (proc.stderr or proc.stdout or "Reload command failed").strip()
            logger.error(
                "Xray reload failed",
                extra={"returncode": proc.returncode, "stderr": proc.stderr, "stdout": proc.stdout},
            )
        else:
            status_text = "applied"
            logger.info("Xray reload succeeded", extra={"output": proc.stdout})
    else:
        logger.info("Xray reload command not configured; config written only")

    snapshot = _write_snapshot(db, serialized, status_text, reload_error)
    healthy = _check_xray_health(settings)

    return XrayApplyResponse(
        snapshot_id=snapshot.id,
        applied_at=snapshot.created_at.isoformat(),
        status=status_text,
        healthy=healthy,
        error=reload_error,
    )


@router.get("/status", response_model=XrayStatus)
def xray_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: UserPublic = Depends(get_current_user),
) -> XrayStatus:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    stmt = select(XrayConfigSnapshot).order_by(XrayConfigSnapshot.created_at.desc())
    last_snapshot = db.scalars(stmt).first()
    healthy = _check_xray_health(settings)
    return XrayStatus(
        healthy=healthy,
        last_apply_status=last_snapshot.apply_status if last_snapshot else None,
        last_apply_error=last_snapshot.apply_error if last_snapshot else None,
        last_applied_at=last_snapshot.created_at.isoformat() if last_snapshot else None,
    )
