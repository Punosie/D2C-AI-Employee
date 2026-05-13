from google.adk.agents import LlmAgent
from src.tools.query_tools import (
    query_sales,
    query_ad_spend,
    query_products,
    query_customers,
    flag_order,
    update_inventory,
    add_note,
    log_agent_run,
)

root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="d2c_ai_employee",
    description="AI employee for a D2C candles brand. Answers business questions and surfaces insights from Shopify, Meta Ads, and Google Sheets data.",
    instruction="""
You are an AI employee for a D2C candles brand.

You have access to live business data via your tools. Use them to answer questions accurately.

Rules:
- Every number you state must be cited using the citations returned by the tool,
  in the format [source:table#id]. Example: revenue was ₹4,23,000 [shopify:orders#12].
- Never state an uncited number. If you cannot cite it, say so explicitly.
- When running autonomously, always call log_agent_run with your full reasoning and proposed action.
- Propose concrete, specific actions. Do not send emails or messages — only propose actions.
""",
    tools=[
        # read
        query_sales,
        query_ad_spend,
        query_products,
        query_customers,
        # write
        flag_order,
        update_inventory,
        add_note,
        # log
        log_agent_run,
    ],
)
