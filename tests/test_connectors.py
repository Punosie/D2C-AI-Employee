"""
Unit tests for connector normalizers and helpers.
These tests use only synthetic data — no live API calls.
"""
import pytest
from src.connectors.shopify import (
    normalize_shopify,
    _normalize_orders,
    _normalize_customers,
    _normalize_products,
    _next_page,
)
from src.connectors.meta_ads import normalize_meta
from src.connectors.google_sheets import _validate_columns


# ── Shopify fixture data ──────────────────────────────────────────────────────

SHOPIFY_ORDER = {
    "id": 5001,
    "customer": {"id": 9001},
    "total_price": "1299.00",
    "financial_status": "paid",
    "fulfillment_status": "fulfilled",
    "created_at": "2026-05-01T10:00:00+05:30",
    "line_items": [
        {
            "id": 8001,
            "product_id": 7001,
            "title": "Sandalwood Candle",
            "sku": "SWC-100",
            "quantity": 2,
            "price": "499.00",
        },
        {
            "id": 8002,
            "product_id": 7002,
            "title": "Rose Candle",
            "sku": "RC-200",
            "quantity": 1,
            "price": "301.00",
        },
    ],
}

SHOPIFY_CUSTOMER = {
    "id": 9001,
    "email": "test@example.com",
    "first_name": "Anika",
    "last_name": "Sharma",
    "orders_count": 3,
    "total_spent": "3897.00",
    "created_at": "2025-12-01T00:00:00+05:30",
}

SHOPIFY_PRODUCT = {
    "id": 7001,
    "title": "Sandalwood Candle",
    "handle": "sandalwood-candle",
    "created_at": "2025-10-01T00:00:00+05:30",
    "variants": [
        {
            "sku": "SWC-100",
            "price": "499.00",
            "inventory_quantity": 42,
        }
    ],
}


# ── Shopify: orders ───────────────────────────────────────────────────────────

def test_normalize_shopify_order_fields():
    records = _normalize_orders([SHOPIFY_ORDER])
    order = next(r for r in records if r.table == "orders")
    assert order.data["external_id"] == "5001"
    assert order.data["customer_id"] == "9001"
    assert order.data["total_price"] == "1299.00"
    assert order.data["financial_status"] == "paid"
    assert order.data["source"] == "shopify"
    assert order.source_id == "5001"


def test_normalize_shopify_order_items_have_foreign_keys():
    records = _normalize_orders([SHOPIFY_ORDER])
    items = [r for r in records if r.table == "order_items"]
    assert len(items) == 2
    for item in items:
        assert item.data["order_id"] == "5001"
    assert items[0].data["product_id"] == "7001"
    assert items[1].data["product_id"] == "7002"


def test_normalize_shopify_order_item_total():
    records = _normalize_orders([SHOPIFY_ORDER])
    items = [r for r in records if r.table == "order_items"]
    sw = next(i for i in items if i.data["sku"] == "SWC-100")
    assert sw.data["total"] == pytest.approx(998.0)


def test_normalize_shopify_order_no_customer():
    order = {**SHOPIFY_ORDER, "customer": None}
    records = _normalize_orders([order])
    o = next(r for r in records if r.table == "orders")
    assert o.data["customer_id"] is None


# ── Shopify: customers ────────────────────────────────────────────────────────

def test_normalize_shopify_customer_fields():
    records = _normalize_customers([SHOPIFY_CUSTOMER])
    assert len(records) == 1
    c = records[0]
    assert c.table == "customers"
    assert c.data["external_id"] == "9001"
    assert c.data["email"] == "test@example.com"
    assert c.data["orders_count"] == 3
    assert c.data["source"] == "shopify"


# ── Shopify: products ─────────────────────────────────────────────────────────

def test_normalize_shopify_product_fields():
    records = _normalize_products([SHOPIFY_PRODUCT])
    assert len(records) == 1
    p = records[0]
    assert p.table == "products"
    assert p.data["external_id"] == "7001"
    assert p.data["title"] == "Sandalwood Candle"
    assert p.data["handle"] == "sandalwood-candle"
    assert p.data["sku"] == "SWC-100"
    assert p.data["inventory_quantity"] == 42
    assert p.data["source"] == "shopify"


def test_normalize_shopify_combines_all_tables():
    raw = {
        "orders":    [SHOPIFY_ORDER],
        "customers": [SHOPIFY_CUSTOMER],
        "products":  [SHOPIFY_PRODUCT],
    }
    records = normalize_shopify(raw)
    tables = {r.table for r in records}
    assert tables == {"orders", "order_items", "customers", "products"}


def test_normalize_shopify_empty_raw():
    records = normalize_shopify({})
    assert records == []


# ── Shopify: pagination ───────────────────────────────────────────────────────

def test_next_page_parses_next_link():
    header = '<https://shop.myshopify.com/admin/api/2024-01/orders.json?page_info=xyz>; rel="next"'
    assert _next_page(header) == "https://shop.myshopify.com/admin/api/2024-01/orders.json?page_info=xyz"


def test_next_page_returns_none_when_previous_only():
    header = '<https://shop.myshopify.com/admin/api/2024-01/orders.json?page_info=abc>; rel="previous"'
    assert _next_page(header) is None


def test_next_page_returns_none_on_empty():
    assert _next_page(None) is None
    assert _next_page("") is None


# ── Meta Ads ──────────────────────────────────────────────────────────────────

META_ROW = {
    "date_start":    "2026-05-01",
    "campaign_name": "Diwali Sale",
    "spend":         "4500.00",
    "impressions":   "90000",
    "clicks":        "3200",
    "actions": [
        {"action_type": "purchase", "value": "42"},
        {"action_type": "add_to_cart", "value": "180"},
    ],
}


def test_normalize_meta_fields():
    records = normalize_meta([META_ROW])
    assert len(records) == 1
    r = records[0]
    assert r.table == "ad_spend"
    assert r.data["platform"] == "meta"
    assert r.data["date"] == "2026-05-01"
    assert r.data["campaign_name"] == "Diwali Sale"
    assert r.data["spend"] == pytest.approx(4500.0)
    assert r.data["impressions"] == 90000
    assert r.data["clicks"] == 3200
    assert r.data["source"] == "meta"


def test_normalize_meta_extracts_purchases():
    records = normalize_meta([META_ROW])
    assert records[0].data["purchases"] == 42


def test_normalize_meta_no_purchases():
    row = {**META_ROW, "actions": [{"action_type": "add_to_cart", "value": "10"}]}
    records = normalize_meta([row])
    assert records[0].data["purchases"] == 0


def test_normalize_meta_source_id_is_deterministic():
    r1 = normalize_meta([META_ROW])[0]
    r2 = normalize_meta([META_ROW])[0]
    assert r1.source_id == r2.source_id


# ── Google Sheets: column validation ─────────────────────────────────────────

def test_validate_columns_passes_with_all_required():
    rows = [{"sku": "A", "product_name": "X", "current_stock": 10,
             "reorder_level": 5, "reorder_qty": 20, "unit_cost": 50.0,
             "location": "Warehouse", "last_updated": "2026-05-01"}]
    # Should not raise
    _validate_columns("Inventory", rows)


def test_validate_columns_raises_on_missing():
    rows = [{"sku": "A", "product_name": "X"}]  # missing most required columns
    with pytest.raises(ValueError, match="missing required columns"):
        _validate_columns("Inventory", rows)


def test_validate_columns_error_message_includes_advice():
    rows = [{"SKU": "A"}]  # wrong header name
    with pytest.raises(ValueError, match="column_aliases"):
        _validate_columns("Inventory", rows)


def test_validate_columns_empty_rows_passes():
    # Empty sheet — no rows to validate
    _validate_columns("Inventory", [])


def test_validate_columns_unknown_sheet_passes():
    # Sheets without a REQUIRED_COLUMNS entry should pass silently
    _validate_columns("SomeNewSheet", [{"foo": "bar"}])
