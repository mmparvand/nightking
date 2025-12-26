from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status

NODE_TOKEN = os.environ.get("NODE_TOKEN", "change-me")
CONFIG_PATH = Path(os.environ.get("NODE_CONFIG_PATH", "/etc/xray/config.json"))
RELOAD_COMMAND = os.environ.get("NODE_RELOAD_COMMAND", "")

app = FastAPI(title="Node Agent")


def _validate_token(request: Request) -> None:
    header = request.headers.get("X-Node-Token")
    if not header or header != NODE_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


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
    return {"status": "ready"}


@app.post("/agent/config/apply")
async def apply_config(payload: dict[str, Any], request: Request) -> dict[str, str]:
    _validate_token(request)
    if "config" not in payload or not isinstance(payload["config"], dict):
        raise HTTPException(status_code=400, detail="config missing")
    _write_config(payload["config"])
    msg = _reload()
    return {"status": "applied", "reload": msg}
