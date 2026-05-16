import logging

from src.connectors.registry import CONNECTORS
from src.config import supabase
from src.ingestion.upsert import upsert_all

logger = logging.getLogger(__name__)


def run_sync(merchant_id: str | None = None):
    for name, sync_fn in CONNECTORS:
        try:
            kwargs = {"merchant_id": merchant_id} if merchant_id else {}
            records = sync_fn(**kwargs)
            upsert_all(records)
            print(f"{name}[{merchant_id or 'env'}]: synced {len(records)} records")
        except Exception as e:
            print(f"{name}[{merchant_id or 'env'}]: ERROR — {e}")


def sync_all_merchants():
    """Fetch every merchant that has saved credentials and run their connectors."""
    try:
        rows = supabase.table("merchant_credentials").select("merchant_id").execute()
        merchant_ids = list({r["merchant_id"] for r in (rows.data or [])})
        logger.info("Scheduled sync: %d merchant(s)", len(merchant_ids))
        for mid in merchant_ids:
            run_sync(merchant_id=mid)
    except Exception as e:
        logger.error("sync_all_merchants error: %s", e)


if __name__ == "__main__":
    run_sync()
