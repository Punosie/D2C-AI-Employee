from src.config import supabase
from src.connectors.base import NormalizedRecord

# The column(s) used to detect duplicates on upsert for each table
UPSERT_KEYS = {
    "customers":          "source,external_id",
    "products":           "source,external_id",
    "orders":             "source,external_id",
    "order_items":        "source_id",
    "ad_spend":           "source,date,platform,campaign_name",
    "inventory":          "source,sku",
    "raw_material_costs": "material,vendor_name",
    "vendors":            "source,vendor_name",
    "monthly_budget":     "month,category",
}


def upsert_all(records: list[NormalizedRecord]) -> None:
    """Group records by table and upsert each batch into Supabase."""
    by_table: dict[str, list[dict]] = {}
    for r in records:
        by_table.setdefault(r.table, []).append(r.data)

    for table, rows in by_table.items():
        (
            supabase.table(table)
            .upsert(rows, on_conflict=UPSERT_KEYS[table])
            .execute()
        )
