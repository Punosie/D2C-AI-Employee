"""
Trigger a manual sync for a specific merchant.
Usage:
  python -m scripts.run_sync                           # syncs shubhankar.kaushik2003@gmail.com
  python -m scripts.run_sync --email other@gmail.com
  python -m scripts.run_sync --merchant-id <uuid>
"""
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from src.config import supabase
from src.jobs.sync import run_sync


def find_merchant_id(email: str) -> str | None:
    resp = supabase.auth.admin.list_users()
    users = resp if isinstance(resp, list) else getattr(resp, "users", [])
    for user in users:
        if getattr(user, "email", None) == email:
            return user.id
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manually trigger a connector sync for a merchant.")
    parser.add_argument("--email", default="shubhankar.kaushik2003@gmail.com", help="Merchant email")
    parser.add_argument("--merchant-id", dest="merchant_id", help="Merchant UUID (skips email lookup)")
    args = parser.parse_args()

    mid = args.merchant_id
    if not mid:
        print(f"Looking up merchant_id for: {args.email}")
        mid = find_merchant_id(args.email)
        if not mid:
            print(f"ERROR: No user found with email {args.email!r}")
            raise SystemExit(1)

    print(f"Running sync for merchant_id: {mid}")
    run_sync(merchant_id=mid)
    print("Sync complete.")
