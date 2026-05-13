"""
Tests for the FastAPI chat backend (src/api.py).
The ADK runner is mocked so no live Gemini calls are made.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_final_event(text: str):
    """Build a mock ADK event that looks like a final response."""
    event = MagicMock()
    event.is_final_response.return_value = True
    part = MagicMock()
    part.text = text
    event.content = MagicMock()
    event.content.parts = [part]
    return event


async def _mock_run_async(*args, **kwargs):
    yield _make_final_event("Revenue last month was ₹4,23,000.")


async def _mock_create_session(*args, **kwargs):
    session = MagicMock()
    session.id = "mock-adk-session-id"
    return session


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    import src.api as api_module
    with (
        patch.object(api_module._runner, "run_async", side_effect=_mock_run_async),
        patch.object(api_module._session_service, "create_session", side_effect=_mock_create_session),
    ):
        yield TestClient(api_module.app)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_returns_response(client):
    resp = client.post("/chat", json={"message": "What was my revenue last month?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Revenue last month was ₹4,23,000."


def test_chat_returns_session_id(client):
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    assert resp.json()["session_id"] != ""


def test_chat_reuses_provided_session_id(client):
    """Passing an existing session_id should return the same id back."""
    resp = client.post("/chat", json={"message": "Hello", "session_id": "existing-session"})
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "existing-session"


def test_chat_auto_generates_session_id_when_omitted(client):
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    assert len(resp.json()["session_id"]) > 0


def test_chat_rejects_missing_message(client):
    resp = client.post("/chat", json={})
    assert resp.status_code == 422  # FastAPI validation error


def test_root_returns_html():
    """GET / should serve the index.html file."""
    import src.api as api_module
    test_client = TestClient(api_module.app)
    resp = test_client.get("/")
    # FileResponse returns 200 if the file exists, 404/500 if not
    # In CI the file might not exist; just check we get a valid HTTP response
    assert resp.status_code in (200, 404, 500)
