"""
FastAPI backend for the D2C AI Employee.

Run:
    uvicorn src.api:app --reload --port 8000
"""
import json
import logging
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from src.agent.agent import root_agent
from src.config import settings, supabase

logger = logging.getLogger(__name__)

app = FastAPI(title="D2C AI Employee")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://d2c-ai-employee-ui.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = authorization.split(" ", 1)[1]
    try:
        result = supabase.auth.get_user(token)
        return result.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid auth token")

_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name="d2c_agent", session_service=_session_service)
_sessions: dict[str, str] = {}


# ── Request / response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:     str
    session_id:  str = ""
    merchant_id: str = "default"


class ChatResponse(BaseModel):
    response:   str
    session_id: str


class ShopifySettings(BaseModel):
    store_url: Optional[str] = None
    api_key:   Optional[str] = None


class MetaSettings(BaseModel):
    access_token: Optional[str] = None
    account_id:   Optional[str] = None


class GoogleSheetsSettings(BaseModel):
    sheet_ids: Optional[str] = None


class SettingsRequest(BaseModel):
    merchant_id:   str = "default"
    shopify:       Optional[ShopifySettings]      = None
    meta_ads:      Optional[MetaSettings]         = None
    google_sheets: Optional[GoogleSheetsSettings] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "D2C AI Employee API", "frontend": "http://localhost:3001"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user_id: str = Depends(get_current_user)):
    session_id = req.session_id or str(uuid.uuid4())
    try:
        if session_id not in _sessions:
            session = await _session_service.create_session(
                app_name="d2c_agent", user_id=session_id
            )
            _sessions[session_id] = session.id

        adk_session_id = _sessions[session_id]
        message        = Content(role="user", parts=[Part(text=req.message)])
        response_text  = ""

        async for event in _runner.run_async(
            user_id=session_id, session_id=adk_session_id, new_message=message
        ):
            if event.is_final_response():
                parts = event.content.parts if event.content else []
                response_text = parts[0].text if parts else "(no response)"

        return ChatResponse(response=response_text, session_id=session_id)

    except Exception as e:
        logger.error("Chat error: %s", e)
        return ChatResponse(
            response="Something went wrong on my end. Please try again.",
            session_id=session_id,
        )


@app.get("/settings")
async def get_settings(user_id: str = Depends(get_current_user)):
    try:
        from src.credentials import credentials_status
        return credentials_status(user_id)
    except Exception as e:
        logger.error("Settings read error: %s", e)
        return JSONResponse({"error": "Could not load settings."}, status_code=500)


@app.post("/settings")
async def save_settings(req: SettingsRequest, user_id: str = Depends(get_current_user)):
    req.merchant_id = user_id
    try:
        from src.credentials import save_credentials

        if req.shopify:
            creds = {}
            if req.shopify.store_url:
                # Strip protocol prefix so "https://mystore.myshopify.com" → "mystore.myshopify.com"
                url = req.shopify.store_url.strip()
                url = url.replace("https://", "").replace("http://", "").rstrip("/")
                creds["store_url"] = url
            if req.shopify.api_key:
                creds["api_key"] = req.shopify.api_key.strip()
            if creds:
                save_credentials(req.merchant_id, "shopify", creds)

        if req.meta_ads:
            creds = {}
            if req.meta_ads.access_token:
                creds["access_token"] = req.meta_ads.access_token.strip()
            if req.meta_ads.account_id:
                # Strip "act_" prefix if the user included it
                acct = req.meta_ads.account_id.strip().lstrip("act_")
                creds["account_id"] = acct
            if creds:
                save_credentials(req.merchant_id, "meta_ads", creds)

        if req.google_sheets:
            creds = {}
            if req.google_sheets.sheet_ids:
                # Accept full Google Sheet URLs and extract just the ID
                raw = req.google_sheets.sheet_ids.strip()
                ids = [_extract_sheet_id(s.strip()) for s in raw.split(",") if s.strip()]
                creds["sheet_ids"] = ",".join(ids)
            if creds:
                save_credentials(req.merchant_id, "google_sheets", creds)

        return {"saved": True}

    except Exception as e:
        logger.error("Settings save error: %s", e)
        return JSONResponse(
            {"saved": False, "error": "Could not save your settings. Please try again."},
            status_code=500,
        )


@app.get("/settings/google-email")
async def google_service_email():
    """Return the service account email so users know what to share their sheet with."""
    try:
        val = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        if val:
            sa = json.loads(val) if val.strip().startswith("{") else {}
            email = sa.get("client_email", "")
            if email:
                return {"email": email}
    except Exception:
        pass
    return {"email": None}


@app.get("/metrics")
async def get_metrics(merchant_id: str = "default"):
    """Aggregate KPIs for the last 30 days."""
    from src.tools.query_tools import query_sales, query_ad_spend, query_customers
    try:
        today          = str(date.today())
        thirty_ago     = str(date.today() - timedelta(days=30))
        sales          = query_sales(thirty_ago, today)
        ad             = query_ad_spend()
        cust           = query_customers()
        return {
            "revenue_30d":    sales["total_revenue"],
            "orders_30d":     sales["order_count"],
            "aov":            sales["aov"],
            "roas":           ad["roas"],
            "ad_spend_30d":   ad["total_spend"],
            "customer_count": cust["customer_count"],
            "repeat_rate_pct":cust["repeat_rate_pct"],
        }
    except Exception as e:
        logger.error("Metrics error: %s", e)
        return {"error": "No data yet — connect your sources and run a sync first."}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_sheet_id(value: str) -> str:
    """Extract spreadsheet ID from a full Google Sheets URL or return as-is."""
    if "spreadsheets/d/" in value:
        part = value.split("spreadsheets/d/")[1]
        return part.split("/")[0].split("?")[0]
    return value
