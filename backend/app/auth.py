from __future__ import annotations

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from . import crud, schemas
from .db import get_db
from .security import create_access_token, decode_token, get_password_hash, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class InMemoryUserStore:
    def __init__(self) -> None:
        self._users: Dict[str, tuple[str, schemas.Role]] = {}

    def add_user(self, username: str, password: str, role: schemas.Role) -> None:
        password_hash = get_password_hash(password)
        self._users[username] = (password_hash, role)
        logger.info("Seeded user", extra={"username": username, "role": role})

    def authenticate(self, username: str, password: str, expected_role: schemas.Role) -> Optional[schemas.UserPublic]:
        if username not in self._users:
            return None
        stored_hash, role = self._users[username]
        if role != expected_role:
            return None
        if not verify_password(password, stored_hash):
            return None
        return schemas.UserPublic(username=username, role=role)

    def get_user(self, username: str) -> Optional[schemas.UserPublic]:
        if username not in self._users:
            return None
        _, role = self._users[username]
        return schemas.UserPublic(username=username, role=role)


user_store = InMemoryUserStore()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> schemas.UserPublic:
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    if not payload or "sub" not in payload or "role" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = user_store.get_user(payload["sub"])
    if not user or user.role != schemas.Role(payload["role"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or role mismatch")
    if user.role == schemas.Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, user.username)
        if not reseller:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Reseller not provisioned")
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)) -> schemas.TokenResponse:
    user = user_store.authenticate(payload.username, payload.password, payload.role_tab)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or role")
    if user.role == schemas.Role.RESELLER and not crud.get_reseller_by_username(db, user.username):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reseller not provisioned")
    token = create_access_token(subject=user.username, role=user.role)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return schemas.TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=schemas.UserPublic)
def read_current_user(current_user: schemas.UserPublic = Depends(get_current_user)) -> schemas.UserPublic:
    return current_user
