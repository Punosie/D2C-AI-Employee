"""
Merchant credentials — stored in Supabase `merchant_credentials` table.

Each merchant has one row per connector. Credentials are read fresh on every
call so no server restart is ever needed after saving from the UI.

Falls back to credentials.json then environment variables for local dev.
"""
import json
import os
from pathlib import Path

_CLIENT = None
CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"
DEFAULT_MERCHANT = "default"


def _supabase():
    """Lazy Supabase client — created on first use so .env is already loaded."""
    global _CLIENT
    if _CLIENT is None:
        from supabase import create_client
        _CLIENT = create_client(
            os.environ.get("SUPABASE_URL", ""),
            os.environ.get("SUPABASE_KEY", ""),
        )
    return _CLIENT


def get_credentials(merchant_id: str = DEFAULT_MERCHANT) -> dict:
    """
    Return all connector credentials for a merchant.
    Priority: Supabase table → credentials.json → (empty dict).
    """
    try:
        rows = (
            _supabase()
            .table("merchant_credentials")
            .select("connector, creds")
            .eq("merchant_id", merchant_id)
            .execute()
            .data
        )
        if rows:
            return {r["connector"]: r["creds"] for r in rows}
    except Exception:
        pass

    # Dev fallback — credentials.json at project root
    if CREDENTIALS_FILE.exists():
        try:
            return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_credentials(merchant_id: str, connector: str, creds: dict) -> None:
    """Upsert connector credentials for a merchant."""
    _supabase().table("merchant_credentials").upsert(
        {"merchant_id": merchant_id, "connector": connector, "creds": creds},
        on_conflict="merchant_id,connector",
    ).execute()


def credentials_status(merchant_id: str = DEFAULT_MERCHANT) -> dict:
    """Return masked status for each connector — never returns raw secrets."""
    creds   = get_credentials(merchant_id)
    shopify = creds.get("shopify", {})
    meta    = creds.get("meta_ads", {})
    sheets  = creds.get("google_sheets", {})
    return {
        "shopify": {
            "configured": bool(shopify.get("store_url") and shopify.get("api_key")),
            "store_url":  shopify.get("store_url") or "",
        },
        "meta_ads": {
            "configured": bool(meta.get("access_token") and meta.get("account_id")),
            "account_id": meta.get("account_id") or "",
        },
        "google_sheets": {
            # service_account_json is global infra (in .env) — merchant only needs sheet_ids
            "configured": bool(sheets.get("sheet_ids") or os.environ.get("GOOGLE_SHEET_IDS")),
            "sheet_ids":  sheets.get("sheet_ids") or os.environ.get("GOOGLE_SHEET_IDS") or "",
        },
    }
