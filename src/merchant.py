"""
Merchant configuration — runtime settings the AI agent can read and update.

Stored in Supabase `merchant_config` table (key TEXT PK, value JSONB).
Falls back to DEFAULTS if the table doesn't exist or a key is unset.

SQL to create the table:
    CREATE TABLE merchant_config (
        key        TEXT PRIMARY KEY,
        value      JSONB NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now()
    );
"""
from src.config import supabase

DEFAULTS: dict = {
    "currency_symbol": "₹",
    "currency_code":   "INR",
    "timezone":        "Asia/Kolkata",
    # Maps canonical sheet role → actual tab name in the spreadsheet
    "sheet_tab_names": {
        "inventory":     "Inventory",
        "raw_materials": "Raw Material Cost",
        "vendors":       "Vendors",
        "budget":        "Monthly Budget",
    },
    # Maps actual header names → canonical names, per tab
    # e.g. {"Inventory": {"SKU Code": "sku", "Stock": "current_stock"}}
    "column_aliases": {},
    # ISO timestamp of last Shopify incremental sync (set automatically)
    "shopify_last_sync": None,
}


def get_all_config() -> dict:
    """Return full config: Supabase values merged over defaults."""
    try:
        rows = supabase.table("merchant_config").select("key, value").execute().data
        config = dict(DEFAULTS)
        for row in rows:
            config[row["key"]] = row["value"]
        return config
    except Exception:
        return dict(DEFAULTS)


def get_merchant_config(key: str) -> dict:
    """Read a merchant config value. Agent tool — use to check currency, sheet names, etc."""
    try:
        rows = (
            supabase.table("merchant_config")
            .select("value")
            .eq("key", key)
            .limit(1)
            .execute()
            .data
        )
        if rows:
            return {"key": key, "value": rows[0]["value"]}
    except Exception:
        pass
    return {"key": key, "value": DEFAULTS.get(key), "source": "default"}


def update_merchant_config(key: str, value: str) -> dict:
    """
    Update a merchant config setting. Agent tool — call this when the user says
    their currency is different, a column was renamed, or a sheet tab was moved.

    Common keys:
      currency_symbol      — e.g. "$", "€", "₹"
      currency_code        — e.g. "USD", "EUR", "INR"
      sheet_tab_names      — JSON object mapping role → actual tab name
      column_aliases       — JSON object mapping tab → {header: canonical}
    """
    supabase.table("merchant_config").upsert(
        {"key": key, "value": value}, on_conflict="key"
    ).execute()
    return {"updated": True, "key": key, "value": value}


def resolve_columns(sheet_tab: str, rows: list[dict]) -> list[dict]:
    """Rename row keys using stored column aliases for the given sheet tab."""
    aliases: dict = get_all_config().get("column_aliases", {}).get(sheet_tab, {})
    if not aliases:
        return rows
    return [{aliases.get(k, k): v for k, v in row.items()} for row in rows]
