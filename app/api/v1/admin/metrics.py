import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin import MetricsSummaryOut, MetricsTimeseriesOut
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
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


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
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
