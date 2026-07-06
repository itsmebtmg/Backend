from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SiteVisit
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.tracking import VisitIn, VisitOut
from app.services import geo

router = APIRouter(prefix="/tracking", tags=["tracking"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/visit", response_model=VisitOut, status_code=202)
async def record_visit(payload: VisitIn, request: Request, background_tasks: BackgroundTasks) -> VisitOut:
    client_ip = geo.client_ip_from_headers(
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )
    user_agent = request.headers.get("user-agent")

    # Fire-and-forget: never let click tracking slow down or fail the page.
    background_tasks.add_task(_store_visit, payload, client_ip, user_agent)
    return VisitOut(ok=True)


async def _store_visit(payload: VisitIn, client_ip: str | None, user_agent: str | None) -> None:
    verdict = await geo.check_ip(client_ip)
    async with AsyncSessionLocal() as session:
        session.add(
            SiteVisit(
                event_type=payload.event_type,
                session_id=payload.session_id,
                path=payload.path,
                source_page=payload.source_page,
                referrer=payload.referrer,
                utm_source=payload.utm_source,
                utm_medium=payload.utm_medium,
                utm_campaign=payload.utm_campaign,
                utm_content=payload.utm_content,
                utm_term=payload.utm_term,
                fbp=payload.fbp,
                fbc=payload.fbc,
                ttclid=payload.ttclid,
                ttp=payload.ttp,
                snap_click_id=payload.snap_click_id,
                client_ip=client_ip,
                client_user_agent=user_agent,
                country_iso=verdict.country_iso,
                is_valid_ma=verdict.is_valid_ma,
                is_vpn=verdict.is_vpn,
            )
        )
        await session.commit()
