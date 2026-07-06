from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.orders import OrderCreate, OrderCreateResponse, OrderStatusUpdate
from app.services.orders import create_order, update_order_status

router = APIRouter(prefix="/orders", tags=["orders"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=OrderCreateResponse)
async def create_order_endpoint(
    payload: OrderCreate, request: Request, session: DbSession
) -> OrderCreateResponse:
    order = await create_order(session, payload, request)
    return OrderCreateResponse(
        ok=True,
        order_id=str(order.id),
        order_number=order.order_number,
        total_mad=order.total_mad,
    )


@router.patch("/{order_number}/status")
async def update_order_status_endpoint(
    order_number: str, payload: OrderStatusUpdate, session: DbSession
) -> dict:
    order = await update_order_status(session, order_number, payload.status, payload.notes)
    return {"ok": True, "order_number": order.order_number, "status": order.status}
