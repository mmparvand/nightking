from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import crud, schemas
from .auth import get_current_user
from .db import get_db
from .models import Role, ServiceProtocol

router = APIRouter(prefix="/api", tags=["api"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[schemas.UserPublic, Depends(get_current_user)]


# Users
@router.get("/users", response_model=schemas.PaginatedUsers)
def list_users(
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> schemas.PaginatedUsers:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    users = crud.list_users(db, limit=limit, offset=offset, reseller_id=reseller_id)
    return schemas.PaginatedUsers(items=[schemas.UserOut.from_orm(u) for u in users], limit=limit, offset=offset)


@router.post("/users", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    db: DbDep,
    current_user: CurrentUser,
) -> schemas.UserOut:
    reseller_id = payload.reseller_id
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    user = crud.create_user(db, email=payload.email, full_name=payload.full_name, reseller_id=reseller_id)
    return schemas.UserOut.from_orm(user)


@router.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> schemas.UserOut:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    user = crud.get_user(db, user_id, reseller_id=reseller_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return schemas.UserOut.from_orm(user)


@router.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: DbDep,
    current_user: CurrentUser,
) -> schemas.UserOut:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    user = crud.get_user(db, user_id, reseller_id=reseller_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = crud.update_user(db, user, email=payload.email, full_name=payload.full_name)
    return schemas.UserOut.from_orm(updated)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> None:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    user = crud.get_user(db, user_id, reseller_id=reseller_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    crud.delete_user(db, user)


# Services
@router.get("/services", response_model=schemas.PaginatedServices)
def list_services(
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> schemas.PaginatedServices:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    services = crud.list_services(db, limit=limit, offset=offset, reseller_id=reseller_id)
    items = [schemas.ServiceOut.from_orm(s) for s in services]
    return schemas.PaginatedServices(items=items, limit=limit, offset=offset)


@router.post("/services", response_model=schemas.ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: schemas.ServiceCreate,
    db: DbDep,
    current_user: CurrentUser,
) -> schemas.ServiceOut:
    reseller_id = payload.reseller_id
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
        if payload.reseller_id and payload.reseller_id != reseller.id:
            raise HTTPException(status_code=403, detail="Reseller scope violation")
    user = crud.get_user(db, payload.user_id, reseller_id=reseller_id if current_user.role == Role.RESELLER else None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found for service")
    service = crud.create_service(
        db,
        name=payload.name,
        user_id=payload.user_id,
        reseller_id=reseller_id,
        protocol=ServiceProtocol(payload.protocol),
        endpoint=payload.endpoint,
    )
    return schemas.ServiceOut.from_orm(service)


@router.get("/services/{service_id}", response_model=schemas.ServiceOut)
def get_service(
    service_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> schemas.ServiceOut:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    service = crud.get_service(db, service_id, reseller_id=reseller_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return schemas.ServiceOut.from_orm(service)


@router.put("/services/{service_id}", response_model=schemas.ServiceOut)
def update_service(
    service_id: int,
    payload: schemas.ServiceUpdate,
    db: DbDep,
    current_user: CurrentUser,
) -> schemas.ServiceOut:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    service = crud.get_service(db, service_id, reseller_id=reseller_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    updated = crud.update_service(
        db,
        service,
        name=payload.name,
        protocol=ServiceProtocol(payload.protocol),
        endpoint=payload.endpoint,
    )
    return schemas.ServiceOut.from_orm(updated)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> None:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    service = crud.get_service(db, service_id, reseller_id=reseller_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    crud.delete_service(db, service)


@router.post("/services/{service_id}/token", response_model=schemas.SubscriptionTokenOut)
def generate_token(
    service_id: int,
    db: DbDep,
    current_user: CurrentUser,
) -> schemas.SubscriptionTokenOut:
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    service = crud.get_service(db, service_id, reseller_id=reseller_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    token = crud.ensure_subscription_token(db, service)
    return schemas.SubscriptionTokenOut.from_orm(token)
