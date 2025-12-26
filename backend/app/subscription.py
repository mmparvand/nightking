from __future__ import annotations

from io import BytesIO
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session
import redis

from . import crud
from .config import get_settings, Settings
from .db import get_db
from .models import ServiceProtocol, SubscriptionToken


router = APIRouter(tags=["subscription"])

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis_client


def _subscription_base_url(settings: Settings, token: str) -> str:
    encoded_token = quote(token, safe="")
    return f"{settings.subscription_scheme}://{settings.subscription_domain}:{settings.subscription_port}/sub/{encoded_token}"


def _build_vless_payload(sub_token: SubscriptionToken, settings: Settings) -> str:
    service = sub_token.service
    if not service:
        raise HTTPException(status_code=404, detail="Service not found for token")
    nodes = service.service_nodes or []
    links = []
    if not nodes:
        nodes = [None]
    for sn in nodes:
        location_label = sn.node.location if sn else "default"
        endpoint = service.endpoint or f"{settings.subscription_domain}:{settings.xray_inbound_port}"
        if sn and sn.node and sn.node.ip_address:
            endpoint = f"{sn.node.ip_address}:{settings.xray_inbound_port}"
        if ":" not in endpoint:
            endpoint = f"{endpoint}:{settings.xray_inbound_port}"
        friendly_name = quote(f"{service.name or 'service'}-{location_label}")
        query = urlencode({"encryption": "none", "type": "tcp", "security": "tls", "sni": settings.subscription_domain})
        links.append(f"vless://{sub_token.token}@{endpoint}?{query}#{friendly_name}")
    return "\n".join(links)


@router.get("/sub/{token}", response_class=PlainTextResponse)
def get_subscription_payload(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> str:
    sub_token = crud.get_subscription_by_token(db, token)
    if not sub_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription token not found")
    if not sub_token.service or sub_token.service.protocol != ServiceProtocol.XRAY_VLESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported service protocol")
    service = sub_token.service
    now = datetime.now(timezone.utc)
    if service.expires_at and service.expires_at < now:
        return PlainTextResponse("SERVICE_EXPIRED", status_code=status.HTTP_403_FORBIDDEN)
    if not service.is_active:
        return PlainTextResponse("SERVICE_DISABLED", status_code=status.HTTP_403_FORBIDDEN)
    if service.traffic_limit_bytes and service.traffic_used_bytes >= service.traffic_limit_bytes:
        return PlainTextResponse("SERVICE_TRAFFIC_EXCEEDED", status_code=status.HTTP_403_FORBIDDEN)
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = None
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    payload = _build_vless_payload(sub_token, settings)
    # IP/concurrency limits (best-effort)
    r = get_redis()
    if r and service.ip_limit:
        key = f"svc:{service.id}:ips"
        if client_ip:
            r.sadd(key, client_ip)
        r.expire(key, settings.ip_limit_window_seconds)
        ip_count = r.scard(key)
        if ip_count and ip_count > service.ip_limit:
            return PlainTextResponse("SERVICE_IP_LIMIT", status_code=status.HTTP_403_FORBIDDEN)
    if r and service.concurrent_limit:
        c_key = f"svc:{service.id}:concurrent"
        current = r.get(c_key)
        current_val = int(current) if current else 0
        if current_val >= service.concurrent_limit:
            return PlainTextResponse("SERVICE_CONCURRENT_LIMIT", status_code=status.HTTP_403_FORBIDDEN)
        r.incr(c_key)
        r.expire(c_key, settings.concurrent_window_seconds)
    return payload


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
