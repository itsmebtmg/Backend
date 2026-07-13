from pydantic import BaseModel, Field


class VisitIn(BaseModel):
    event_type: str = Field(pattern="^(page_view|cta_click|heartbeat)$")
    session_id: str | None = Field(default=None, max_length=80)
    path: str | None = None
    source_page: str | None = None
    referrer: str | None = None

    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None

    fbp: str | None = None
    fbc: str | None = None
    ttclid: str | None = None
    ttp: str | None = None
    snap_click_id: str | None = None


class VisitOut(BaseModel):
    ok: bool = True
