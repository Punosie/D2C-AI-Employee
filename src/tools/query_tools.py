from src.config import supabase


# ── Read tools ────────────────────────────────────────────────────────────────

def query_sales(from_date: str, to_date: str) -> dict:
    """Return total revenue, order count, and AOV for a date range with source citations."""
    rows = (
        supabase.table("orders")
        .select("id, external_id, total_price, created_at, source, source_id")
        .gte("created_at", from_date)
        .lte("created_at", to_date)
        .execute()
        .data
    )
    total = sum(float(r["total_price"]) for r in rows)
    aov = total / len(rows) if rows else 0
    return {
        "total_revenue": round(total, 2),
        "order_count": len(rows),
        "aov": round(aov, 2),
        "citations": [
            {"table": "orders", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
            for r in rows
        ],
    }


def query_ad_spend(platform: str | None = None, from_date: str | None = None) -> dict:
    """Return spend, ROAS, and CPC by platform with source citations."""
    q = supabase.table("ad_spend").select(
        "id, date, platform, campaign_name, spend, impressions, clicks, purchases, source, source_id"
    )
    if platform:
        q = q.eq("platform", platform)
    if from_date:
        q = q.gte("date", from_date)
    rows = q.execute().data

    total_spend = sum(r["spend"] for r in rows)
    total_purchases = sum(r["purchases"] for r in rows)
    return {
        "total_spend": round(total_spend, 2),
        "total_purchases": total_purchases,
        "roas": round(total_purchases / total_spend, 4) if total_spend else 0,
        "by_campaign": rows,
        "citations": [
            {"table": "ad_spend", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
            for r in rows
        ],
    }


def query_products(limit: int = 10) -> dict:
    """Return top selling products by revenue with source citations."""
    rows = (
        supabase.table("order_items")
        .select("product_id, quantity, total, source, source_id")
        .execute()
        .data
    )
    # aggregate by product_id
    aggregated: dict[str, dict] = {}
    for r in rows:
        pid = str(r["product_id"])
        if pid not in aggregated:
            aggregated[pid] = {"product_id": pid, "total_quantity": 0, "total_revenue": 0.0, "source": r["source"], "source_id": r["source_id"]}
        aggregated[pid]["total_quantity"] += r["quantity"] or 0
        aggregated[pid]["total_revenue"] += float(r["total"] or 0)

    top = sorted(aggregated.values(), key=lambda x: x["total_revenue"], reverse=True)[:limit]
    return {
        "top_products": top,
        "citations": [
            {"table": "order_items", "source": p["source"], "source_id": p["source_id"]}
            for p in top
        ],
    }


def query_customers() -> dict:
    """Return customer count and repeat purchase rate with citations."""
    customers = supabase.table("customers").select("id, source, source_id").execute().data
    orders = supabase.table("orders").select("customer_id").execute().data

    from collections import Counter
    order_counts = Counter(o["customer_id"] for o in orders if o["customer_id"])
    repeat = sum(1 for c in order_counts.values() if c > 1)
    repeat_rate = round(repeat / len(order_counts) * 100, 1) if order_counts else 0

    return {
        "customer_count": len(customers),
        "repeat_rate_pct": repeat_rate,
        "citations": [
            {"table": "customers", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
            for r in customers
        ],
    }


# ── Write tools ───────────────────────────────────────────────────────────────

def flag_order(order_id: int, reason: str) -> dict:
    """Flag an order for review by updating its fulfillment_status."""
    supabase.table("orders").update({"fulfillment_status": f"flagged: {reason}"}).eq("id", order_id).execute()
    return {"flagged": True, "order_id": order_id}


def update_inventory(product_id: int, new_quantity: int) -> dict:
    """Update a product's inventory quantity after a manual stock count."""
    supabase.table("products").update({"inventory_quantity": new_quantity}).eq("id", product_id).execute()
    return {"updated": True, "product_id": product_id, "new_quantity": new_quantity}


def add_note(table: str, row_id: int, note: str) -> dict:
    """Attach a freeform note to any row via the agent_runs log."""
    supabase.table("agent_runs").insert({
        "check_name": "manual_note",
        "status": "note",
        "reasoning": note,
        "proposed_action": "",
        "citations": [{"table": table, "id": row_id}],
    }).execute()
    return {"noted": True}


# ── Agent log ─────────────────────────────────────────────────────────────────

def log_agent_run(check_name: str, status: str, reasoning: str, proposed_action: str, citations: list) -> dict:
    """Write an autonomous agent run with reasoning and proposed action to the database."""
    supabase.table("agent_runs").insert({
        "check_name": check_name,
        "status": status,
        "reasoning": reasoning,
        "proposed_action": proposed_action,
        "citations": citations,
    }).execute()
    return {"logged": True}
