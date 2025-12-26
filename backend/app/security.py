from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_secret_key() -> str:
    return get_settings().secret_key


def get_algorithm() -> str:
    return get_settings().jwt_algorithm


def get_access_token_expires_minutes() -> int:
    return get_settings().access_token_expires_minutes


def create_access_token(subject: str, role: str) -> str:
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": dt.datetime.utcnow(),
        "exp": dt.datetime.utcnow() + dt.timedelta(minutes=get_access_token_expires_minutes()),
    }
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=get_algorithm())
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[get_algorithm()])
        return payload
    except JWTError:
        return None
