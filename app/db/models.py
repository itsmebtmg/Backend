import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)

    customer_name: Mapped[str] = mapped_column(String(120))
    phone_raw: Mapped[str] = mapped_column(String(32))
    phone_local: Mapped[str] = mapped_column(String(16), index=True)
    phone_e164: Mapped[str] = mapped_column(String(20))
    phone_digits: Mapped[str] = mapped_column(String(20))
    city: Mapped[str] = mapped_column(String(80))
    address: Mapped[str] = mapped_column(Text)

    subtotal_mad: Mapped[int] = mapped_column(Integer)
    discount_mad: Mapped[int] = mapped_column(Integer, default=0)
    shipping_mad: Mapped[int] = mapped_column(Integer, default=0)
    total_mad: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="MAD")
    payment_method: Mapped[str] = mapped_column(String(16), default="COD")

    source_page: Mapped[str | None] = mapped_column(Text)
    landing_url: Mapped[str | None] = mapped_column(Text)
    utm_source: Mapped[str | None] = mapped_column(String(120))
    utm_medium: Mapped[str | None] = mapped_column(String(120))
    utm_campaign: Mapped[str | None] = mapped_column(String(160))
    utm_content: Mapped[str | None] = mapped_column(String(160))
    utm_term: Mapped[str | None] = mapped_column(String(160))

    fbp: Mapped[str | None] = mapped_column(Text)
    fbc: Mapped[str | None] = mapped_column(Text)
    ttclid: Mapped[str | None] = mapped_column(Text)
    ttp: Mapped[str | None] = mapped_column(Text)
    snap_click_id: Mapped[str | None] = mapped_column(Text)
    client_user_agent: Mapped[str | None] = mapped_column(Text)
    client_ip: Mapped[str | None] = mapped_column(INET)
    event_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    upsell_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Set the first time status transitions to "confirmed" — the source of
    # truth for the admin dashboard's confirmation rate, independent of
    # whatever the order's *current* status later becomes (delivered, etc).
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Server-side geo/VPN verdict computed at order-creation time (MaxMind),
    # mirroring the check already done client-side in the storefront's
    # submitOrder action. Used to flag/filter suspicious orders in reporting
    # without blocking checkout a second time.
    geo_country: Mapped[str | None] = mapped_column(String(2))
    is_valid_ma: Mapped[bool | None] = mapped_column(Boolean)
    is_vpn: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    shipment: Mapped["Shipment | None"] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(String(80))
    product_slug: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_mad: Mapped[int] = mapped_column(Integer)
    line_total_mad: Mapped[int] = mapped_column(Integer)
    is_free_gift: Mapped[bool] = mapped_column(Boolean, default=False)
    offer_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="items")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(80))
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    event_id: Mapped[str] = mapped_column(String(120), index=True)
    platform: Mapped[str] = mapped_column(String(40))
    event_name: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSONB)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SiteVisit(Base):
    """A single storefront page view or CTA click, used to compute clicks and
    conversion rate on the admin dashboard. Only rows with is_valid_ma=True and
    is_vpn=False are counted as "clicks" — everything else is kept for
    auditing/debugging but excluded from reported metrics.
    """

    __tablename__ = "site_visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(20), index=True)  # page_view | cta_click
    session_id: Mapped[str | None] = mapped_column(String(80), index=True)
    path: Mapped[str | None] = mapped_column(Text)
    source_page: Mapped[str | None] = mapped_column(Text)
    referrer: Mapped[str | None] = mapped_column(Text)

    utm_source: Mapped[str | None] = mapped_column(String(120))
    utm_medium: Mapped[str | None] = mapped_column(String(120))
    utm_campaign: Mapped[str | None] = mapped_column(String(160))
    utm_content: Mapped[str | None] = mapped_column(String(160))
    utm_term: Mapped[str | None] = mapped_column(String(160))

    fbp: Mapped[str | None] = mapped_column(Text)
    fbc: Mapped[str | None] = mapped_column(Text)
    ttclid: Mapped[str | None] = mapped_column(Text)
    ttp: Mapped[str | None] = mapped_column(Text)
    snap_click_id: Mapped[str | None] = mapped_column(Text)

    client_ip: Mapped[str | None] = mapped_column(INET)
    client_user_agent: Mapped[str | None] = mapped_column(Text)
    country_iso: Mapped[str | None] = mapped_column(String(2))
    is_valid_ma: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_vpn: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Shipment(Base):
    """Delivery tracking for an order. delivery_status is edited manually by
    the admin today; once a shipping-company API is wired in (see
    app/services/shipping.py), it can be synced automatically instead.
    """

    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, index=True
    )
    carrier: Mapped[str | None] = mapped_column(String(80))
    tracking_number: Mapped[str | None] = mapped_column(String(120))
    delivery_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    cod_amount_mad: Mapped[int | None] = mapped_column(Integer)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="shipment")
