import random
import unicodedata
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, OrderEvent, OrderItem, TrackingEvent
from app.schemas.orders import OrderCreate
from app.services import geo
from app.services.offers import validate_and_price_order
from app.services.phone import InvalidMoroccanPhone, normalize_moroccan_phone
from app.services.sheets import sync_order_to_sheet
from app.services.tracking.dispatcher import send_purchase_events

# Maps the exact labels used in the Google Sheet "Status" dropdown (see the
# data-validation rule the ops team set on the column) to our canonical
# `Order.status` values (see ORDER_STATUSES in app/schemas/admin.py). Keys are
# normalized (lowercased, accents stripped) before lookup so "Confirmé",
# "confirme" and "CONFIRMÉ" all match the same entry.
SHEET_STATUS_MAP: dict[str, str] = {
    "confirme": "confirmed",
    "appel 1": "no_answer",
    "appel 2": "no_answer",
    "appel 3": "no_answer",
    "appel 4": "no_answer",
    "reporte": "postponed",
    "plus tard": "postponed",
    "faux numero": "canceled",
    "double": "canceled",
    "annule": "canceled",
    "rappel": "postponed",
}


def _normalize_sheet_label(raw: str) -> str:
    decomposed = unicodedata.normalize("NFKD", raw.strip().lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def map_sheet_status(raw_status: str) -> str | None:
    """Translate a raw Google Sheet status label to a canonical order status,
    or None if the label isn't recognized (e.g. the cell was cleared)."""
    return SHEET_STATUS_MAP.get(_normalize_sheet_label(raw_status))


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
    geo_verdict = await geo.check_ip(client_ip)

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
        geo_country=geo_verdict.country_iso,
        is_valid_ma=geo_verdict.is_valid_ma,
        is_vpn=geo_verdict.is_vpn,
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
    if status == "confirmed" and order.confirmed_at is None:
        order.confirmed_at = datetime.now(tz=timezone.utc)
    session.add(OrderEvent(order_id=order.id, event_type=status, event_data={"notes": notes}))
    await session.commit()
    await session.refresh(order)
    return order


async def apply_sheet_status(session: AsyncSession, order_number: str, raw_status: str) -> Order:
    """Handle a Status-column edit coming from the Google Sheet. Maps the raw
    French label to a canonical status, applies it via update_order_status,
    and records the original label so it stays visible in the admin timeline."""
    canonical = map_sheet_status(raw_status)
    if canonical is None:
        raise HTTPException(status_code=422, detail="unrecognized_sheet_status")

    order = await session.scalar(select(Order).where(Order.order_number == order_number))
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    notes = f"Sheet: \"{raw_status.strip()}\""
    order.status = canonical
    order.notes = notes
    if canonical == "confirmed" and order.confirmed_at is None:
        order.confirmed_at = datetime.now(tz=timezone.utc)
    session.add(
        OrderEvent(
            order_id=order.id,
            event_type=f"sheet_status:{canonical}",
            event_data={"raw_status": raw_status, "notes": notes},
        )
    )
    await session.commit()
    await session.refresh(order)
    return order


async def _generate_unique_order_number(session: AsyncSession) -> str:
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    for _ in range(20):
        candidate = f"Solyra-{today}-{random.randint(1000, 9999)}"
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
    created_at = order.created_at or datetime.now(tz=timezone.utc)

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
        # Simplified fields for the Google Sheet webhook (docs/google-apps-script/orders-webhook.js)
        "sheet_date": created_at.strftime("%d/%m/%Y"),
        "sheet_order_id": order.order_number,
        "sheet_country": "Morocco",
        "sheet_name": order.customer_name,
        "sheet_phone": order.phone_local,
        "sheet_product": "/".join(item["name"] for item in items_payload),
        "sheet_quantity": "/".join(str(item["quantity"]) for item in items_payload),
        "sheet_total_price": order.total_mad,
        "sheet_currency": "MAD",
        "sheet_status": "",
    }
