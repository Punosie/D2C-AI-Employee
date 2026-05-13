from src.connectors.shopify import sync as shopify_sync
from src.connectors.meta_ads import sync as meta_sync
from src.connectors.google_sheets import sync as sheets_sync

# To add a connector: import its sync() and add a tuple here.
# To disable one: comment out its line.
CONNECTORS: list[tuple[str, callable]] = [
    ("shopify",       shopify_sync),
    ("meta_ads",      meta_sync),
    ("google_sheets", sheets_sync),
]
