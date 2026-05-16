from src.config import settings
from .base import NormalizedRecord, make_session


def fetch_shopify(store_url: str | None = None, api_key: str | None = None, updated_since: str | None = None) -> dict:
    """
    Fetch orders, customers, and products from Shopify.

    Credentials are passed explicitly so they can be loaded fresh per merchant.
    updated_since — ISO timestamp for incremental order sync.
    """
    _store_url = store_url or settings.SHOPIFY_STORE_URL or ""
    _api_key   = api_key   or settings.SHOPIFY_API_KEY   or ""

    session = make_session()
    session.headers["X-Shopify-Access-Token"] = _api_key
    base = f"https://{_store_url}/admin/api/2024-01"

    orders_url = f"{base}/orders.json?status=any&limit=250"
    if updated_since:
        orders_url += f"&updated_at_min={updated_since}"

    return {
        "orders":    _fetch_paginated(session, orders_url, "orders"),
        "customers": _fetch_paginated(session, f"{base}/customers.json?limit=250", "customers"),
        "products":  _fetch_paginated(session, f"{base}/products.json?limit=250", "products"),
    }


def normalize_shopify(raw: dict) -> list[NormalizedRecord]:
    """Normalize all Shopify resources into NormalizedRecords."""
    records = []
    records.extend(_normalize_orders(raw.get("orders", [])))
    records.extend(_normalize_customers(raw.get("customers", [])))
    records.extend(_normalize_products(raw.get("products", [])))
    return records


def sync(merchant_id: str = "default") -> list[NormalizedRecord]:
    """Incremental sync: reads credentials fresh from DB — no restart needed."""
    from src.credentials import get_credentials
    from src.merchant import get_merchant_config, update_merchant_config
    from datetime import datetime, timezone

    creds     = get_credentials(merchant_id).get("shopify", {})
    store_url = creds.get("store_url") or settings.SHOPIFY_STORE_URL
    api_key   = creds.get("api_key")   or settings.SHOPIFY_API_KEY

    if not (store_url and api_key):
        raise ValueError(
            "Shopify not connected. Go to Settings and add your Shopify store details."
        )

    last_sync = get_merchant_config("shopify_last_sync").get("value")
    records   = normalize_shopify(fetch_shopify(store_url, api_key, updated_since=last_sync))
    update_merchant_config("shopify_last_sync", datetime.now(timezone.utc).isoformat())
    return records


# ── Private normalizers ───────────────────────────────────────────────────────

def _normalize_orders(orders: list[dict]) -> list[NormalizedRecord]:
    records = []
    for order in orders:
        customer_external_id = str(order["customer"]["id"]) if order.get("customer") else None
        records.append(NormalizedRecord(
            table="orders",
            data={
                "external_id":        str(order["id"]),
                "customer_id":        customer_external_id,
                "total_price":        order["total_price"],
                "financial_status":   order["financial_status"],
                "fulfillment_status": order.get("fulfillment_status"),
                "created_at":         order["created_at"],
                "source":             "shopify",
                "source_id":          str(order["id"]),
            },
            source="shopify",
            source_id=str(order["id"]),
        ))
        for item in order.get("line_items", []):
            records.append(NormalizedRecord(
                table="order_items",
                data={
                    "source_id":  str(item["id"]),
                    "order_id":   str(order["id"]),
                    "product_id": str(item["product_id"]) if item.get("product_id") else None,
                    "title":      item["title"],
                    "sku":        item.get("sku"),
                    "quantity":   item["quantity"],
                    "price":      item["price"],
                    "total":      float(item["price"]) * item["quantity"],
                    "source":     "shopify",
                },
                source="shopify",
                source_id=str(item["id"]),
            ))
    return records


def _normalize_customers(customers: list[dict]) -> list[NormalizedRecord]:
    records = []
    for c in customers:
        records.append(NormalizedRecord(
            table="customers",
            data={
                "external_id":  str(c["id"]),
                "email":        c.get("email"),
                "first_name":   c.get("first_name"),
                "last_name":    c.get("last_name"),
                "orders_count": c.get("orders_count", 0),
                "total_spent":  c.get("total_spent", "0.00"),
                "created_at":   c["created_at"],
                "source":       "shopify",
                "source_id":    str(c["id"]),
            },
            source="shopify",
            source_id=str(c["id"]),
        ))
    return records


def _normalize_products(products: list[dict]) -> list[NormalizedRecord]:
    records = []
    for p in products:
        first_variant = p["variants"][0] if p.get("variants") else {}
        records.append(NormalizedRecord(
            table="products",
            data={
                "external_id":        str(p["id"]),
                "title":              p["title"],
                "handle":             p.get("handle"),
                "sku":                first_variant.get("sku"),
                "price":              first_variant.get("price"),
                "inventory_quantity": first_variant.get("inventory_quantity", 0),
                "created_at":         p["created_at"],
                "source":             "shopify",
                "source_id":          str(p["id"]),
            },
            source="shopify",
            source_id=str(p["id"]),
        ))
    return records


# ── Pagination helpers ────────────────────────────────────────────────────────

def _fetch_paginated(session, url: str, key: str) -> list[dict]:
    results = []
    while url:
        resp = session.get(url)
        resp.raise_for_status()
        results.extend(resp.json()[key])
        url = _next_page(resp.headers.get("Link"))
    return results


def _next_page(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None
