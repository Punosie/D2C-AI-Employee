import logging
from openai import AsyncOpenAI
from src.config import settings

logger = logging.getLogger(__name__)

_SYSTEM = """You are a D2C AI Employee helping e-commerce merchants understand their business.
IMPORTANT: You are running in fallback mode — the primary Gemini AI service is temporarily unavailable.
You do NOT have access to the merchant's live Shopify, Meta Ads, or Google Sheets data right now.
Be helpful but clearly state this limitation. Advise the merchant to check their GOOGLE_GENAI_API_KEY on Railway."""


async def _complete(base_url: str, api_key: str, model: str, message: str) -> str:
    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": message},
        ],
        max_tokens=1024,
    )
    return resp.choices[0].message.content or ""


async def run_with_fallback(message: str) -> str:
    """Try Groq when Gemini is unavailable. Returns a formatted response."""
    if settings.GROQ_API_KEY:
        try:
            text = await _complete(
                "https://api.groq.com/openai/v1",
                settings.GROQ_API_KEY,
                "llama-3.3-70b-versatile",
                message,
            )
            logger.info("Fallback succeeded via Groq")
            return (
                "> **Fallback mode** — responding via Groq · Llama-3.3-70b. "
                "Live data tools are offline (Gemini API unavailable).\n\n"
                + text
            )
        except Exception as e:
            logger.warning("Groq fallback failed: %s", e)

    return (
        "All AI models are currently unavailable. Please check:\n\n"
        "1. **`GOOGLE_GENAI_API_KEY`** on Railway — may be expired or over quota\n"
        "2. **`GROQ_API_KEY`** — get a free key at [console.groq.com](https://console.groq.com)\n\n"
        "Add both keys to the Railway service variables and redeploy."
    )
