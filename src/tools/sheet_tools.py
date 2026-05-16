"""Query tools for Google Sheets-sourced tables: inventory, raw materials, vendors, budget."""
from src.config import supabase


def query_inventory() -> dict:
    """Return all inventory rows with stock levels and reorder flags."""
    rows = (
        supabase.table("inventory")
        .select("id, sku, product_name, current_stock, reorder_level, reorder_qty, unit_cost, location, source, source_id")
        .execute()
        .data
    )
    low_stock = [r for r in rows if r["current_stock"] is not None and r["reorder_level"] is not None
                 and r["current_stock"] <= r["reorder_level"]]
    return {
        "inventory": rows,
        "low_stock_items": low_stock,
        "total_skus": len(rows),
        "citations": [
            {"table": "inventory", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
            for r in rows
        ],
    }


def query_raw_materials() -> dict:
    """Return raw material costs, monthly spend, and vendor details."""
    rows = (
        supabase.table("raw_material_costs")
        .select("id, material, vendor_name, unit, cost_per_unit, monthly_usage, monthly_cost, last_purchase_date, notes, source, source_id")
        .execute()
        .data
    )
    total_monthly = sum(r["monthly_cost"] or 0 for r in rows)
    sorted_rows = sorted(rows, key=lambda r: r["monthly_cost"] or 0, reverse=True)
    return {
        "materials": sorted_rows,
        "total_monthly_cost": round(total_monthly, 2),
        "citations": [
            {"table": "raw_material_costs", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
            for r in rows
        ],
    }


def query_vendors() -> dict:
    """Return vendor list with ratings, lead times, and payment terms."""
    rows = (
        supabase.table("vendors")
        .select("id, vendor_name, category, contact_person, phone, email, payment_terms, lead_time_days, rating, notes, source, source_id")
        .execute()
        .data
    )
    sorted_rows = sorted(rows, key=lambda r: r["rating"] or 0, reverse=True)
    return {
        "vendors": sorted_rows,
        "citations": [
            {"table": "vendors", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
            for r in rows
        ],
    }


def query_budget(month: str | None = None) -> dict:
    """Return budget vs actual spend with variance by category."""
    q = supabase.table("monthly_budget").select(
        "id, month, category, budgeted, actual, variance, notes, source, source_id"
    )
    if month:
        q = q.eq("month", month)
    rows = q.order("month").execute().data

    over_budget = [r for r in rows if (r["variance"] or 0) < 0]
    total_budgeted = sum(r["budgeted"] or 0 for r in rows)
    total_actual = sum(r["actual"] or 0 for r in rows)

    return {
        "budget_rows": rows,
        "over_budget_categories": over_budget,
        "total_budgeted": round(total_budgeted, 2),
        "total_actual": round(total_actual, 2),
        "net_variance": round(total_budgeted - total_actual, 2),
        "citations": [
            {"table": "monthly_budget", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
            for r in rows
        ],
    }
