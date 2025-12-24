from __future__ import annotations

import secrets
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .models import Reseller, Service, ServiceProtocol, SubscriptionToken, User


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
    db: Session, *, name: str, user_id: int, reseller_id: int | None, protocol: ServiceProtocol, endpoint: str | None
) -> Service:
    service = Service(name=name, user_id=user_id, reseller_id=reseller_id, protocol=protocol, endpoint=endpoint)
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


def update_service(
    db: Session, service: Service, *, name: str, protocol: ServiceProtocol, endpoint: str | None
) -> Service:
    service.name = name
    service.protocol = protocol
    service.endpoint = endpoint
    db.commit()
    db.refresh(service)
    ensure_subscription_token(db, service)
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
        .options(selectinload(SubscriptionToken.service).selectinload(Service.user))
    )
    return db.scalar(stmt)
