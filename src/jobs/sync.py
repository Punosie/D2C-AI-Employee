from src.connectors.shopify import fetch_shopify, normalize_shopify
from src.connectors.meta_ads import fetch_meta, normalize_meta
from src.connectors.google_sheets import fetch_sheets, normalize_sheets
from src.ingestion.upsert import upsert_all

CONNECTORS = [
    ("shopify",       fetch_shopify,  normalize_shopify),
    ("meta_ads",      fetch_meta,     normalize_meta),
    ("google_sheets", fetch_sheets,   normalize_sheets),
]


def run_sync():
    for name, fetch_fn, normalize_fn in CONNECTORS:
        try:
            records = normalize_fn(fetch_fn())
            upsert_all(records)
            print(f"{name}: synced {len(records)} records")
        except Exception as e:
            print(f"{name}: ERROR — {e}")


if __name__ == "__main__":
    run_sync()
