"""
Delete all rows from data tables (keeps merchant_credentials and merchant_config).
Usage: python -m scripts.clear_data
"""
from src.config import supabase

# Data tables only — credentials and config are preserved
DATA_TABLES = [
    "order_items",
    "orders",
    "customers",
    "products",
    "ad_spend",
    "inventory",
    "raw_material_costs",
    "vendors",
    "monthly_budget",
    "agent_runs",
]

print("Clearing data tables...")
for table in DATA_TABLES:
    try:
        supabase.table(table).delete().neq("source", "__none__").execute()
        print(f"  cleared {table}")
    except Exception as e:
        print(f"  skipped {table}: {e}")

print("\nDone. merchant_credentials and merchant_config are untouched.")
print("Run 'python -m scripts.run_sync' to repopulate after connecting connectors.")
