import json
import gspread
from src.config import settings
from .base import NormalizedRecord


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
                "month":    row["month"],
                "category": row["category"],
                "budgeted": float(row["budgeted"]),
                "actual":   float(row["actual"]),
                "variance": float(row["variance"]),
                "notes":    row.get("notes", ""),
                "source":   "google_sheets",
                "source_id": source_id,
            },
            source="google_sheets",
            source_id=source_id,
        ))
    return records


# ── Sheet config: name → normalizer ──────────────────────────────────────────

SHEET_CONFIG = {
    "Inventory":         _normalize_inventory,
    "Raw Material Cost": _normalize_raw_materials,
    "Vendors":           _normalize_vendors,
    "Monthly Budget":    _normalize_budget,
}


# ── Public interface (matches fetch/normalize pattern in sync.py) ─────────────

def fetch_sheets() -> dict[str, list[dict]]:
    """Read all configured sheet tabs across all sheet IDs. Returns {sheet_name: rows}."""
    val = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if val.strip().startswith("{"):
        gc = gspread.service_account_from_dict(json.loads(val))
    else:
        gc = gspread.service_account(filename=val)

    sheet_ids = [s.strip() for s in settings.GOOGLE_SHEET_IDS.split(",") if s.strip()]

    result = {}
    for sheet_id in sheet_ids:
        spreadsheet = gc.open_by_key(sheet_id)
        for name in SHEET_CONFIG:
            try:
                result[name] = spreadsheet.worksheet(name).get_all_records()
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


def sync() -> list[NormalizedRecord]:
    return normalize_sheets(fetch_sheets())
