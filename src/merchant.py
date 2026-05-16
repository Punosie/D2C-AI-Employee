"""
Merchant configuration — runtime settings the AI agent can read and update.

Stored in Supabase `merchant_config(merchant_id, key, value JSONB)`.
Falls back to DEFAULTS if the table is empty or Supabase is unreachable.

SQL:
    CREATE TABLE IF NOT EXISTS merchant_config (
        merchant_id TEXT    NOT NULL DEFAULT 'default',
        key         TEXT    NOT NULL,
        value       JSONB   NOT NULL,
        updated_at  TIMESTAMPTZ DEFAULT now(),
        PRIMARY KEY (merchant_id, key)
    );
"""
from src.config import supabase

DEFAULT_MERCHANT = "default"

DEFAULTS: dict = {
    "currency_symbol": "₹",
    "currency_code":   "INR",
    "timezone":        "Asia/Kolkata",
    "sheet_tab_names": {
        "inventory":     "Inventory",
        "raw_materials": "Raw Material Cost",
        "vendors":       "Vendors",
        "budget":        "Monthly Budget",
    },
    "column_aliases":  {},
    "shopify_last_sync": None,
}


def get_all_config(merchant_id: str = DEFAULT_MERCHANT) -> dict:
    try:
        rows = (
            supabase.table("merchant_config")
            .select("key, value")
            .eq("merchant_id", merchant_id)
            .execute()
            .data
        )
        config = dict(DEFAULTS)
        for row in rows:
            config[row["key"]] = row["value"]
        return config
    except Exception:
        return dict(DEFAULTS)


def get_merchant_config(key: str, merchant_id: str = DEFAULT_MERCHANT) -> dict:
    """Read a merchant config value. Agent tool."""
    try:
        rows = (
            supabase.table("merchant_config")
            .select("value")
            .eq("merchant_id", merchant_id)
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


def update_merchant_config(key: str, value: str, merchant_id: str = DEFAULT_MERCHANT) -> dict:
    """Update a merchant config setting. Agent tool."""
    supabase.table("merchant_config").upsert(
        {"merchant_id": merchant_id, "key": key, "value": value},
        on_conflict="merchant_id,key",
    ).execute()
    return {"updated": True, "key": key, "value": value}


def resolve_columns(sheet_tab: str, rows: list[dict], merchant_id: str = DEFAULT_MERCHANT) -> list[dict]:
    """Rename row keys using stored column aliases for the given sheet tab."""
    aliases: dict = get_all_config(merchant_id).get("column_aliases", {}).get(sheet_tab, {})
    if not aliases:
        return rows
    return [{aliases.get(k, k): v for k, v in row.items()} for row in rows]
