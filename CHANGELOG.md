# Changelog

All notable changes are documented here, in reverse chronological order.

---

### Added
- `src/connectors/shopify.py` — full Shopify connector: fetches orders, customers, and products; normalises into `orders`, `order_items`, `customers`, and `products` tables. Pagination via Shopify `Link` header. `customer_id`, `order_id`, and `product_id` foreign-key fields on child records.
- `src/connectors/meta_ads.py` — Meta Ads connector: fetches last-30-day campaign insights, normalises into `ad_spend`.
- `CHANGELOG.md` — this file.

### Changed
- `src/jobs/sync.py` — expanded from Google Sheets only to all three connectors (Shopify, Meta Ads, Google Sheets).
- `src/config.py` — added optional `SHOPIFY_STORE_URL`, `SHOPIFY_API_KEY`, `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` fields.

---

## 21a1c14 — 2026-05-13 · feat: add AI agent core with query tools and runner

### Added
- `src/agent/agent.py` — ADK `LlmAgent` wired to all query and write tools; citation-enforcement (`[source:table#id]`) in system prompt.
- `src/agent/runner.py` — autonomous check loop: ROAS drop >20% WoW, low inventory (<10 units), repeat customer rate <20%.
- `src/agent/__init__.py`
- `src/tools/query_tools.py` — `query_sales`, `query_ad_spend`, `query_products`, `query_customers`, `log_agent_run`, `flag_order`, `update_inventory`, `add_note`. Every read tool returns a `citations` list.
- `src/tools/__init__.py`

### Changed
- `src/config.py` — minor update.
- `docs/Plan_V1.jpeg` — moved to `docs/Plans/`.

---

## 02d894e — 2026-05-13 · feat: add Google Sheets connector, ingestion pipeline, and sync job

### Added
- `src/connectors/base.py` — shared `NormalizedRecord` NamedTuple and `make_session()` with 3-retry backoff.
- `src/connectors/google_sheets.py` — reads ad spend sheet via service account; normalises into `ad_spend` table.
- `src/connectors/__init__.py`
- `src/ingestion/upsert.py` — `upsert_all()` batches records by table, upserts with per-table conflict keys.
- `src/ingestion/__init__.py`
- `src/jobs/sync.py` — scheduled ingestion entry point (Google Sheets only at this point).
- `src/jobs/__init__.py`

### Changed
- `.gitignore` — updated.
- `docs/Plans/Plan_V1.jpeg` — renamed from `project_plan_v1.jpeg`.

---

## 46f3377 — 2026-05-12 · feat: create sample google sheet, test connection

### Added
- `data/create_sample_sheets.py` — script to seed a sample Google Sheet with ad spend data.
- `data/sample_data.xlsx` — sample data file.
- `requirements.txt` — full dependency list.
- `src/config.py` — extended with Google Sheets config fields.
- `tests/test_google_spreadsheet_connection.py` — connection smoke test.

---

## 243d52c — 2026-05-12 · feat: update schema, create supabase tables, plan for Day 01

### Added
- `docs/schema.sql` — full Supabase schema: `customers`, `products`, `orders`, `order_items`, `ad_spend`, `inventory`, `agent_runs` tables with provenance columns (`source`, `source_id`, `synced_at`).
- `docs/schama_v2.png`, `docs/schema_v1.png` — schema diagrams.
- `docs/Plans/plan_day_1.jpeg`, `docs/Plans/project_plan_v1.jpeg` — day-1 plan images.

---

## c5d1261 — 2026-05-12 · feat: test supabase connection and initial setup

### Added
- `src/config.py` — Pydantic settings with validation for `SUPABASE_URL`, `SUPABASE_KEY`, and Google credentials; exits with a clear error if any required var is missing.
- `src/__init__.py`
- `tests/test_supabase_connection.py` — Supabase connection smoke test.
- `tests/__init__.py`
- `.gitignore` — initial ignore rules.

---

## 4d0657e — 2026-05-12 · first commit

### Added
- `README.md`
