from __future__ import annotations

from datetime import date, datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Order, OrderEvent, Shipment, TrackingEvent
from app.schemas.admin import (
    OrderDetailOut,
    OrderEventOut,
    OrderItemOut,
    OrderListItemOut,
    OrderListOut,
    ShipmentOut,
    ShipmentUpdateIn,
    TrackingEventOut,
)


async def list_orders(
    session: AsyncSession,
    *,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
    search: str | None,
    page: int,
    page_size: int,
) -> OrderListOut:
    filters = []
    if status:
        filters.append(Order.status == status)
    if date_from:
        filters.append(Order.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        filters.append(Order.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Order.order_number.ilike(pattern),
                Order.phone_local.ilike(pattern),
                Order.customer_name.ilike(pattern),
            )
        )

    total = await session.scalar(select(func.count()).select_from(Order).where(*filters))

    rows = (
        await session.execute(
            select(Order, Shipment.delivery_status)
            .outerjoin(Shipment, Shipment.order_id == Order.id)
            .options(selectinload(Order.items))
            .where(*filters)
            .order_by(Order.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [
        OrderListItemOut(
            id=str(order.id),
            order_number=order.order_number,
            created_at=order.created_at,
            status=order.status,
            confirmed_at=order.confirmed_at,
            customer_name=order.customer_name,
            phone_local=order.phone_local,
            city=order.city,
            total_mad=order.total_mad,
            items_summary=", ".join(f"{item.name} x{item.quantity}" for item in order.items),
            is_valid_ma=order.is_valid_ma,
            is_vpn=order.is_vpn,
            delivery_status=delivery_status,
        )
        for order, delivery_status in rows
    ]

    return OrderListOut(total=total or 0, page=page, page_size=page_size, items=items)


async def get_order_detail(session: AsyncSession, order_number: str) -> OrderDetailOut:
    order = await session.scalar(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.shipment))
        .where(Order.order_number == order_number)
    )
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    events = (
        await session.execute(
            select(OrderEvent)
            .where(OrderEvent.order_id == order.id)
            .order_by(OrderEvent.created_at.desc())
        )
    ).scalars().all()

    tracking_events = (
        await session.execute(
            select(TrackingEvent)
            .where(TrackingEvent.order_id == order.id)
            .order_by(TrackingEvent.created_at.desc())
        )
    ).scalars().all()

    shipment = order.shipment

    return OrderDetailOut(
        id=str(order.id),
        order_number=order.order_number,
        status=order.status,
        confirmed_at=order.confirmed_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        customer_name=order.customer_name,
        phone_raw=order.phone_raw,
        phone_local=order.phone_local,
        phone_e164=order.phone_e164,
        city=order.city,
        address=order.address,
        subtotal_mad=order.subtotal_mad,
        discount_mad=order.discount_mad,
        shipping_mad=order.shipping_mad,
        total_mad=order.total_mad,
        currency=order.currency,
        payment_method=order.payment_method,
        source_page=order.source_page,
        landing_url=order.landing_url,
        utm_source=order.utm_source,
        utm_medium=order.utm_medium,
        utm_campaign=order.utm_campaign,
        fbp=order.fbp,
        fbc=order.fbc,
        ttclid=order.ttclid,
        ttp=order.ttp,
        snap_click_id=order.snap_click_id,
        client_ip=str(order.client_ip) if order.client_ip else None,
        geo_country=order.geo_country,
        is_valid_ma=order.is_valid_ma,
        is_vpn=order.is_vpn,
        upsell_accepted=order.upsell_accepted,
        notes=order.notes,
        items=[
            OrderItemOut(
                sku=item.sku,
                product_slug=item.product_slug,
                name=item.name,
                quantity=item.quantity,
                unit_price_mad=item.unit_price_mad,
                line_total_mad=item.line_total_mad,
                is_free_gift=item.is_free_gift,
                offer_code=item.offer_code,
            )
            for item in order.items
        ],
        events=[
            OrderEventOut(event_type=e.event_type, event_data=e.event_data, created_at=e.created_at)
            for e in events
        ],
        tracking_events=[
            TrackingEventOut(
                platform=t.platform,
                event_name=t.event_name,
                success=t.success,
                response_status=t.response_status,
                created_at=t.created_at,
            )
            for t in tracking_events
        ],
        shipment=(
            ShipmentOut(
                carrier=shipment.carrier,
                tracking_number=shipment.tracking_number,
                delivery_status=shipment.delivery_status,
                cod_amount_mad=shipment.cod_amount_mad,
                shipped_at=shipment.shipped_at,
                delivered_at=shipment.delivered_at,
                updated_at=shipment.updated_at,
            )
            if shipment
            else None
        ),
    )


async def upsert_shipment(session: AsyncSession, order_number: str, payload: ShipmentUpdateIn) -> ShipmentOut:
    order = await session.scalar(
        select(Order).options(selectinload(Order.shipment)).where(Order.order_number == order_number)
    )
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")

    shipment = order.shipment
    now = datetime.now(tz=timezone.utc)
    if not shipment:
        shipment = Shipment(order_id=order.id)
        session.add(shipment)

    was_delivered = shipment.delivery_status == "delivered"
    was_shipped = shipment.delivery_status in {"in_transit", "delivered", "returned", "failed"}

    shipment.delivery_status = payload.delivery_status
    if payload.carrier is not None:
        shipment.carrier = payload.carrier
    if payload.tracking_number is not None:
        shipment.tracking_number = payload.tracking_number
    if payload.cod_amount_mad is not None:
        shipment.cod_amount_mad = payload.cod_amount_mad

    if payload.delivery_status in {"in_transit", "delivered", "returned", "failed"} and not was_shipped:
        shipment.shipped_at = shipment.shipped_at or now
    if payload.delivery_status == "delivered" and not was_delivered:
        shipment.delivered_at = now

    session.add(
        OrderEvent(
            order_id=order.id,
            event_type="shipment_updated",
            event_data={"delivery_status": payload.delivery_status},
        )
    )
    await session.commit()
    await session.refresh(shipment)

    return ShipmentOut(
        carrier=shipment.carrier,
        tracking_number=shipment.tracking_number,
        delivery_status=shipment.delivery_status,
        cod_amount_mad=shipment.cod_amount_mad,
        shipped_at=shipment.shipped_at,
        delivered_at=shipment.delivered_at,
        updated_at=shipment.updated_at,
    )
