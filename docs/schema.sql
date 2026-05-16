-- =============================================================================
-- D2C AI Employee — Database Schema
-- =============================================================================
-- Run this file against a fresh Supabase project to build the entire database.
-- Paste into the Supabase SQL Editor and click Run.
--
-- Multi-tenancy note (v0):
--   Credentials and config are per-merchant via merchant_id.
--   Data tables (orders, products, etc.) are currently shared — this is
--   intentional for v0 where each deployment serves one brand.
--   Full isolation requires adding merchant_id to each data table and
--   including it in every upsert conflict key (v1 work).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Safe reset: drop everything before recreating
DROP TABLE IF EXISTS agent_runs           CASCADE;
DROP TABLE IF EXISTS order_items          CASCADE;
DROP TABLE IF EXISTS orders               CASCADE;
DROP TABLE IF EXISTS customers            CASCADE;
DROP TABLE IF EXISTS products             CASCADE;
DROP TABLE IF EXISTS ad_spend             CASCADE;
DROP TABLE IF EXISTS inventory            CASCADE;
DROP TABLE IF EXISTS raw_material_costs   CASCADE;
DROP TABLE IF EXISTS vendors              CASCADE;
DROP TABLE IF EXISTS monthly_budget       CASCADE;
DROP TABLE IF EXISTS merchant_config      CASCADE;
DROP TABLE IF EXISTS merchant_credentials CASCADE;

-- =============================================================================
-- merchant_credentials
-- Per-merchant connector credentials written by the Settings UI.
-- Read fresh on every sync call — no backend restart needed.
-- =============================================================================
CREATE TABLE merchant_credentials (
    merchant_id TEXT        NOT NULL,
    connector   TEXT        NOT NULL,
    creds       JSONB       NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ          DEFAULT now(),
    PRIMARY KEY (merchant_id, connector)
);

-- =============================================================================
-- merchant_config
-- Key/value config per merchant (spend alerts, thresholds, etc.).
-- =============================================================================
CREATE TABLE merchant_config (
    merchant_id TEXT        NOT NULL DEFAULT 'default',
    key         TEXT        NOT NULL,
    value       JSONB       NOT NULL,
    updated_at  TIMESTAMPTZ          DEFAULT now(),
    PRIMARY KEY (merchant_id, key)
);

-- =============================================================================
-- customers
-- One row per unique customer. external_id is the source-system identifier
-- (e.g. Shopify customer GID). orders_count and total_spent are written by
-- the Shopify connector and used by the agent to compute repeat-buyer rate.
-- =============================================================================
CREATE TABLE customers (
    id            BIGSERIAL    PRIMARY KEY,
    external_id   TEXT         NOT NULL,
    email         TEXT,
    first_name    TEXT,
    last_name     TEXT,
    orders_count  INT4,
    total_spent   NUMERIC(12, 2),
    created_at    TIMESTAMPTZ,
    source        TEXT         NOT NULL,
    source_id     TEXT,
    synced_at     TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (source, external_id)
);

-- =============================================================================
-- products
-- One row per product variant. handle is the Shopify URL slug used for
-- deduplication when the same product is referenced by multiple connectors.
-- =============================================================================
CREATE TABLE products (
    id                  BIGSERIAL    PRIMARY KEY,
    external_id         TEXT         NOT NULL,
    title               TEXT,
    handle              TEXT,
    sku                 TEXT,
    price               NUMERIC(12, 2),
    inventory_quantity  INT4,
    created_at          TIMESTAMPTZ,
    source              TEXT         NOT NULL,
    source_id           TEXT,
    synced_at           TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (source, external_id)
);

-- =============================================================================
-- orders
-- customer_id is a TEXT field storing the source-system customer identifier,
-- NOT a foreign key to customers.id. Shopify customer IDs are string GIDs
-- and arrive before the customer row may exist in the DB.
-- =============================================================================
CREATE TABLE orders (
    id                  BIGSERIAL    PRIMARY KEY,
    external_id         TEXT         NOT NULL,
    customer_id         TEXT,
    total_price         NUMERIC(12, 2),
    financial_status    TEXT,
    fulfillment_status  TEXT,
    created_at          TIMESTAMPTZ,
    source              TEXT         NOT NULL,
    source_id           TEXT,
    synced_at           TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (source, external_id)
);

-- =============================================================================
-- order_items
-- order_id and product_id are TEXT source-system identifiers, not integer FKs.
-- The upsert conflict key is source_id (the line-item GID from Shopify).
-- =============================================================================
CREATE TABLE order_items (
    id          BIGSERIAL    PRIMARY KEY,
    source_id   TEXT         NOT NULL,
    order_id    TEXT,
    product_id  TEXT,
    title       TEXT,
    sku         TEXT,
    quantity    INT4,
    price       NUMERIC(12, 2),
    total       NUMERIC(12, 2),
    source      TEXT         NOT NULL,
    synced_at   TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (source_id)
);

-- =============================================================================
-- ad_spend
-- Daily campaign performance. Conflict key is (source, date, platform,
-- campaign_name) so re-running sync on the same day is idempotent.
-- =============================================================================
CREATE TABLE ad_spend (
    id             BIGSERIAL    PRIMARY KEY,
    date           DATE         NOT NULL,
    platform       TEXT         NOT NULL,
    campaign_name  TEXT,
    spend          NUMERIC(12, 2),
    impressions    INT4,
    clicks         INT4,
    purchases      INT4,
    source         TEXT         NOT NULL,
    source_id      TEXT,
    synced_at      TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (source, date, platform, campaign_name)
);

-- =============================================================================
-- inventory
-- Current stock levels per SKU from Google Sheets.
-- =============================================================================
CREATE TABLE inventory (
    id             BIGSERIAL    PRIMARY KEY,
    sku            TEXT         NOT NULL,
    product_name   TEXT,
    current_stock  INT4,
    reorder_level  INT4,
    reorder_qty    INT4,
    unit_cost      NUMERIC(12, 2),
    location       TEXT,
    last_updated   DATE,
    source         TEXT         NOT NULL,
    source_id      TEXT,
    synced_at      TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (source, sku)
);

-- =============================================================================
-- raw_material_costs
-- Cost-per-unit for raw materials from Google Sheets.
-- =============================================================================
CREATE TABLE raw_material_costs (
    id                  BIGSERIAL    PRIMARY KEY,
    material            TEXT         NOT NULL,
    vendor_name         TEXT         NOT NULL,
    unit                TEXT,
    cost_per_unit       NUMERIC(12, 2),
    monthly_usage       NUMERIC(12, 2),
    monthly_cost        NUMERIC(12, 2),
    last_purchase_date  DATE,
    notes               TEXT,
    source              TEXT         NOT NULL,
    source_id           TEXT,
    synced_at           TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (material, vendor_name)
);

-- =============================================================================
-- vendors
-- Supplier directory from Google Sheets.
-- =============================================================================
CREATE TABLE vendors (
    id               BIGSERIAL    PRIMARY KEY,
    vendor_name      TEXT         NOT NULL,
    category         TEXT,
    contact_person   TEXT,
    phone            TEXT,
    email            TEXT,
    payment_terms    TEXT,
    lead_time_days   INT4,
    rating           NUMERIC(3, 1),
    notes            TEXT,
    source           TEXT         NOT NULL,
    source_id        TEXT,
    synced_at        TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (source, vendor_name)
);

-- =============================================================================
-- monthly_budget
-- Planned vs. actual spend by category and month from Google Sheets.
-- month is TEXT to accept whatever format the spreadsheet uses (e.g. "2024-01").
-- =============================================================================
CREATE TABLE monthly_budget (
    id         BIGSERIAL    PRIMARY KEY,
    month      TEXT         NOT NULL,
    category   TEXT         NOT NULL,
    budgeted   NUMERIC(12, 2),
    actual     NUMERIC(12, 2),
    variance   NUMERIC(12, 2),
    notes      TEXT,
    source     TEXT         NOT NULL,
    source_id  TEXT,
    synced_at  TIMESTAMPTZ  DEFAULT now(),
    UNIQUE (month, category)
);

-- =============================================================================
-- agent_runs
-- Audit log for every autonomous agent check and manual annotation.
-- citations: [{table, id}, ...] verified against the DB before storage.
-- =============================================================================
CREATE TABLE agent_runs (
    id               BIGSERIAL    PRIMARY KEY,
    check_name       TEXT         NOT NULL,
    status           TEXT         NOT NULL,
    reasoning        TEXT,
    proposed_action  TEXT,
    citations        JSONB                 DEFAULT '[]',
    created_at       TIMESTAMPTZ  DEFAULT now()
);

-- =============================================================================
-- Indexes
-- Data tables are queried by date, source, and status frequently.
-- =============================================================================
CREATE INDEX idx_orders_customer_id      ON orders(customer_id);
CREATE INDEX idx_orders_created_at       ON orders(created_at);
CREATE INDEX idx_order_items_order_id    ON order_items(order_id);
CREATE INDEX idx_order_items_product_id  ON order_items(product_id);
CREATE INDEX idx_ad_spend_date           ON ad_spend(date);
CREATE INDEX idx_agent_runs_created_at   ON agent_runs(created_at);
