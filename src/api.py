"""
Minimal FastAPI chat server for the D2C AI Employee.

Run:
    uvicorn src.api:app --reload

Then open http://localhost:8000 in your browser.
"""
import uuid
import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from src.agent.agent import root_agent

app = FastAPI(title="D2C AI Employee")

_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="d2c_agent",
    session_service=_session_service,
)

# In-memory map: client session_id → ADK session_id
_sessions: dict[str, str] = {}

_TEMPLATE = Path(__file__).parent.parent / "templates" / "index.html"


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.get("/")
async def root():
    return FileResponse(_TEMPLATE)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    if session_id not in _sessions:
        session = await _session_service.create_session(
            app_name="d2c_agent", user_id=session_id
        )
        _sessions[session_id] = session.id

    adk_session_id = _sessions[session_id]
    message = Content(role="user", parts=[Part(text=req.message)])
    response_text = ""

    async for event in _runner.run_async(
        user_id=session_id,
        session_id=adk_session_id,
        new_message=message,
    ):
        if event.is_final_response():
            parts = event.content.parts if event.content else []
            response_text = parts[0].text if parts else "(no response)"

    return ChatResponse(response=response_text, session_id=session_id)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
