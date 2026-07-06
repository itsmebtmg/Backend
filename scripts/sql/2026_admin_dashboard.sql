-- Solyra Admin Dashboard — schema migration
-- Run this once against your Postgres database if you are not using Alembic.
-- Equivalent to alembic revision 20260706_0002_admin_dashboard.
--
-- Usage:
--   psql "$DATABASE_URL" -f backend/scripts/sql/2026_admin_dashboard.sql
--
-- This file is idempotent (safe to re-run) thanks to IF NOT EXISTS guards.

BEGIN;

-- 1. New columns on orders -----------------------------------------------

ALTER TABLE orders ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS geo_country VARCHAR(2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_valid_ma BOOLEAN;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_vpn BOOLEAN;

-- 2. site_visits — page views / CTA clicks, used for the "clicks" metric --

CREATE TABLE IF NOT EXISTS site_visits (
    id UUID PRIMARY KEY,
    event_type VARCHAR(20) NOT NULL,           -- 'page_view' | 'cta_click'
    session_id VARCHAR(80),
    path TEXT,
    source_page TEXT,
    referrer TEXT,
    utm_source VARCHAR(120),
    utm_medium VARCHAR(120),
    utm_campaign VARCHAR(160),
    utm_content VARCHAR(160),
    utm_term VARCHAR(160),
    fbp TEXT,
    fbc TEXT,
    ttclid TEXT,
    ttp TEXT,
    snap_click_id TEXT,
    client_ip INET,
    client_user_agent TEXT,
    country_iso VARCHAR(2),
    is_valid_ma BOOLEAN NOT NULL DEFAULT FALSE, -- true only for non-VPN Moroccan IPs (MaxMind)
    is_vpn BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_site_visits_event_type ON site_visits (event_type);
CREATE INDEX IF NOT EXISTS ix_site_visits_session_id ON site_visits (session_id);
CREATE INDEX IF NOT EXISTS ix_site_visits_is_valid_ma ON site_visits (is_valid_ma);
CREATE INDEX IF NOT EXISTS ix_site_visits_created_at ON site_visits (created_at);

-- 3. shipments — delivery tracking per order (manual today, API-ready later)

CREATE TABLE IF NOT EXISTS shipments (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    carrier VARCHAR(80),
    tracking_number VARCHAR(120),
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending|in_transit|delivered|returned|failed
    cod_amount_mad INTEGER,
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_shipments_order_id ON shipments (order_id);
CREATE INDEX IF NOT EXISTS ix_shipments_delivery_status ON shipments (delivery_status);

COMMIT;

-- After running this, also stamp Alembic's version table so future
-- `alembic upgrade head` runs don't try to re-apply this migration:
--   UPDATE alembic_version SET version_num = '20260706_0002';
-- (Only needed if you use both Alembic and manual SQL — skip if you only
-- ever run `alembic upgrade head`.)
