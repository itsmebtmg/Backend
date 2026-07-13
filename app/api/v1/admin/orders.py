from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin import (
    ORDER_STATUSES,
    OrderDetailOut,
    OrderListOut,
    OrderStatusUpdateIn,
    ShipmentOut,
    ShipmentUpdateIn,
)
from app.services import admin_orders
from app.services.auth import AdminSession, require_admin
from app.services.orders import update_order_status

router = APIRouter(prefix="/orders", tags=["admin-orders"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
Admin = Annotated[AdminSession, Depends(require_admin)]


@router.get("", response_model=OrderListOut)
async def list_orders(
    session: DbSession,
    _admin: Admin,
    status: str | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> OrderListOut:
    if status and status not in ORDER_STATUSES:
        status = None
    return await admin_orders.list_orders(
        session,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_number}", response_model=OrderDetailOut)
async def get_order(order_number: str, session: DbSession, _admin: Admin) -> OrderDetailOut:
    return await admin_orders.get_order_detail(session, order_number)


@router.patch("/{order_number}/status")
async def set_order_status(
    order_number: str, payload: OrderStatusUpdateIn, session: DbSession, _admin: Admin
) -> dict:
    order = await update_order_status(session, order_number, payload.status, payload.notes)
    return {"ok": True, "order_number": order.order_number, "status": order.status, "confirmed_at": order.confirmed_at}


@router.patch("/{order_number}/shipment", response_model=ShipmentOut)
async def set_order_shipment(
    order_number: str, payload: ShipmentUpdateIn, session: DbSession, _admin: Admin
) -> ShipmentOut:
    return await admin_orders.upsert_shipment(session, order_number, payload)


@router.delete("/{order_number}")
async def remove_order(order_number: str, session: DbSession, _admin: Admin) -> dict:
    await admin_orders.delete_order(session, order_number)
    return {"ok": True, "order_number": order_number}
