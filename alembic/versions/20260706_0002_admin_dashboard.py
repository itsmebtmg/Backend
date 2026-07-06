"""admin dashboard: site_visits, shipments, order flags

Revision ID: 20260706_0002
Revises: 20260706_0001
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260706_0002"
down_revision: str | None = "20260706_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("geo_country", sa.String(length=2), nullable=True))
    op.add_column("orders", sa.Column("is_valid_ma", sa.Boolean(), nullable=True))
    op.add_column("orders", sa.Column("is_vpn", sa.Boolean(), nullable=True))

    op.create_table(
        "site_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Text(), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
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
        sa.Column("client_ip", postgresql.INET(), nullable=True),
        sa.Column("client_user_agent", sa.Text(), nullable=True),
        sa.Column("country_iso", sa.String(length=2), nullable=True),
        sa.Column("is_valid_ma", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_vpn", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_site_visits_event_type", "site_visits", ["event_type"])
    op.create_index("ix_site_visits_session_id", "site_visits", ["session_id"])
    op.create_index("ix_site_visits_is_valid_ma", "site_visits", ["is_valid_ma"])
    op.create_index("ix_site_visits_created_at", "site_visits", ["created_at"])

    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("carrier", sa.String(length=80), nullable=True),
        sa.Column("tracking_number", sa.String(length=120), nullable=True),
        sa.Column("delivery_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("cod_amount_mad", sa.Integer(), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"], unique=True)
    op.create_index("ix_shipments_delivery_status", "shipments", ["delivery_status"])


def downgrade() -> None:
    op.drop_index("ix_shipments_delivery_status", table_name="shipments")
    op.drop_index("ix_shipments_order_id", table_name="shipments")
    op.drop_table("shipments")

    op.drop_index("ix_site_visits_created_at", table_name="site_visits")
    op.drop_index("ix_site_visits_is_valid_ma", table_name="site_visits")
    op.drop_index("ix_site_visits_session_id", table_name="site_visits")
    op.drop_index("ix_site_visits_event_type", table_name="site_visits")
    op.drop_table("site_visits")

    op.drop_column("orders", "is_vpn")
    op.drop_column("orders", "is_valid_ma")
    op.drop_column("orders", "geo_country")
    op.drop_column("orders", "confirmed_at")
