import asyncio
import json
import logging
from openai import AsyncOpenAI
from src.config import settings

logger = logging.getLogger(__name__)

# ── Tool schemas (read-only subset of the Gemini agent's tools) ───────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sales",
            "description": "Get total revenue, order count, and AOV for a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "to_date":   {"type": "string", "description": "End date YYYY-MM-DD"},
                },
                "required": ["from_date", "to_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_ad_spend",
            "description": "Get ad spend, ROAS, and campaign breakdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform":  {"type": "string", "description": "Filter by platform e.g. 'meta'"},
                    "from_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_products",
            "description": "Get top products by revenue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"description": "Max products to return as a number, e.g. 10 (default 10)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_customers",
            "description": "Get customer count and repeat purchase rate.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_roas_trend",
            "description": "Get ROAS trend over recent weeks.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_sales_trend",
            "description": "Get weekly sales revenue trend.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant_config",
            "description": "Read a merchant config value such as currency_symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Config key e.g. 'currency_symbol'"},
                },
                "required": ["key"],
            },
        },
    },
]

# ── Tool dispatch ─────────────────────────────────────────────────────────────

def _dispatch(name: str, args: dict):
    from src.tools.query_tools import (
        query_sales, query_ad_spend, query_products, query_customers,
    )
    from src.tools.trend_tools import query_roas_trend, query_sales_trend
    from src.merchant import get_merchant_config

    fns = {
        "query_sales":         query_sales,
        "query_ad_spend":      query_ad_spend,
        "query_products":      query_products,
        "query_customers":     query_customers,
        "query_roas_trend":    query_roas_trend,
        "query_sales_trend":   query_sales_trend,
        "get_merchant_config": get_merchant_config,
    }
    fn = fns.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    # Coerce types that LLMs commonly get wrong
    if name == "query_products" and "limit" in args:
        try:
            args["limit"] = int(args["limit"])
        except (ValueError, TypeError):
            args.pop("limit")
    try:
        return fn(**args)
    except Exception as e:
        return {"error": str(e)}

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = """You are an AI employee for a D2C brand. Answer business questions accurately using your tools.

━━ CITATION FORMAT ━━
Every number you state MUST be cited. Format: [connector:table#id]
  connector = exact source name from the tool's citations array: "shopify", "meta_ads", or "google_sheets"
  table     = exact table name from the citations array: "orders", "ad_spend", "customers", etc.
  id        = exact numeric row ID from the citations array

Example: Revenue was ₹4,23,000 [shopify:orders#12] with 43 orders [shopify:orders#12].

STRICT RULES:
- If the citations array is empty → do NOT state the number. Say "I don't see data for this period."
- NEVER produce [table#] with an empty ID. If you don't have the ID, omit the citation entirely.
- A citation must reference a real row returned by the tool. Never fabricate or guess IDs.
- Every revenue figure, order count, ROAS, spend amount, and product metric requires a citation.
- Use the EXACT connector name from the citations array (e.g. "shopify", not "Shopify" or "source").

━━ ZERO / EMPTY DATA ━━
When a tool returns zero values, empty arrays, or no rows:
- DO NOT say "revenue was ₹0" or "there are 0 orders" — these are misleading.
- INSTEAD say: "I don't see any [data type] for [period]. This may mean the sync hasn't run yet,
  or no transactions occurred in that window. Check Settings to confirm your connector is active."

━━ CURRENCY ━━
Always call get_merchant_config("currency_symbol") before displaying any monetary value.

━━ TREND CONTEXT ━━
Use query_roas_trend and query_sales_trend to provide trend context, not just point-in-time values."""

# ── Main entry point ──────────────────────────────────────────────────────────

async def run_with_fallback(message: str) -> str:
    if not settings.GROQ_API_KEY:
        logger.warning("Groq fallback skipped: GROQ_API_KEY not configured")
        return "I'm having a bit of trouble right now. Please try again in a moment."

    try:
        client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
        )

        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": message},
        ]

        for _ in range(8):  # max tool-call rounds
            resp = await client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=messages,
                tools=_TOOLS,
                tool_choice="auto",
                max_tokens=2048,
            )
            msg = resp.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                logger.info("Groq fallback served response")
                return msg.content or ""

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                result = await asyncio.to_thread(_dispatch, tc.function.name, args)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result),
                })

        logger.warning("Groq fallback hit max tool-call rounds")
        return "I ran into an issue processing your request. Please try again."

    except Exception as e:
        logger.error("Groq fallback error: %s", repr(e))
        return "I'm having a bit of trouble right now. Please try again in a moment."
