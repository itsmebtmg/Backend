from typing import Literal

from pydantic import BaseModel, Field


class CustomerIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=32)
    city: str = Field(default="Non précisée", min_length=2, max_length=80)
    address: str = Field(min_length=1, max_length=300)


class OrderItemIn(BaseModel):
    sku: str
    product_slug: str
    name: str
    quantity: int = Field(ge=1, le=10)
    unit_price_mad: int = Field(ge=0)
    is_free_gift: bool = False
    offer_code: str | None = None


class OfferIn(BaseModel):
    code: str = "STANDARD"
    upsell_accepted: bool = False


class TrackingIn(BaseModel):
    event_id: str | None = None
    fbp: str | None = None
    fbc: str | None = None
    ttclid: str | None = None
    ttp: str | None = None
    snap_click_id: str | None = None
    client_user_agent: str | None = None


class OrderCreate(BaseModel):
    event_id: str
    source_page: str | None = None
    landing_url: str | None = None
    customer: CustomerIn
    items: list[OrderItemIn] = Field(min_length=1)
    offer: OfferIn = Field(default_factory=OfferIn)
    tracking: TrackingIn = Field(default_factory=TrackingIn)
    # upsell_pending: base order saved while customer sees upsell (abandonment capture)
    # final: checkout complete — updates the same event_id row, fires pixels once
    checkout_phase: Literal["upsell_pending", "final"] = "final"


class OrderCreateResponse(BaseModel):
    ok: bool
    order_id: str
    order_number: str
    total_mad: int


class OrderStatusUpdate(BaseModel):
    status: str
    notes: str | None = None


class SheetStatusUpdate(BaseModel):
    """Payload sent by the Google Apps Script onEdit trigger whenever the
    ops team edits the "Status" column (Confirmé, appel 1, annulé, ...)."""

    order_id: str = Field(min_length=1, max_length=64)
    status: str = Field(min_length=1, max_length=64)
    secret: str | None = None


class WhatsAppStatusUpdate(BaseModel):
    """Called by n8n when a customer taps a confirmation button on WhatsApp."""

    order_id: str = Field(min_length=1, max_length=64)
    action: Literal["confirm", "cancel", "modify"]
    secret: str | None = None


class WhatsAppUpsellUpdate(BaseModel):
    """Called by n8n when a Lumea+-only customer accepts/declines the WhatsApp upsell."""

    order_id: str = Field(min_length=1, max_length=64)
    accepted: bool
    secret: str | None = None


class WhatsAppLookupIn(BaseModel):
    """Resolve the active order for an inbound WhatsApp reply (buttons use static payloads)."""

    phone: str = Field(min_length=8, max_length=32)
    secret: str | None = None


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "solyra-api"
