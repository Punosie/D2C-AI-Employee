-- ─────────────────────────────────────────────────────────────────────────────
-- Universal Normalized Schema — D2C AI Employee
-- Source-independent. Provenance on every row.
-- ─────────────────────────────────────────────────────────────────────────────


-- Customers
CREATE TABLE customers (
    id          BIGSERIAL PRIMARY KEY,
    external_id TEXT NOT NULL,
    email       TEXT,
    first_name  TEXT,
    last_name   TEXT,
    phone       TEXT,
    city        TEXT,
    source      TEXT NOT NULL,
    source_id   TEXT,
    synced_at   TIMESTAMPTZ DEFAULT NOW(),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, external_id)
);

-- Products
CREATE TABLE products (
    id                 BIGSERIAL PRIMARY KEY,
    external_id        TEXT NOT NULL,
    title              TEXT,
    sku                TEXT,
    price              NUMERIC(10, 2),
    inventory_quantity INT,
    source             TEXT NOT NULL,
    source_id          TEXT,
    synced_at          TIMESTAMPTZ DEFAULT NOW(),
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, external_id)
);

-- Orders
CREATE TABLE orders (
    id                 BIGSERIAL PRIMARY KEY,
    external_id        TEXT NOT NULL,
    customer_id        BIGINT REFERENCES customers(id),
    total_price        NUMERIC(10, 2),
    financial_status   TEXT,
    fulfillment_status TEXT,
    source             TEXT NOT NULL,
    source_id          TEXT,
    synced_at          TIMESTAMPTZ DEFAULT NOW(),
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, external_id)
);

-- Order Items
CREATE TABLE order_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT NOT NULL REFERENCES orders(id),
    product_id  BIGINT REFERENCES products(id),
    title       TEXT,
    sku         TEXT,
    quantity    INT,
    price       NUMERIC(10, 2),
    total       NUMERIC(10, 2),
    source      TEXT NOT NULL,
    source_id   TEXT,
    synced_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_id)
);

-- Ad Spend
CREATE TABLE ad_spend (
    id            BIGSERIAL PRIMARY KEY,
    date          DATE NOT NULL,
    platform      TEXT NOT NULL,
    campaign_name TEXT,
    spend         NUMERIC(10, 2),
    impressions   INT,
    clicks        INT,
    purchases     INT,
    source        TEXT NOT NULL,
    source_id     TEXT,
    synced_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, date, platform, campaign_name)
);

-- Inventory
CREATE TABLE inventory (
    id            BIGSERIAL PRIMARY KEY,
    sku           TEXT NOT NULL,
    product_name  TEXT,
    current_stock INT,
    reorder_level INT,
    reorder_qty   INT,
    unit_cost     NUMERIC(10, 2),
    location      TEXT,
    last_updated  DATE,
    source        TEXT NOT NULL,
    source_id     TEXT,
    synced_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, sku)
);

-- Raw Material Costs
CREATE TABLE raw_material_costs (
    id                 BIGSERIAL PRIMARY KEY,
    material           TEXT NOT NULL,
    vendor_name        TEXT,
    unit               TEXT,
    cost_per_unit      NUMERIC(10, 2),
    monthly_usage      NUMERIC(10, 2),
    monthly_cost       NUMERIC(10, 2),
    last_purchase_date DATE,
    notes              TEXT,
    source             TEXT NOT NULL,
    source_id          TEXT,
    synced_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (material, vendor_name)
);

-- Vendors
CREATE TABLE vendors (
    id             BIGSERIAL PRIMARY KEY,
    vendor_name    TEXT NOT NULL,
    category       TEXT,
    contact_person TEXT,
    phone          TEXT,
    email          TEXT,
    payment_terms  TEXT,
    lead_time_days INT,
    rating         INT,
    notes          TEXT,
    source         TEXT NOT NULL,
    source_id      TEXT,
    synced_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, vendor_name)
);

-- Monthly Budget
CREATE TABLE monthly_budget (
    id        BIGSERIAL PRIMARY KEY,
    month     TEXT NOT NULL,
    category  TEXT NOT NULL,
    budgeted  NUMERIC(10, 2),
    actual    NUMERIC(10, 2),
    variance  NUMERIC(10, 2),
    notes     TEXT,
    source    TEXT NOT NULL,
    source_id TEXT,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (month, category)
);

-- Agent Run Log
CREATE TABLE agent_runs (
    id              BIGSERIAL PRIMARY KEY,
    ran_at          TIMESTAMPTZ DEFAULT NOW(),
    check_name      TEXT NOT NULL,
    status          TEXT NOT NULL,
    reasoning       TEXT,
    proposed_action TEXT,
    citations       JSONB
);

-- Indexes (FK columns — not auto-indexed by Postgres)
CREATE INDEX idx_orders_customer_id     ON orders(customer_id);
CREATE INDEX idx_order_items_order_id   ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
