from __future__ import annotations

import secrets
from typing import Iterable, Optional

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from datetime import datetime, timedelta

from .models import (
    Reseller,
    ResellerPlan,
    ResellerSubscription,
    Service,
    ServiceProtocol,
    SubscriptionToken,
    User,
    WalletTransaction,
    WalletTransactionType,
    SupportTicket,
    SupportTicketMessage,
    AuditLog,
    Node,
    ServiceNode,
)


def paginate(query, limit: int, offset: int):
    return query.limit(limit).offset(offset)


# Resellers
def get_reseller_by_username(db: Session, username: str) -> Optional[Reseller]:
    return db.scalar(select(Reseller).where(Reseller.auth_username == username))


# Users
def list_users(db: Session, limit: int, offset: int, reseller_id: int | None = None) -> Iterable[User]:
    stmt = select(User)
    if reseller_id:
        stmt = stmt.where(User.reseller_id == reseller_id)
    stmt = stmt.order_by(User.id)
    stmt = paginate(stmt, limit, offset)
    return db.scalars(stmt).all()


def create_user(db: Session, email: str, full_name: str, reseller_id: int | None) -> User:
    user = User(email=email, full_name=full_name, reseller_id=reseller_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int, reseller_id: int | None = None) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    if reseller_id:
        stmt = stmt.where(User.reseller_id == reseller_id)
    return db.scalar(stmt)


def update_user(db: Session, user: User, *, email: str, full_name: str) -> User:
    user.email = email
    user.full_name = full_name
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


# Services
def list_services(db: Session, limit: int, offset: int, reseller_id: int | None = None) -> Iterable[Service]:
    stmt = select(Service)
    if reseller_id:
        stmt = stmt.where(Service.reseller_id == reseller_id)
    stmt = stmt.order_by(Service.id)
    stmt = paginate(stmt, limit, offset)
    return db.scalars(stmt).all()


def create_service(
    db: Session,
    *,
    name: str,
    user_id: int,
    reseller_id: int | None,
    protocol: ServiceProtocol,
    endpoint: str | None,
    traffic_limit_bytes: int | None = None,
    expires_at=None,
    ip_limit: int | None = None,
    concurrent_limit: int | None = None,
    is_active: bool | None = True,
) -> Service:
    service = Service(
        name=name,
        user_id=user_id,
        reseller_id=reseller_id,
        protocol=protocol,
        endpoint=endpoint,
        traffic_limit_bytes=traffic_limit_bytes,
        expires_at=expires_at,
        ip_limit=ip_limit,
        concurrent_limit=concurrent_limit,
        is_active=is_active if is_active is not None else True,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    ensure_subscription_token(db, service)
    db.refresh(service)
    return service


def get_service(db: Session, service_id: int, reseller_id: int | None = None) -> Optional[Service]:
    stmt = select(Service).where(Service.id == service_id)
    if reseller_id:
        stmt = stmt.where(Service.reseller_id == reseller_id)
    return db.scalar(stmt)


def count_services_for_reseller(db: Session, reseller_id: int) -> int:
    return db.scalar(select(db.func.count()).where(Service.reseller_id == reseller_id)) or 0


def count_users_for_reseller(db: Session, reseller_id: int) -> int:
    return db.scalar(select(db.func.count()).where(User.reseller_id == reseller_id)) or 0


def update_service(
    db: Session,
    service: Service,
    *,
    name: str,
    protocol: ServiceProtocol,
    endpoint: str | None,
    traffic_limit_bytes: int | None = None,
    expires_at=None,
    ip_limit: int | None = None,
    concurrent_limit: int | None = None,
    is_active: bool | None = None,
) -> Service:
    service.name = name
    service.protocol = protocol
    service.endpoint = endpoint
    service.traffic_limit_bytes = traffic_limit_bytes
    if expires_at is not None:
        service.expires_at = expires_at
    service.ip_limit = ip_limit
    service.concurrent_limit = concurrent_limit
    if is_active is not None:
        service.is_active = is_active
    db.commit()
    db.refresh(service)
    ensure_subscription_token(db, service)
    db.refresh(service)
    return service


def update_usage(db: Session, service: Service, *, traffic_used_bytes: int) -> Service:
    service.traffic_used_bytes = traffic_used_bytes
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service: Service) -> None:
    db.delete(service)
    db.commit()


def ensure_subscription_token(db: Session, service: Service) -> SubscriptionToken:
    if service.subscription_token:
        return service.subscription_token
    token_value = secrets.token_urlsafe(32)
    token = SubscriptionToken(token=token_value, service_id=service.id)
    db.add(token)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(token)
    return token


def get_subscription_by_token(db: Session, token: str) -> SubscriptionToken | None:
    stmt = (
        select(SubscriptionToken)
        .where(SubscriptionToken.token == token)
        .options(selectinload(SubscriptionToken.service).selectinload(Service.user), selectinload(SubscriptionToken.service).selectinload(Service.service_nodes).selectinload(ServiceNode.node))
    )
    return db.scalar(stmt)


# Reseller plans and wallet
def create_plan(db: Session, **kwargs) -> ResellerPlan:
    plan = ResellerPlan(**kwargs)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_plans(db: Session) -> list[ResellerPlan]:
    return db.scalars(select(ResellerPlan)).all()


def get_plan(db: Session, plan_id: int) -> ResellerPlan | None:
    return db.get(ResellerPlan, plan_id)


def update_plan(db: Session, plan: ResellerPlan, **kwargs) -> ResellerPlan:
    for k, v in kwargs.items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


def add_transaction(db: Session, reseller_id: int, amount: int, type: WalletTransactionType, reason: str | None = None):
    tx = WalletTransaction(reseller_id=reseller_id, amount=amount, type=type, reason=reason)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get_wallet_balance(db: Session, reseller_id: int) -> int:
    credits = db.scalar(select(db.func.coalesce(db.func.sum(WalletTransaction.amount), 0)).where(WalletTransaction.reseller_id == reseller_id, WalletTransaction.type == WalletTransactionType.CREDIT)) or 0
    debits = db.scalar(select(db.func.coalesce(db.func.sum(WalletTransaction.amount), 0)).where(WalletTransaction.reseller_id == reseller_id, WalletTransaction.type == WalletTransactionType.DEBIT)) or 0
    return credits - debits


def activate_plan(db: Session, reseller_id: int, plan: ResellerPlan) -> ResellerSubscription:
    now = datetime.utcnow()
    sub = ResellerSubscription(
        reseller_id=reseller_id,
        plan_id=plan.id,
        starts_at=now,
        ends_at=now + timedelta(days=plan.duration_days),
        is_active=True,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def get_active_subscription(db: Session, reseller_id: int) -> ResellerSubscription | None:
    stmt = (
        select(ResellerSubscription)
        .where(ResellerSubscription.reseller_id == reseller_id, ResellerSubscription.is_active == True)  # noqa: E712
        .order_by(ResellerSubscription.ends_at.desc())
    )
    return db.scalar(stmt)


def add_audit_log(db: Session, actor: str, action: str, detail: str | None = None) -> AuditLog:
    log = AuditLog(actor=actor, action=action, detail=detail)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# Tickets
def create_ticket(db: Session, created_by: str, subject: str, message: str, sender_role: str) -> SupportTicket:
    ticket = SupportTicket(created_by=created_by, subject=subject)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    msg = SupportTicketMessage(ticket_id=ticket.id, sender_role=sender_role, message=message)
    db.add(msg)
    db.commit()
    db.refresh(ticket)
    return ticket


def add_ticket_message(db: Session, ticket: SupportTicket, sender_role: str, message: str) -> SupportTicket:
    msg = SupportTicketMessage(ticket_id=ticket.id, sender_role=sender_role, message=message)
    db.add(msg)
    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(db: Session, created_by: str | None = None) -> list[SupportTicket]:
    stmt = select(SupportTicket)
    if created_by:
        stmt = stmt.where(SupportTicket.created_by == created_by)
    return db.scalars(stmt).all()


def get_ticket(db: Session, ticket_id: int) -> SupportTicket | None:
    return db.get(SupportTicket, ticket_id)


def update_ticket_status(db: Session, ticket: SupportTicket, status: str) -> SupportTicket:
    ticket.status = status
    db.commit()
    db.refresh(ticket)
    return ticket


# Nodes
def create_node(db: Session, **kwargs) -> Node:
    node = Node(**kwargs)
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def list_nodes(db: Session) -> list[Node]:
    return db.scalars(select(Node)).all()


def get_node(db: Session, node_id: int) -> Node | None:
    return db.get(Node, node_id)


def set_node_active(db: Session, node: Node, active: bool) -> Node:
    node.is_active = active
    db.commit()
    db.refresh(node)
    return node


def assign_service_nodes(db: Session, service: Service, node_ids: list[int]) -> list[ServiceNode]:
    existing = {sn.node_id: sn for sn in service.service_nodes}
    for nid in node_ids:
        if nid not in existing:
            db.add(ServiceNode(service_id=service.id, node_id=nid))
    for nid, sn in list(existing.items()):
        if nid not in node_ids:
            db.delete(sn)
    db.commit()
    db.refresh(service)
    return service.service_nodes
