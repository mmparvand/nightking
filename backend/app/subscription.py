from __future__ import annotations

from io import BytesIO
from urllib.parse import quote, urlencode

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from . import crud
from .config import get_settings, Settings
from .db import get_db
from .models import ServiceProtocol, SubscriptionToken


router = APIRouter(tags=["subscription"])


def _subscription_base_url(settings: Settings, token: str) -> str:
    encoded_token = quote(token, safe="")
    return f"{settings.subscription_scheme}://{settings.subscription_domain}:{settings.subscription_port}/sub/{encoded_token}"


def _build_vless_payload(sub_token: SubscriptionToken, settings: Settings) -> str:
    service = sub_token.service
    if not service:
        raise HTTPException(status_code=404, detail="Service not found for token")
    endpoint = service.endpoint or f"{settings.subscription_domain}:{settings.subscription_port}"
    if ":" not in endpoint:
        endpoint = f"{endpoint}:{settings.subscription_port}"
    friendly_name = quote(service.name or f"service-{service.id}")
    query = urlencode({"encryption": "none", "type": "tcp", "security": "tls", "sni": settings.subscription_domain})
    return f"vless://{sub_token.token}@{endpoint}?{query}#{friendly_name}"


@router.get("/sub/{token}", response_class=PlainTextResponse)
def get_subscription_payload(token: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> str:
    sub_token = crud.get_subscription_by_token(db, token)
    if not sub_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription token not found")
    if not sub_token.service or sub_token.service.protocol != ServiceProtocol.XRAY_VLESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported service protocol")
    return _build_vless_payload(sub_token, settings)


@router.get("/sub/{token}/qr")
def get_subscription_qr(token: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    sub_token = crud.get_subscription_by_token(db, token)
    if not sub_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription token not found")
    link = _subscription_base_url(settings, token)
    img = qrcode.make(link)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")
