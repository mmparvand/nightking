from __future__ import annotations

from typing import Annotated, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import UploadFile, File, Body
from fastapi.responses import FileResponse

from . import crud, schemas
from .auth import get_current_user
from .db import get_db
from .models import Role, ServiceProtocol
from .config import get_settings
from .backup import create_backup, list_backups, download_backup, restore_backup, upload_backup
from . import migration
from .models import Node, ServiceNode
from .security import get_password_hash, verify_password
import httpx

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
        _enforce_plan_quota_users(db, reseller_id)
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
    settings = get_settings()
    reseller_id = payload.reseller_id
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
        if payload.reseller_id and payload.reseller_id != reseller.id:
            raise HTTPException(status_code=403, detail="Reseller scope violation")
        _enforce_reseller_limits(payload, settings)
        _enforce_plan_quota_services(db, reseller_id)
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
        traffic_limit_bytes=payload.traffic_limit_bytes,
        expires_at=payload.expires_at,
        ip_limit=payload.ip_limit,
        concurrent_limit=payload.concurrent_limit,
        is_active=payload.is_active,
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
    settings = get_settings()
    reseller_id = None
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if reseller is None:
            raise HTTPException(status_code=404, detail="Reseller mapping not found")
        reseller_id = reseller.id
    service = crud.get_service(db, service_id, reseller_id=reseller_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if current_user.role == Role.RESELLER:
        _enforce_reseller_limits(payload, settings)
    updated = crud.update_service(
        db,
        service,
        name=payload.name,
        protocol=ServiceProtocol(payload.protocol),
        endpoint=payload.endpoint,
        traffic_limit_bytes=payload.traffic_limit_bytes,
        expires_at=payload.expires_at,
        ip_limit=payload.ip_limit,
        concurrent_limit=payload.concurrent_limit,
        is_active=payload.is_active,
    )
    return schemas.ServiceOut.from_orm(updated)


@router.post("/services/{service_id}/usage", response_model=schemas.ServiceOut)
def set_usage(
    service_id: int,
    traffic_used_bytes: int,
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
    updated = crud.update_usage(db, service, traffic_used_bytes=traffic_used_bytes)
    return schemas.ServiceOut.from_orm(updated)


def _enforce_reseller_limits(payload: schemas.ServiceBase, settings) -> None:
    if payload.ip_limit and payload.ip_limit > settings.reseller_max_ip_limit:
        raise HTTPException(status_code=403, detail="IP limit exceeds reseller plan")
    if payload.concurrent_limit and payload.concurrent_limit > settings.reseller_max_concurrent_limit:
        raise HTTPException(status_code=403, detail="Concurrent limit exceeds reseller plan")
    if payload.traffic_limit_bytes and payload.traffic_limit_bytes > settings.reseller_max_traffic_limit_bytes:
        raise HTTPException(status_code=403, detail="Traffic limit exceeds reseller plan")


def _get_active_plan(db: Session, reseller_id: int):
    sub = crud.get_active_subscription(db, reseller_id)
    if not sub or sub.ends_at < datetime.utcnow() or not sub.is_active:
        return None
    return sub


def _enforce_plan_quota_users(db: Session, reseller_id: int) -> None:
    sub = _get_active_plan(db, reseller_id)
    if not sub:
        return
    if sub.plan.max_users is not None:
        count = crud.count_users_for_reseller(db, reseller_id)
        if count >= sub.plan.max_users:
            raise HTTPException(status_code=403, detail="Plan user limit reached")


def _enforce_plan_quota_services(db: Session, reseller_id: int) -> None:
    sub = _get_active_plan(db, reseller_id)
    if not sub:
        return
    if sub.plan.max_services is not None:
        count = crud.count_services_for_reseller(db, reseller_id)
        if count >= sub.plan.max_services:
            raise HTTPException(status_code=403, detail="Plan service limit reached")


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


# Nodes
@router.post("/nodes", response_model=schemas.NodeOut, status_code=status.HTTP_201_CREATED)
def create_node_endpoint(payload: schemas.NodeCreate, db: DbDep, current_user: CurrentUser) -> schemas.NodeOut:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    node = crud.create_node(
        db,
        name=payload.name,
        location=payload.location,
        ip_address=payload.ip_address,
        api_base_url=payload.api_base_url,
        auth_token_hash=get_password_hash(payload.auth_token),
        is_active=True,
    )
    crud.add_audit_log(db, current_user.username, "node_create", node.name)
    return schemas.NodeOut.from_orm(node)


@router.get("/nodes", response_model=list[schemas.NodeOut])
def list_nodes_endpoint(db: DbDep, current_user: CurrentUser) -> list[schemas.NodeOut]:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    nodes = crud.list_nodes(db)
    return [schemas.NodeOut.from_orm(n) for n in nodes]


@router.post("/nodes/{node_id}/enable", response_model=schemas.NodeOut)
def enable_node(node_id: int, db: DbDep, current_user: CurrentUser) -> schemas.NodeOut:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    node = crud.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node = crud.set_node_active(db, node, True)
    return schemas.NodeOut.from_orm(node)


@router.post("/nodes/{node_id}/disable", response_model=schemas.NodeOut)
def disable_node(node_id: int, db: DbDep, current_user: CurrentUser) -> schemas.NodeOut:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    node = crud.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node = crud.set_node_active(db, node, False)
    return schemas.NodeOut.from_orm(node)


@router.get("/nodes/{node_id}/status")
def node_status(node_id: int, db: DbDep, current_user: CurrentUser):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    node = crud.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        resp = httpx.get(f"{node.api_base_url}/agent/status", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return {"status": data, "last_seen_at": node.last_seen_at}
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc), "last_seen_at": node.last_seen_at}


@router.post("/nodes/{node_id}/apply-config")
def node_apply_config(
    node_id: int,
    token: str = Body(..., embed=True),
    db: DbDep = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    settings=Depends(get_settings),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    node = crud.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if not verify_password(token, node.auth_token_hash):
        raise HTTPException(status_code=403, detail="Invalid node token")
    config = _render_xray_config(db, settings)
    try:
        resp = httpx.post(
            f"{node.api_base_url}/agent/config/apply",
            json={"config": config},
            headers={"X-Node-Token": token},
            timeout=10,
        )
        resp.raise_for_status()
        node.last_seen_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Node apply failed: {exc}")
    return {"status": "applied"}


@router.post("/services/{service_id}/nodes")
def set_service_nodes(
    service_id: int,
    node_ids: list[int] = Body(...),
    db: DbDep = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    service = crud.get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    crud.assign_service_nodes(db, service, node_ids)
    return {"service_id": service_id, "node_ids": node_ids}


# Reseller business system (minimal MVP)
@router.get("/plans", response_model=list[schemas.ResellerPlanOut])
def list_plans(db: DbDep, current_user: CurrentUser) -> list[schemas.ResellerPlanOut]:
    plans = crud.list_plans(db)
    return [schemas.ResellerPlanOut.from_orm(p) for p in plans]


@router.post("/plans", response_model=schemas.ResellerPlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(payload: schemas.ResellerPlanCreate, db: DbDep, current_user: CurrentUser) -> schemas.ResellerPlanOut:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    plan = crud.create_plan(db, **payload.dict())
    crud.add_audit_log(db, current_user.username, "plan_create", str(payload.dict()))
    return schemas.ResellerPlanOut.from_orm(plan)


@router.put("/plans/{plan_id}", response_model=schemas.ResellerPlanOut)
def update_plan(plan_id: int, payload: schemas.ResellerPlanCreate, db: DbDep, current_user: CurrentUser) -> schemas.ResellerPlanOut:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    plan = crud.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = crud.update_plan(db, plan, **payload.dict())
    crud.add_audit_log(db, current_user.username, "plan_update", f"{plan_id}")
    return schemas.ResellerPlanOut.from_orm(plan)


@router.post("/resellers/{reseller_id}/wallet", response_model=schemas.WalletTransaction)
def wallet_action(
    reseller_id: int,
    amount: int,
    type: str,
    reason: str = "",
    db: DbDep = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    if type not in ("CREDIT", "DEBIT"):
        raise HTTPException(status_code=400, detail="Invalid type")
    balance = crud.get_wallet_balance(db, reseller_id)
    if type == "DEBIT" and balance - amount < 0:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    tx = crud.add_transaction(db, reseller_id, amount, getattr(crud.WalletTransactionType, type), reason or "")
    crud.add_audit_log(db, current_user.username, "wallet_"+type.lower(), f"{reseller_id}:{amount}")
    return schemas.WalletTransaction.from_orm(tx)


@router.post("/resellers/{reseller_id}/subscribe", response_model=schemas.ResellerSubscriptionOut)
def subscribe_plan(
    reseller_id: int,
    plan_id: int,
    db: DbDep,
    current_user: CurrentUser,
):
    if current_user.role not in (Role.ADMIN, Role.RESELLER):
        raise HTTPException(status_code=403, detail="Forbidden")
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if not reseller or reseller.id != reseller_id:
            raise HTTPException(status_code=403, detail="Reseller scope violation")
    plan = crud.get_plan(db, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not available")
    balance = crud.get_wallet_balance(db, reseller_id)
    if balance < plan.price:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    crud.add_transaction(db, reseller_id, plan.price, crud.WalletTransactionType.DEBIT, f"Plan purchase {plan_id}")
    sub = crud.activate_plan(db, reseller_id, plan)
    crud.add_audit_log(db, current_user.username, "plan_purchase", f"{reseller_id}:{plan_id}")
    return schemas.ResellerSubscriptionOut.from_orm(sub)


@router.get("/resellers/{reseller_id}/report", response_model=schemas.ResellerReport)
def reseller_report(reseller_id: int, db: DbDep, current_user: CurrentUser) -> schemas.ResellerReport:
    if current_user.role == Role.RESELLER:
        reseller = crud.get_reseller_by_username(db, current_user.username)
        if not reseller or reseller.id != reseller_id:
            raise HTTPException(status_code=403, detail="Reseller scope violation")
    users = crud.count_users_for_reseller(db, reseller_id)
    services = crud.count_services_for_reseller(db, reseller_id)
    traffic_used = db.scalar(select(db.func.coalesce(db.func.sum(Service.traffic_used_bytes), 0)).where(Service.reseller_id == reseller_id)) or 0
    plan = _get_active_plan(db, reseller_id)
    balance = crud.get_wallet_balance(db, reseller_id)
    return schemas.ResellerReport(
        reseller_id=reseller_id,
        users=users,
        services=services,
        traffic_used_bytes=traffic_used,
        plan=schemas.ResellerSubscriptionOut.from_orm(plan) if plan else None,
        wallet_balance=balance,
    )


@router.get("/tickets", response_model=list[schemas.SupportTicketOut])
def list_support_tickets(db: DbDep, current_user: CurrentUser) -> list[schemas.SupportTicketOut]:
    created_by = None
    if current_user.role == Role.RESELLER:
        created_by = current_user.username
    tickets = crud.list_tickets(db, created_by=created_by)
    return [schemas.SupportTicketOut.from_orm(t) for t in tickets]


@router.post("/tickets", response_model=schemas.SupportTicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(subject: str, message: str, db: DbDep, current_user: CurrentUser) -> schemas.SupportTicketOut:
    ticket = crud.create_ticket(db, created_by=current_user.username, subject=subject, message=message, sender_role=current_user.role.value)
    crud.add_audit_log(db, current_user.username, "ticket_create", subject)
    return schemas.SupportTicketOut.from_orm(ticket)


@router.post("/tickets/{ticket_id}/reply", response_model=schemas.SupportTicketOut)
def reply_ticket(ticket_id: int, message: str, db: DbDep, current_user: CurrentUser) -> schemas.SupportTicketOut:
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == Role.RESELLER and ticket.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="Forbidden")
    ticket = crud.add_ticket_message(db, ticket, current_user.role.value, message)
    crud.add_audit_log(db, current_user.username, "ticket_reply", str(ticket_id))
    return schemas.SupportTicketOut.from_orm(ticket)


@router.post("/tickets/{ticket_id}/status", response_model=schemas.SupportTicketOut)
def set_ticket_status(ticket_id: int, status: str, db: DbDep, current_user: CurrentUser) -> schemas.SupportTicketOut:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = crud.update_ticket_status(db, ticket, status)
    crud.add_audit_log(db, current_user.username, "ticket_status", f"{ticket_id}:{status}")
    return schemas.SupportTicketOut.from_orm(ticket)


# Backups (admin only)
@router.post("/backups/create", response_model=schemas.BackupCreateResponse)
def create_backup_endpoint(db: DbDep, current_user: CurrentUser, settings=Depends(get_settings)) -> schemas.BackupCreateResponse:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    info = create_backup(settings, db, current_user.username)
    return schemas.BackupCreateResponse(**info)


@router.get("/backups", response_model=list[schemas.BackupInfo])
def list_backups_endpoint(current_user: CurrentUser, settings=Depends(get_settings)) -> list[schemas.BackupInfo]:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    items = list_backups(settings)
    return [schemas.BackupInfo(**i) for i in items]


@router.get("/backups/{backup_id}/download")
def download_backup_endpoint(backup_id: str, current_user: CurrentUser, settings=Depends(get_settings)):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    path = download_backup(settings, backup_id)
    return FileResponse(path)


@router.post("/backups/{backup_id}/restore")
def restore_backup_endpoint(
    backup_id: str,
    confirm: bool = Body(...),
    db: DbDep = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    settings=Depends(get_settings),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    status_text = restore_backup(settings, backup_id, db, current_user.username)
    return {"status": status_text}


@router.post("/backups/upload", response_model=schemas.BackupInfo)
def upload_backup_endpoint(
    file: UploadFile = File(...),
    db: DbDep = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    settings=Depends(get_settings),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    info = upload_backup(settings, file, current_user.username, db)
    return schemas.BackupInfo(**info)


# Migration wizard (admin only)
@router.post("/migration/marzban/preview", response_model=schemas.MigrationPreview)
def migration_preview(
    method: str = Body("json"),
    file: UploadFile | None = None,
    db_connection: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    if method == "json":
        if not file:
            raise HTTPException(status_code=400, detail="File required")
        data = file.file.read()
        preview = migration.preview_json(data)
        return schemas.MigrationPreview(**preview)
    elif method == "db":
        if not db_connection:
            raise HTTPException(status_code=400, detail="DB connection required")
        return migration.preview_db(db_connection)
    raise HTTPException(status_code=400, detail="Invalid method")


@router.post("/migration/marzban/run", response_model=schemas.MigrationResult)
def migration_run(
    method: str = Body("json"),
    file: UploadFile | None = None,
    db_connection: str | None = None,
    db: DbDep = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    if method == "json":
        if not file:
            raise HTTPException(status_code=400, detail="File required")
        data = file.file.read()
        result = migration.run_json_import(db, data)
        crud.add_audit_log(db, current_user.username, "migration_run", f"json:{result}")
        return schemas.MigrationResult(**result)
    elif method == "db":
        if not db_connection:
            raise HTTPException(status_code=400, detail="DB connection required")
        result = migration.run_db_import(db_connection)
        crud.add_audit_log(db, current_user.username, "migration_run", f"db:{db_connection}")
        return result
    raise HTTPException(status_code=400, detail="Invalid method")
