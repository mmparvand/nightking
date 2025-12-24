from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from .auth import get_current_user
from .schemas import Role, UserPublic


def require_role(role: Role):
    def _dependency(user: Annotated[UserPublic, Depends(get_current_user)]) -> UserPublic:
        if user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dependency
