from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    RESELLER = "RESELLER"


class ServiceProtocol(str, enum.Enum):
    XRAY_VLESS = "XRAY_VLESS"


class Reseller(Base):
    __tablename__ = "resellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    auth_username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship("User", back_populates="reseller")
    services: Mapped[list["Service"]] = relationship("Service", back_populates="reseller")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reseller_id: Mapped[int | None] = mapped_column(ForeignKey("resellers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    reseller: Mapped["Reseller | None"] = relationship("Reseller", back_populates="users")
    services: Mapped[list["Service"]] = relationship("Service", back_populates="user")


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("user_id", "protocol", name="uq_user_protocol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reseller_id: Mapped[int | None] = mapped_column(ForeignKey("resellers.id"), nullable=True)
    protocol: Mapped[ServiceProtocol] = mapped_column(Enum(ServiceProtocol), nullable=False, default=ServiceProtocol.XRAY_VLESS)
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="services")
    reseller: Mapped["Reseller | None"] = relationship("Reseller", back_populates="services")
    subscription_token: Mapped["SubscriptionToken | None"] = relationship(
        "SubscriptionToken", back_populates="service", uselist=False, cascade="all, delete-orphan"
    )


class SubscriptionToken(Base):
    __tablename__ = "subscription_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    service: Mapped["Service"] = relationship("Service", back_populates="subscription_token")
