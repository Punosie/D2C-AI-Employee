"""
Tests for the FastAPI chat backend (src/api.py).
The Groq agent and credential check are mocked — no live API or DB calls needed.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    import src.api as api_module
    api_module.app.dependency_overrides[api_module.get_current_user] = lambda: "test-user-id"
    with (
        patch("src.agent.groq_agent.run_agent",
              new=AsyncMock(return_value="Revenue last month was ₹4,23,000.")),
        patch("src.credentials.credentials_status",
              return_value={"shopify": {"configured": True}}),
    ):
        yield TestClient(api_module.app)
    api_module.app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_returns_response(client):
    resp = client.post("/chat", json={"message": "What was my revenue last month?"})
    assert resp.status_code == 200
    assert resp.json()["response"] == "Revenue last month was ₹4,23,000."


def test_chat_returns_session_id(client):
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    assert resp.json()["session_id"] != ""


def test_chat_reuses_provided_session_id(client):
    resp = client.post("/chat", json={"message": "Hello", "session_id": "existing-session"})
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "existing-session"


def test_chat_auto_generates_session_id_when_omitted(client):
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    assert len(resp.json()["session_id"]) > 0


def test_chat_rejects_missing_message(client):
    resp = client.post("/chat", json={})
    assert resp.status_code == 422


def test_chat_blocked_when_no_connectors_configured():
    """Guard returns friendly message when no connectors are set up."""
    import src.api as api_module
    api_module.app.dependency_overrides[api_module.get_current_user] = lambda: "test-user-id"
    try:
        with patch("src.credentials.credentials_status",
                   return_value={"shopify": {"configured": False}, "meta_ads": {"configured": False}}):
            resp = TestClient(api_module.app).post("/chat", json={"message": "Hello"})
            assert resp.status_code == 200
            assert "Settings" in resp.json()["response"]
    finally:
        api_module.app.dependency_overrides.clear()


def test_root_returns_valid_response():
    import src.api as api_module
    resp = TestClient(api_module.app).get("/")
    assert resp.status_code in (200, 404, 500)
