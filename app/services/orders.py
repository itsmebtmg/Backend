import random
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, OrderEvent, OrderItem, TrackingEvent
from app.schemas.orders import OrderCreate
from app.services.offers import validate_and_price_order
from app.services.phone import InvalidMoroccanPhone, normalize_moroccan_phone
from app.services.sheets import sync_order_to_sheet
from app.services.tracking.dispatcher import send_purchase_events


async def create_order(session: AsyncSession, payload: OrderCreate, request: Request) -> Order:
    existing = await session.scalar(select(Order).where(Order.event_id == payload.event_id))
    if existing:
        return existing

    try:
        phone = normalize_moroccan_phone(payload.customer.phone)
    except InvalidMoroccanPhone as exc:
        raise HTTPException(status_code=422, detail="invalid_moroccan_phone") from exc

    items, subtotal_mad, discount_mad, total_mad = validate_and_price_order(payload)
    order_number = await _generate_unique_order_number(session)
    client_ip = _client_ip(request)

    order = Order(
        order_number=order_number,
        status="new",
        customer_name=payload.customer.name.strip(),
        phone_raw=payload.customer.phone,
        phone_local=phone["local"],
        phone_e164=phone["e164"],
        phone_digits=phone["digits_international"],
        city=payload.customer.city.strip(),
        address=payload.customer.address.strip(),
        subtotal_mad=subtotal_mad,
        discount_mad=discount_mad,
        shipping_mad=0,
        total_mad=total_mad,
        source_page=payload.source_page,
        landing_url=payload.landing_url,
        fbp=payload.tracking.fbp,
        fbc=payload.tracking.fbc,
        ttclid=payload.tracking.ttclid,
        ttp=payload.tracking.ttp,
        snap_click_id=payload.tracking.snap_click_id,
        client_user_agent=payload.tracking.client_user_agent
        or request.headers.get("user-agent"),
        client_ip=client_ip,
        event_id=payload.event_id,
        upsell_accepted=payload.offer.upsell_accepted,
    )
    session.add(order)
    await session.flush()

    order_items: list[OrderItem] = []
    for item in items:
        line_total = 0 if item.is_free_gift else item.unit_price_mad * item.quantity
        db_item = OrderItem(
            order_id=order.id,
            sku=item.sku,
            product_slug=item.product_slug,
            name=item.name,
            quantity=item.quantity,
            unit_price_mad=item.unit_price_mad,
            line_total_mad=line_total,
            is_free_gift=item.is_free_gift,
            offer_code=item.offer_code,
        )
        session.add(db_item)
        order_items.append(db_item)

    session.add(OrderEvent(order_id=order.id, event_type="created", event_data={"total_mad": total_mad}))
    await session.commit()
    await session.refresh(order)

    order_payload = _order_payload(order, order_items)

    try:
        await sync_order_to_sheet(order_payload)
        session.add(OrderEvent(order_id=order.id, event_type="sheet_synced", event_data={}))
    except Exception as exc:  # noqa: BLE001
        session.add(OrderEvent(order_id=order.id, event_type="sheet_sync_failed", event_data={"error": str(exc)}))

    capi_results = await send_purchase_events(order_payload, phone)
    for result in capi_results:
        session.add(
            TrackingEvent(
                order_id=order.id,
                event_id=order.event_id,
                platform=result["platform"],
                event_name=result["event_name"],
                payload=result["payload"],
                response_status=result["response_status"],
                response_body=result["response_body"],
                success=result["success"],
            )
        )
    if capi_results:
        session.add(
            OrderEvent(
                order_id=order.id,
                event_type="capi_sent",
                event_data={"results": [{k: v for k, v in r.items() if k != "payload"} for r in capi_results]},
            )
        )
    await session.commit()

    return order


async def update_order_status(
    session: AsyncSession, order_number: str, status: str, notes: str | None
) -> Order:
    order = await session.scalar(select(Order).where(Order.order_number == order_number))
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    order.status = status
    order.notes = notes
    session.add(OrderEvent(order_id=order.id, event_type=status, event_data={"notes": notes}))
    await session.commit()
    await session.refresh(order)
    return order


async def _generate_unique_order_number(session: AsyncSession) -> str:
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    for _ in range(20):
        candidate = f"SLY-{today}-{random.randint(1000, 9999)}"
        exists = await session.scalar(select(Order.id).where(Order.order_number == candidate))
        if not exists:
            return candidate
    raise HTTPException(status_code=500, detail="order_number_generation_failed")


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _order_payload(order: Order, items: list[OrderItem]) -> dict:
    items_payload = [
        {
            "sku": item.sku,
            "product_slug": item.product_slug,
            "name": item.name,
            "quantity": item.quantity,
            "unit_price_mad": item.unit_price_mad,
            "is_free_gift": item.is_free_gift,
        }
        for item in items
    ]
    items_text = " | ".join(
        f"{item['name']} x{item['quantity']} "
        f"{'FREE' if item['is_free_gift'] else str(item['unit_price_mad']) + ' MAD'}"
        for item in items_payload
    )
    return {
        "order_number": order.order_number,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "status": order.status,
        "customer_name": order.customer_name,
        "phone_local": order.phone_local,
        "phone_e164": order.phone_e164,
        "phone_digits": order.phone_digits,
        "city": order.city,
        "address": order.address,
        "subtotal_mad": order.subtotal_mad,
        "discount_mad": order.discount_mad,
        "shipping_mad": order.shipping_mad,
        "total_mad": order.total_mad,
        "payment_method": order.payment_method,
        "source_page": order.source_page,
        "landing_url": order.landing_url,
        "upsell_accepted": order.upsell_accepted,
        "items": items_payload,
        "items_text": items_text,
        "event_id": order.event_id,
        "fbp": order.fbp,
        "fbc": order.fbc,
        "ttclid": order.ttclid,
        "ttp": order.ttp,
        "snap_click_id": order.snap_click_id,
        "client_user_agent": order.client_user_agent,
        "client_ip": str(order.client_ip) if order.client_ip else None,
    }
