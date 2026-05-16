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
                    "limit": {"type": "integer", "description": "Max products to return (default 10)"},
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
    try:
        return fn(**args)
    except Exception as e:
        return {"error": str(e)}

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = """You are an AI employee for a D2C brand. Answer business questions accurately using your tools.

Citation rules:
- Every number must be cited in the format [source:table#id]. Example: revenue was ₹4,23,000 [source:orders#12].
- Never state an uncited number. If you cannot cite it, say so explicitly.

Currency: always call get_merchant_config("currency_symbol") before displaying monetary values.

Trend context: use query_roas_trend and query_sales_trend to give context beyond point-in-time values."""

# ── Main entry point ──────────────────────────────────────────────────────────

async def run_with_fallback(message: str) -> str:
    if not settings.GROQ_API_KEY:
        return (
            "The AI service is temporarily unavailable and no fallback is configured.\n\n"
            "Add `GROQ_API_KEY` to Railway service variables to enable fallback. "
            "Get a free key at https://console.groq.com"
        )

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
            model="llama-3.3-70b-versatile",
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
