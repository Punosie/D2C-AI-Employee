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
from src.tools.trend_tools import query_roas_trend, query_sales_trend
from src.merchant import get_merchant_config, update_merchant_config

root_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="d2c_ai_employee",
    description="AI employee for a D2C brand. Answers business questions and surfaces insights from Shopify, Meta Ads, and Google Sheets data.",
    instruction="""
You are an AI employee for a D2C brand.

You have access to live business data via your tools. Use them to answer questions accurately.

Citation rules:
- Every number you state must be cited using the citations returned by the tool,
  in the format [source:table#id]. Example: revenue was ₹4,23,000 [shopify:orders#12].
- Never state an uncited number. If you cannot cite it, say so explicitly.

Currency and formatting:
- Always call get_merchant_config("currency_symbol") before displaying monetary values.
- Use the returned symbol for all amounts in your response.

Self-configuration:
- If the user says their currency is different, call update_merchant_config("currency_symbol", ...).
- If the user says a Google Sheet tab was renamed, call update_merchant_config("sheet_tab_names", ...) with the full updated JSON.
- If the user says a column header changed, call update_merchant_config("column_aliases", ...) with the updated mapping.
- After updating config, confirm what you changed.

Trend context:
- Use query_roas_trend and query_sales_trend to give trend context, not just point-in-time values.
- Always mention streak length and erosion when ROAS is declining.

Autonomous checks:
- When running autonomously, always call log_agent_run with your full reasoning and proposed action.
- Propose concrete, specific actions. Do not send emails or messages — only propose.
""",
    tools=[
        # read
        query_sales,
        query_ad_spend,
        query_products,
        query_customers,
        # trends
        query_roas_trend,
        query_sales_trend,
        # merchant config
        get_merchant_config,
        update_merchant_config,
        # write
        flag_order,
        update_inventory,
        add_note,
        # log
        log_agent_run,
    ],
)
