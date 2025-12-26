from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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
    traffic_limit_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traffic_used_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    concurrent_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

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


class XrayConfigSnapshot(Base):
    __tablename__ = "xray_config_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    applied: Mapped[bool] = mapped_column(default=False)
    apply_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    apply_error: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ResellerPlan(Base):
    __tablename__ = "reseller_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_services: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_traffic_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_concurrent_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    subscriptions: Mapped[list["ResellerSubscription"]] = relationship("ResellerSubscription", back_populates="plan")


class ResellerSubscription(Base):
    __tablename__ = "reseller_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reseller_id: Mapped[int] = mapped_column(ForeignKey("resellers.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("reseller_plans.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    reseller: Mapped["Reseller"] = relationship("Reseller", backref="subscriptions")
    plan: Mapped["ResellerPlan"] = relationship("ResellerPlan", back_populates="subscriptions")


class WalletTransactionType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reseller_id: Mapped[int] = mapped_column(ForeignKey("resellers.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[WalletTransactionType] = mapped_column(Enum(WalletTransactionType), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    reseller: Mapped["Reseller"] = relationship("Reseller", backref="transactions")


class SupportTicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_by: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[SupportTicketStatus] = mapped_column(Enum(SupportTicketStatus), default=SupportTicketStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    messages: Mapped[list["SupportTicketMessage"]] = relationship(
        "SupportTicketMessage", back_populates="ticket", cascade="all, delete-orphan"
    )


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reseller_id: Mapped[int | None] = mapped_column(ForeignKey("resellers.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reseller: Mapped["Reseller | None"] = relationship("Reseller", backref="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
