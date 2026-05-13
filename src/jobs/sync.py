from src.connectors.registry import CONNECTORS
from src.ingestion.upsert import upsert_all


def run_sync():
    for name, sync_fn in CONNECTORS:
        try:
            records = sync_fn()
            upsert_all(records)
            print(f"{name}: synced {len(records)} records")
        except Exception as e:
            print(f"{name}: ERROR — {e}")


if __name__ == "__main__":
    run_sync()
