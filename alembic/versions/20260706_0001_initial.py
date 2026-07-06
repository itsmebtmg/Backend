"""initial schema

Revision ID: 20260706_0001
Revises:
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260706_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("phone_raw", sa.String(length=32), nullable=False),
        sa.Column("phone_local", sa.String(length=16), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("phone_digits", sa.String(length=20), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("subtotal_mad", sa.Integer(), nullable=False),
        sa.Column("discount_mad", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shipping_mad", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_mad", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="MAD"),
        sa.Column("payment_method", sa.String(length=16), nullable=False, server_default="COD"),
        sa.Column("source_page", sa.Text(), nullable=True),
        sa.Column("landing_url", sa.Text(), nullable=True),
        sa.Column("utm_source", sa.String(length=120), nullable=True),
        sa.Column("utm_medium", sa.String(length=120), nullable=True),
        sa.Column("utm_campaign", sa.String(length=160), nullable=True),
        sa.Column("utm_content", sa.String(length=160), nullable=True),
        sa.Column("utm_term", sa.String(length=160), nullable=True),
        sa.Column("fbp", sa.Text(), nullable=True),
        sa.Column("fbc", sa.Text(), nullable=True),
        sa.Column("ttclid", sa.Text(), nullable=True),
        sa.Column("ttp", sa.Text(), nullable=True),
        sa.Column("snap_click_id", sa.Text(), nullable=True),
        sa.Column("client_user_agent", sa.Text(), nullable=True),
        sa.Column("client_ip", postgresql.INET(), nullable=True),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("upsell_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)
    op.create_index("ix_orders_event_id", "orders", ["event_id"], unique=True)
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_phone_local", "orders", ["phone_local"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("product_slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_mad", sa.Integer(), nullable=False),
        sa.Column("line_total_mad", sa.Integer(), nullable=False),
        sa.Column("is_free_gift", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("offer_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "order_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("event_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tracking_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tracking_events_event_id", "tracking_events", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_tracking_events_event_id", table_name="tracking_events")
    op.drop_table("tracking_events")
    op.drop_table("order_events")
    op.drop_table("order_items")
    op.drop_index("ix_orders_phone_local", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_event_id", table_name="orders")
    op.drop_index("ix_orders_order_number", table_name="orders")
    op.drop_table("orders")
