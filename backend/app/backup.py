from __future__ import annotations

import json
import os
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import shutil
import subprocess

from fastapi import HTTPException, status, UploadFile

from .config import Settings
from .models import AuditLog
from .db import get_db
from sqlalchemy.orm import Session


def _safe_join(base: Path, name: str) -> Path:
    candidate = (base / name).resolve()
    if base not in candidate.parents and candidate != base:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    return candidate


def _current_revision() -> str:
    # Minimal placeholder; in real deployment consult alembic_version table
    return "head"


def create_backup(settings: Settings, db_session: Session, actor: str) -> dict[str, Any]:
    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_id = uuid.uuid4().hex
    work_dir = backup_dir / backup_id
    work_dir.mkdir(parents=True, exist_ok=True)

    db_dump_path = work_dir / "db.dump"
    try:
        subprocess.run(
            ["pg_dump", "-Fc", settings.database_url, "-f", str(db_dump_path)],
            check=True,
            capture_output=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pg_dump failed: {exc}") from exc

    settings_json = {
        "app_name": settings.app_name,
        "subscription_domain": settings.subscription_domain,
        "subscription_port": settings.subscription_port,
        "subscription_scheme": settings.subscription_scheme,
    }
    (work_dir / "settings.json").write_text(json.dumps(settings_json))
    version_json = {
        "app_version": settings.app_version,
        "alembic_revision": _current_revision(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (work_dir / "version.json").write_text(json.dumps(version_json))

    archive_path = backup_dir / f"{backup_id}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        for filename in ["db.dump", "settings.json", "version.json"]:
            tar.add(work_dir / filename, arcname=filename)

    shutil.rmtree(work_dir, ignore_errors=True)
    _log(db_session, actor, "backup_create", str(archive_path))
    return {"id": backup_id, "path": str(archive_path), "created_at": version_json["created_at"]}


def list_backups(settings: Settings) -> list[dict[str, Any]]:
    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups: list[dict[str, Any]] = []
    for f in backup_dir.glob("*.tar.gz"):
        meta = {"id": f.stem, "path": str(f), "created_at": None}
        try:
            with tarfile.open(f, "r:gz") as tar:
                version = tar.extractfile("version.json")
                if version:
                    meta["created_at"] = json.loads(version.read().decode()).get("created_at")
        except Exception:
            pass
        backups.append(meta)
    return backups


def download_backup(settings: Settings, backup_id: str) -> Path:
    backup_dir = Path(settings.backup_dir)
    path = _safe_join(backup_dir, f"{backup_id}.tar.gz")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    return path


def upload_backup(settings: Settings, file: UploadFile, actor: str, db_session: Session) -> dict[str, Any]:
    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_id = uuid.uuid4().hex
    dest = backup_dir / f"{backup_id}.tar.gz"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    _validate_backup(dest)
    _log(db_session, actor, "backup_upload", str(dest))
    return {"id": backup_id, "path": str(dest)}


def restore_backup(settings: Settings, backup_id: str, db_session: Session, actor: str) -> str:
    archive = download_backup(settings, backup_id)
    _validate_backup(archive, expect_revision=_current_revision())
    extract_dir = Path(settings.backup_dir) / f"restore_{backup_id}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        _safe_extract(tar, extract_dir)
    db_dump = extract_dir / "db.dump"
    try:
        subprocess.run(["pg_restore", "-d", settings.database_url, str(db_dump)], check=True, capture_output=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"pg_restore failed: {exc}") from exc
    _log(db_session, actor, "backup_restore", backup_id)
    shutil.rmtree(extract_dir, ignore_errors=True)
    return "restored"


def _safe_extract(tar: tarfile.TarFile, path: Path):
    for member in tar.getmembers():
        target = (path / member.name).resolve()
        if path not in target.parents and target != path:
            raise HTTPException(status_code=400, detail="Unsafe archive path")
    tar.extractall(path)


def _validate_backup(path: Path, expect_revision: str | None = None) -> None:
    try:
        with tarfile.open(path, "r:gz") as tar:
            names = tar.getnames()
            if "db.dump" not in names or "version.json" not in names:
                raise HTTPException(status_code=400, detail="Invalid backup contents")
            version = tar.extractfile("version.json")
            if version:
                data = json.loads(version.read().decode())
                if expect_revision and data.get("alembic_revision") not in (None, expect_revision):
                    raise HTTPException(status_code=400, detail="Schema revision mismatch")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid backup: {exc}") from exc


def _log(db: Session, actor: str, action: str, detail: str) -> None:
    db.add(AuditLog(actor=actor, action=action, detail=detail))
    db.commit()
