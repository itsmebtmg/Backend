"""Admin dashboard metrics. All queries filter clicks to
is_valid_ma=True (non-VPN, Moroccan IP per MaxMind) as requested; orders are
shown in total plus a "valid" subset used for the conversion rate so fraud
traffic never inflates it.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, OrderItem, Shipment, SiteVisit
from app.schemas.admin import BreakdownItemOut, DailyPointOut, MetricsSummaryOut, MetricsTimeseriesOut

log = logging.getLogger(__name__)

CONFIRMED_LIKE_STATUSES = {"confirmed", "delivered", "returned"}


def _range_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
    return start, end


async def _table_exists(session: AsyncSession, table_name: str) -> bool:
    result = await session.execute(
        text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :t)"),
        {"t": table_name},
    )
    return result.scalar() or False


async def get_summary(session: AsyncSession, date_from: date, date_to: date) -> MetricsSummaryOut:
    start, end = _range_bounds(date_from, date_to)

    has_visits = await _table_exists(session, "site_visits")
    has_shipments = await _table_exists(session, "shipments")

    if has_visits:
        clicks_row = (
            await session.execute(
                select(
                    func.count().filter(SiteVisit.event_type == "page_view"),
                    func.count().filter(SiteVisit.event_type == "cta_click"),
                ).where(
                    SiteVisit.created_at.between(start, end),
                    SiteVisit.is_valid_ma.is_(True),
                )
            )
        ).one()
        page_views, cta_clicks = clicks_row
    else:
        log.warning("site_visits table missing — run 'alembic upgrade head'")
        page_views, cta_clicks = 0, 0
    clicks = page_views + cta_clicks

    try:
        orders_row = (
            await session.execute(
                select(
                    func.count(),
                    func.count().filter(Order.is_valid_ma.is_(True)),
                    func.coalesce(func.sum(Order.total_mad), 0),
                    func.count().filter(Order.confirmed_at.is_not(None)),
                    func.count().filter(Order.status == "canceled"),
                    func.count().filter(Order.status == "no_answer"),
                    func.count().filter(Order.upsell_accepted.is_(True)),
                ).where(Order.created_at.between(start, end))
            )
        ).one()
        (
            orders,
            valid_orders,
            revenue_mad,
            confirmed_orders,
            canceled_orders,
            no_answer_orders,
            upsell_orders,
        ) = orders_row
    except Exception:
        await session.rollback()
        log.warning("orders query with is_valid_ma/confirmed_at failed — columns may be missing")
        fallback = (
            await session.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(Order.total_mad), 0),
                    func.count().filter(Order.status == "canceled"),
                    func.count().filter(Order.status == "no_answer"),
                    func.count().filter(Order.upsell_accepted.is_(True)),
                ).where(Order.created_at.between(start, end))
            )
        ).one()
        orders, revenue_mad, canceled_orders, no_answer_orders, upsell_orders = fallback
        valid_orders, confirmed_orders = 0, 0

    if has_shipments:
        shipment_row = (
            await session.execute(
                select(
                    func.count().filter(Shipment.delivery_status == "delivered"),
                    func.count().filter(Shipment.delivery_status == "returned"),
                    func.count().filter(Shipment.delivery_status == "in_transit"),
                    func.count().filter(Shipment.delivery_status == "pending"),
                )
                .join(Order, Order.id == Shipment.order_id)
                .where(Order.created_at.between(start, end))
            )
        ).one()
        delivered_orders, returned_orders, in_transit_orders, pending_shipment_orders = shipment_row
    else:
        log.warning("shipments table missing — run 'alembic upgrade head'")
        delivered_orders, returned_orders, in_transit_orders, pending_shipment_orders = 0, 0, 0, 0

    status_rows = (
        await session.execute(
            select(Order.status, func.count())
            .where(Order.created_at.between(start, end))
            .group_by(Order.status)
            .order_by(func.count().desc())
        )
    ).all()

    city_rows = (
        await session.execute(
            select(Order.city, func.count())
            .where(Order.created_at.between(start, end))
            .group_by(Order.city)
            .order_by(func.count().desc())
            .limit(8)
        )
    ).all()

    source_rows = (
        await session.execute(
            select(func.coalesce(Order.source_page, "direct"), func.count())
            .where(Order.created_at.between(start, end))
            .group_by(func.coalesce(Order.source_page, "direct"))
            .order_by(func.count().desc())
            .limit(8)
        )
    ).all()

    product_rows = (
        await session.execute(
            select(OrderItem.name, func.coalesce(func.sum(OrderItem.quantity), 0))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.created_at.between(start, end))
            .group_by(OrderItem.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(8)
        )
    ).all()

    delivered_plus_returned = delivered_orders + returned_orders
    conversion_rate = (valid_orders / clicks * 100) if clicks else 0.0
    confirmation_rate = (confirmed_orders / orders * 100) if orders else 0.0
    delivery_rate = (delivered_orders / delivered_plus_returned * 100) if delivered_plus_returned else 0.0
    upsell_rate = (upsell_orders / orders * 100) if orders else 0.0
    aov_mad = (revenue_mad / orders) if orders else 0.0

    return MetricsSummaryOut(
        date_from=date_from,
        date_to=date_to,
        clicks=clicks,
        page_views=page_views,
        cta_clicks=cta_clicks,
        orders=orders,
        valid_orders=valid_orders,
        revenue_mad=int(revenue_mad),
        aov_mad=round(aov_mad, 2),
        conversion_rate=round(conversion_rate, 2),
        confirmation_rate=round(confirmation_rate, 2),
        delivery_rate=round(delivery_rate, 2),
        upsell_rate=round(upsell_rate, 2),
        confirmed_orders=confirmed_orders,
        canceled_orders=canceled_orders,
        no_answer_orders=no_answer_orders,
        delivered_orders=delivered_orders,
        returned_orders=returned_orders,
        in_transit_orders=in_transit_orders,
        pending_shipment_orders=pending_shipment_orders,
        by_status=[BreakdownItemOut(label=s or "unknown", value=c) for s, c in status_rows],
        top_cities=[BreakdownItemOut(label=c or "unknown", value=n) for c, n in city_rows],
        top_sources=[BreakdownItemOut(label=s or "direct", value=n) for s, n in source_rows],
        top_products=[BreakdownItemOut(label=p, value=int(n)) for p, n in product_rows],
    )


async def get_timeseries(session: AsyncSession, date_from: date, date_to: date) -> MetricsTimeseriesOut:
    start, end = _range_bounds(date_from, date_to)

    has_visits = await _table_exists(session, "site_visits")
    if has_visits:
        click_rows = (
            await session.execute(
                select(
                    func.date(SiteVisit.created_at),
                    func.count().filter(SiteVisit.event_type == "page_view"),
                    func.count().filter(SiteVisit.event_type == "cta_click"),
                )
                .where(SiteVisit.created_at.between(start, end), SiteVisit.is_valid_ma.is_(True))
                .group_by(func.date(SiteVisit.created_at))
            )
        ).all()
    else:
        click_rows = []

    order_rows = (
        await session.execute(
            select(
                func.date(Order.created_at),
                func.count(),
                func.coalesce(func.sum(Order.total_mad), 0),
            )
            .where(Order.created_at.between(start, end))
            .group_by(func.date(Order.created_at))
        )
    ).all()

    clicks_by_day: dict[date, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for d, page_views, cta_clicks in click_rows:
        clicks_by_day[_as_date(d)] = (page_views, cta_clicks)

    orders_by_day: dict[date, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for d, count, revenue in order_rows:
        orders_by_day[_as_date(d)] = (count, int(revenue))

    points: list[DailyPointOut] = []
    current = date_from
    while current <= date_to:
        page_views, cta_clicks = clicks_by_day[current]
        orders, revenue_mad = orders_by_day[current]
        points.append(
            DailyPointOut(
                date=current,
                clicks=page_views + cta_clicks,
                page_views=page_views,
                cta_clicks=cta_clicks,
                orders=orders,
                revenue_mad=revenue_mad,
            )
        )
        current += timedelta(days=1)

    return MetricsTimeseriesOut(date_from=date_from, date_to=date_to, points=points)


def _as_date(value: date | datetime) -> date:
    return value if isinstance(value, date) and not isinstance(value, datetime) else value.date()
