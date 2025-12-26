from __future__ import annotations

import json
import os
import subprocess
import time
import hmac
import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
import ipaddress

NODE_TOKEN = os.environ.get("NODE_TOKEN", "change-me")
CONFIG_PATH = Path(os.environ.get("NODE_CONFIG_PATH", "/etc/xray/config.json"))
RELOAD_COMMAND = os.environ.get("NODE_RELOAD_COMMAND", "")
ALLOWED_IPS = [ip.strip() for ip in os.environ.get("NODE_ALLOWED_IPS", "").split(",") if ip.strip()]
NONCE_CACHE: dict[str, float] = {}
NONCE_TTL = 300

app = FastAPI(title="Node Agent")


def _validate_token(request: Request) -> None:
    header = request.headers.get("X-Node-Token")
    if not header or header != NODE_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


def _validate_ip(request: Request) -> None:
    if not ALLOWED_IPS:
        return
    client = request.client.host if request.client else None
    if not client:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="IP unknown")
    try:
        candidate = ipaddress.ip_address(client)
        for net in ALLOWED_IPS:
            if candidate in ipaddress.ip_network(net, strict=False):
                return
    except ValueError:
        pass
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="IP not allowed")


def _validate_signature(request: Request, body: bytes) -> None:
    ts = request.headers.get("X-NK-Timestamp")
    nonce = request.headers.get("X-NK-Nonce")
    sig = request.headers.get("X-NK-Signature")
    if not ts or not nonce or not sig:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature headers")
    try:
        ts_int = int(ts)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad timestamp")
    if abs(time.time() - ts_int) > NONCE_TTL:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Timestamp too old")
    if nonce in NONCE_CACHE and time.time() - NONCE_CACHE[nonce] < NONCE_TTL:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Replay detected")
    expected = hmac.new(NODE_TOKEN.encode(), body + ts.encode() + nonce.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad signature")
    NONCE_CACHE[nonce] = time.time()


def _write_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def _reload() -> str:
    if not RELOAD_COMMAND:
        return "reload command not set"
    proc = subprocess.run(RELOAD_COMMAND, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout or "reload failed")
    return proc.stdout or "reloaded"


@app.get("/agent/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/agent/status")
async def status_endpoint(request: Request) -> dict[str, str]:
    _validate_token(request)
    _validate_ip(request)
    return {"status": "ready"}


@app.post("/agent/config/apply")
async def apply_config(payload: dict[str, Any], request: Request) -> dict[str, str]:
    _validate_token(request)
    _validate_ip(request)
    if "config" not in payload or not isinstance(payload["config"], dict):
        raise HTTPException(status_code=400, detail="config missing")
    body = json.dumps(payload).encode()
    _validate_signature(request, body)
    _write_config(payload["config"])
    msg = _reload()
    return {"status": "applied", "reload": msg}
