from datetime import date, datetime

from pydantic import BaseModel, Field

ORDER_STATUSES = (
    "new",
    "upsell_pending",
    "confirmed",
    "no_answer",
    "postponed",
    "canceled",
    "delivered",
    "returned",
    "refunded",
)

DELIVERY_STATUSES = ("pending", "in_transit", "delivered", "returned", "failed")


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class MeOut(BaseModel):
    username: str


class LoginOut(BaseModel):
    username: str
    token: str


class DailyPointOut(BaseModel):
    date: date
    clicks: int
    page_views: int
    cta_clicks: int
    orders: int
    revenue_mad: int


class BreakdownItemOut(BaseModel):
    label: str
    value: int


class MetricsSummaryOut(BaseModel):
    date_from: date
    date_to: date

    clicks: int
    page_views: int
    cta_clicks: int

    orders: int
    valid_orders: int
    revenue_mad: int
    aov_mad: float

    conversion_rate: float
    confirmation_rate: float
    delivery_rate: float
    upsell_rate: float

    confirmed_orders: int
    canceled_orders: int
    no_answer_orders: int
    delivered_orders: int
    returned_orders: int
    in_transit_orders: int
    pending_shipment_orders: int

    by_status: list[BreakdownItemOut]
    top_cities: list[BreakdownItemOut]
    top_sources: list[BreakdownItemOut]
    top_products: list[BreakdownItemOut]


class MetricsTimeseriesOut(BaseModel):
    date_from: date
    date_to: date
    points: list[DailyPointOut]


class OrderItemOut(BaseModel):
    sku: str
    product_slug: str
    name: str
    quantity: int
    unit_price_mad: int
    line_total_mad: int
    is_free_gift: bool
    offer_code: str | None


class ShipmentOut(BaseModel):
    carrier: str | None
    tracking_number: str | None
    delivery_status: str
    cod_amount_mad: int | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    updated_at: datetime


class OrderListItemOut(BaseModel):
    id: str
    order_number: str
    created_at: datetime
    status: str
    confirmed_at: datetime | None
    customer_name: str
    phone_local: str
    city: str
    total_mad: int
    items_summary: str
    is_valid_ma: bool | None
    is_vpn: bool | None
    delivery_status: str | None


class OrderListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[OrderListItemOut]


class OrderEventOut(BaseModel):
    event_type: str
    event_data: dict
    created_at: datetime


class TrackingEventOut(BaseModel):
    platform: str
    event_name: str
    success: bool
    response_status: int | None
    created_at: datetime


class OrderDetailOut(BaseModel):
    id: str
    order_number: str
    status: str
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    customer_name: str
    phone_raw: str
    phone_local: str
    phone_e164: str
    city: str
    address: str

    subtotal_mad: int
    discount_mad: int
    shipping_mad: int
    total_mad: int
    currency: str
    payment_method: str

    source_page: str | None
    landing_url: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None

    fbp: str | None
    fbc: str | None
    ttclid: str | None
    ttp: str | None
    snap_click_id: str | None
    client_ip: str | None
    geo_country: str | None
    is_valid_ma: bool | None
    is_vpn: bool | None

    upsell_accepted: bool
    notes: str | None

    items: list[OrderItemOut]
    events: list[OrderEventOut]
    tracking_events: list[TrackingEventOut]
    shipment: ShipmentOut | None


class OrderStatusUpdateIn(BaseModel):
    status: str = Field(pattern="^(" + "|".join(ORDER_STATUSES) + ")$")
    notes: str | None = None


class ShipmentUpdateIn(BaseModel):
    delivery_status: str = Field(pattern="^(" + "|".join(DELIVERY_STATUSES) + ")$")
    carrier: str | None = None
    tracking_number: str | None = None
    cod_amount_mad: int | None = None
