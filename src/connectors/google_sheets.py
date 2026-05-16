import json
import gspread
from src.config import settings
from .base import NormalizedRecord


# ── Required columns per canonical sheet name ────────────────────────────────
# Validation runs after alias resolution, so these are canonical names.
# If a founder renames a column, they update column_aliases — not this list.

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "Inventory": {
        "sku", "product_name", "current_stock", "reorder_level",
        "reorder_qty", "unit_cost", "location", "last_updated",
    },
    "Raw Material Cost": {
        "material", "vendor_name", "unit", "cost_per_unit",
        "monthly_usage", "monthly_cost", "last_purchase_date",
    },
    "Vendors": {
        "vendor_name", "category", "contact_person", "phone",
        "email", "payment_terms", "lead_time_days", "rating",
    },
    "Monthly Budget": {"month", "category", "budgeted", "actual", "variance"},
}


# ── Normalizers ───────────────────────────────────────────────────────────────

def _normalize_inventory(rows: list[dict]) -> list[NormalizedRecord]:
    records = []
    for row in rows:
        records.append(NormalizedRecord(
            table="inventory",
            data={
                "sku":           row["sku"],
                "product_name":  row["product_name"],
                "current_stock": int(row["current_stock"]),
                "reorder_level": int(row["reorder_level"]),
                "reorder_qty":   int(row["reorder_qty"]),
                "unit_cost":     float(row["unit_cost"]),
                "location":      row["location"],
                "last_updated":  row["last_updated"],
                "source":        "google_sheets",
                "source_id":     f"inventory_{row['sku']}",
            },
            source="google_sheets",
            source_id=f"inventory_{row['sku']}",
        ))
    return records


def _normalize_raw_materials(rows: list[dict]) -> list[NormalizedRecord]:
    records = []
    for row in rows:
        source_id = f"raw_material_{row['material']}_{row['vendor_name']}".replace(" ", "_").lower()
        records.append(NormalizedRecord(
            table="raw_material_costs",
            data={
                "material":           row["material"],
                "vendor_name":        row["vendor_name"],
                "unit":               row["unit"],
                "cost_per_unit":      float(row["cost_per_unit"]),
                "monthly_usage":      float(row["monthly_usage"]),
                "monthly_cost":       float(row["monthly_cost"]),
                "last_purchase_date": row["last_purchase_date"],
                "notes":              row.get("notes", ""),
                "source":             "google_sheets",
                "source_id":          source_id,
            },
            source="google_sheets",
            source_id=source_id,
        ))
    return records


def _normalize_vendors(rows: list[dict]) -> list[NormalizedRecord]:
    records = []
    for row in rows:
        source_id = f"vendor_{row['vendor_name']}".replace(" ", "_").lower()
        records.append(NormalizedRecord(
            table="vendors",
            data={
                "vendor_name":    row["vendor_name"],
                "category":       row["category"],
                "contact_person": row["contact_person"],
                "phone":          str(row["phone"]),
                "email":          row["email"],
                "payment_terms":  row["payment_terms"],
                "lead_time_days": int(row["lead_time_days"]),
                "rating":         int(row["rating"]),
                "notes":          row.get("notes", ""),
                "source":         "google_sheets",
                "source_id":      source_id,
            },
            source="google_sheets",
            source_id=source_id,
        ))
    return records


def _normalize_budget(rows: list[dict]) -> list[NormalizedRecord]:
    records = []
    for row in rows:
        source_id = f"budget_{row['month']}_{row['category']}".replace(" ", "_").lower()
        records.append(NormalizedRecord(
            table="monthly_budget",
            data={
                "month":     row["month"],
                "category":  row["category"],
                "budgeted":  float(row["budgeted"]),
                "actual":    float(row["actual"]),
                "variance":  float(row["variance"]),
                "notes":     row.get("notes", ""),
                "source":    "google_sheets",
                "source_id": source_id,
            },
            source="google_sheets",
            source_id=source_id,
        ))
    return records


# ── Sheet config: canonical name → normalizer ─────────────────────────────────

SHEET_CONFIG: dict[str, callable] = {
    "Inventory":         _normalize_inventory,
    "Raw Material Cost": _normalize_raw_materials,
    "Vendors":           _normalize_vendors,
    "Monthly Budget":    _normalize_budget,
}


# ── Public interface ──────────────────────────────────────────────────────────

def fetch_sheets(sheet_ids: str | None = None, tab_names: dict | None = None) -> dict[str, list[dict]]:
    """
    Read all configured sheet tabs across all sheet IDs.

    sheet_ids — comma-separated spreadsheet IDs (overrides settings).
    tab_names — optional override from merchant config.
    """
    from src.merchant import resolve_columns

    val = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if not val:
        raise ValueError(
            "Google service account is not configured. "
            "Add GOOGLE_SERVICE_ACCOUNT_JSON to your .env file."
        )
    gc = (
        gspread.service_account_from_dict(json.loads(val))
        if val.strip().startswith("{")
        else gspread.service_account(filename=val)
    )

    # Build canonical_name → actual tab name mapping
    tab_map = {
        "Inventory":         (tab_names or {}).get("inventory",     "Inventory"),
        "Raw Material Cost": (tab_names or {}).get("raw_materials", "Raw Material Cost"),
        "Vendors":           (tab_names or {}).get("vendors",       "Vendors"),
        "Monthly Budget":    (tab_names or {}).get("budget",        "Monthly Budget"),
    }

    _ids      = sheet_ids or settings.GOOGLE_SHEET_IDS or ""
    sheet_id_list = [s.strip() for s in _ids.split(",") if s.strip()]
    result: dict[str, list[dict]] = {}

    for sheet_id in sheet_id_list:
        spreadsheet = gc.open_by_key(sheet_id)
        for canonical_name, actual_tab_name in tab_map.items():
            try:
                rows = spreadsheet.worksheet(actual_tab_name).get_all_records()
                rows = resolve_columns(actual_tab_name, rows)
                _validate_columns(canonical_name, rows)
                result[canonical_name] = rows
            except gspread.exceptions.WorksheetNotFound:
                pass

    return result


def normalize_sheets(raw: dict[str, list[dict]]) -> list[NormalizedRecord]:
    """Dispatch each sheet's rows to the right normalizer."""
    records = []
    for sheet_name, rows in raw.items():
        normalizer = SHEET_CONFIG.get(sheet_name)
        if normalizer:
            records.extend(normalizer(rows))
    return records


def sync(merchant_id: str = "default") -> list[NormalizedRecord]:
    """Reads sheet IDs fresh from DB — no restart needed."""
    from src.credentials import get_credentials
    from src.merchant import get_all_config

    sheet_creds = get_credentials(merchant_id).get("google_sheets", {})
    sheet_ids   = sheet_creds.get("sheet_ids") or settings.GOOGLE_SHEET_IDS

    if not sheet_ids:
        raise ValueError(
            "Google Sheets not connected. Go to Settings and share your spreadsheet."
        )

    config = get_all_config()
    raw    = fetch_sheets(sheet_ids=sheet_ids, tab_names=config.get("sheet_tab_names"))
    return normalize_sheets(raw)


# ── Column validation ─────────────────────────────────────────────────────────

def _validate_columns(canonical_name: str, rows: list[dict]) -> None:
    """Raise loudly if required columns are missing after alias resolution."""
    if not rows:
        return
    required = REQUIRED_COLUMNS.get(canonical_name, set())
    if not required:
        return
    actual = set(rows[0].keys())
    missing = required - actual
    if missing:
        raise ValueError(
            f"Sheet '{canonical_name}': missing required columns {sorted(missing)}. "
            f"Found: {sorted(actual)}. "
            f"If the header was renamed, call update_merchant_config('column_aliases', ...) "
            f"to map it to the canonical name."
        )
