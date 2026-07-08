import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.orders import OrderCreate, OrderCreateResponse, OrderStatusUpdate, SheetStatusUpdate
from app.services.orders import apply_sheet_status, create_order, update_order_status

log = logging.getLogger(__name__)

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


@router.post("/sheet-status")
async def sheet_status_webhook(payload: SheetStatusUpdate, session: DbSession) -> dict:
    """Called by the Google Apps Script onEdit trigger whenever the ops team
    changes the "Status" cell for a row. Keeps the admin panel in sync with
    what's typed in the sheet (Confirmé, appel 1..4, reporté, annulé, ...)."""
    if settings.order_webhook_secret:
        if payload.secret != settings.order_webhook_secret:
            raise HTTPException(status_code=401, detail="invalid_secret")
    else:
        log.warning("ORDER_WEBHOOK_SECRET is not set — /sheet-status is unauthenticated")

    order = await apply_sheet_status(session, payload.order_id, payload.status)
    return {"ok": True, "order_number": order.order_number, "status": order.status}
