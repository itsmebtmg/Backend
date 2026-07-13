import logging
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin import LiveVisitorsOut, MetricsSummaryOut, MetricsTimeseriesOut
from app.services import metrics as metrics_service
from app.services.auth import AdminSession, require_admin

log = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics", tags=["admin-metrics"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
Admin = Annotated[AdminSession, Depends(require_admin)]


def _default_range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    resolved_to = date_to or date.today()
    resolved_from = date_from or (resolved_to - timedelta(days=6))
    return resolved_from, resolved_to


@router.get("/summary", response_model=MetricsSummaryOut)
async def summary(
    session: DbSession,
    _admin: Admin,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> MetricsSummaryOut:
    resolved_from, resolved_to = _default_range(date_from, date_to)
    try:
        return await metrics_service.get_summary(session, resolved_from, resolved_to)
    except Exception as exc:
        log.exception("metrics summary failed")
        return MetricsSummaryOut(
            date_from=resolved_from,
            date_to=resolved_to,
            clicks=0,
            page_views=0,
            cta_clicks=0,
            orders=0,
            valid_orders=0,
            revenue_mad=0,
            aov_mad=0,
            conversion_rate=0,
            confirmation_rate=0,
            delivery_rate=0,
            upsell_rate=0,
            confirmed_orders=0,
            canceled_orders=0,
            no_answer_orders=0,
            delivered_orders=0,
            returned_orders=0,
            in_transit_orders=0,
            pending_shipment_orders=0,
            by_status=[],
            top_cities=[],
            top_sources=[],
            top_products=[],
        )


@router.get("/timeseries", response_model=MetricsTimeseriesOut)
async def timeseries(
    session: DbSession,
    _admin: Admin,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> MetricsTimeseriesOut:
    resolved_from, resolved_to = _default_range(date_from, date_to)
    try:
        return await metrics_service.get_timeseries(session, resolved_from, resolved_to)
    except Exception as exc:
        log.exception("metrics timeseries failed")
        return MetricsTimeseriesOut(date_from=resolved_from, date_to=resolved_to, points=[])


@router.get("/live", response_model=LiveVisitorsOut)
async def live_visitors(session: DbSession, _admin: Admin) -> LiveVisitorsOut:
    try:
        return await metrics_service.get_live_visitors(session)
    except Exception:
        log.exception("live visitors failed")
        return LiveVisitorsOut(
            live_now=0,
            live_valid_ma=0,
            window_minutes=metrics_service.LIVE_VISITOR_WINDOW_MINUTES,
            as_of=datetime.now(tz=timezone.utc),
        )
