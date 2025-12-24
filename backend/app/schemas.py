from __future__ import annotations

from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class Role(str, Enum):
    ADMIN = "ADMIN"
    RESELLER = "RESELLER"

class ServiceProtocol(str, Enum):
    XRAY_VLESS = "XRAY_VLESS"


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    role_tab: Role


class UserPublic(BaseModel):
    username: str
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class Message(BaseModel):
    detail: str


# Domain models
class UserBase(BaseModel):
    email: str
    full_name: str
    reseller_id: Optional[int] = None

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    email: str
    full_name: str


class UserUpdate(BaseModel):
    email: str
    full_name: str

    class Config:
        orm_mode = True


class UserOut(UserBase):
    id: int


class PaginatedUsers(BaseModel):
    items: list[UserOut]
    limit: int
    offset: int


class ServiceBase(BaseModel):
    name: str
    user_id: int
    reseller_id: Optional[int] = None
    protocol: ServiceProtocol = ServiceProtocol.XRAY_VLESS
    endpoint: Optional[str] = None
    traffic_limit_bytes: Optional[int] = None
    traffic_used_bytes: Optional[int] = None
    expires_at: Optional[datetime] = None
    ip_limit: Optional[int] = None
    concurrent_limit: Optional[int] = None
    is_active: Optional[bool] = True

    class Config:
        orm_mode = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str
    protocol: ServiceProtocol = ServiceProtocol.XRAY_VLESS
    endpoint: Optional[str] = None
    traffic_limit_bytes: Optional[int] = None
    traffic_used_bytes: Optional[int] = None
    expires_at: Optional[str] = None
    ip_limit: Optional[int] = None
    concurrent_limit: Optional[int] = None
    is_active: Optional[bool] = True

    class Config:
        orm_mode = True


class SubscriptionTokenOut(BaseModel):
    id: int
    token: str
    service_id: int

    class Config:
        orm_mode = True


class ServiceOut(ServiceBase):
    id: int
    subscription_token: Optional[SubscriptionTokenOut] = None


class PaginatedServices(BaseModel):
    items: list[ServiceOut]
    limit: int
    offset: int


class XrayRenderResponse(BaseModel):
    generated_at: str
    config: dict


class XrayApplyResponse(BaseModel):
    snapshot_id: int
    applied_at: str
    status: str
    healthy: bool
    error: Optional[str] = None


class XrayStatus(BaseModel):
    healthy: bool
    last_apply_status: Optional[str] = None
    last_apply_error: Optional[str] = None
    last_applied_at: Optional[str] = None
