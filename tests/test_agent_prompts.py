"""
Unit tests for the Groq fallback agent (src/agent/fallback.py).
All Groq API calls and tool dispatches are mocked — no live network or DB access.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_completion(content: str = "Here is the answer.", tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    msg.model_dump.return_value = {"role": "assistant", "content": content}
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _patched_client(response=None, error=None):
    """Return a context manager that patches AsyncOpenAI with a mock client."""
    instance = MagicMock()
    if error:
        instance.chat.completions.create = AsyncMock(side_effect=error)
    else:
        instance.chat.completions.create = AsyncMock(return_value=response or _mock_completion())
    mock_cls = MagicMock(return_value=instance)
    return patch("src.agent.groq_agent.AsyncOpenAI", mock_cls)


# ── Error-path tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_groq_key_returns_friendly_message(monkeypatch):
    """No key → friendly string, not an exception or env-var reference."""
    monkeypatch.setattr("src.agent.groq_agent.settings.GROQ_API_KEY", "")
    from src.agent.groq_agent import run_agent as run_with_fallback
    result = await run_with_fallback("What is my revenue?")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "GROQ" not in result
    assert "Railway" not in result
    assert "trouble" in result.lower() or "moment" in result.lower()


@pytest.mark.asyncio
async def test_groq_api_error_returns_friendly_message(monkeypatch):
    """Network/auth error from Groq → friendly string, not a raised exception."""
    monkeypatch.setattr("src.agent.groq_agent.settings.GROQ_API_KEY", "test-key")
    from src.agent.groq_agent import run_agent as run_with_fallback
    with _patched_client(error=Exception("Connection reset")):
        result = await run_with_fallback("Hello")
    assert isinstance(result, str)
    assert "trouble" in result.lower() or "moment" in result.lower()


@pytest.mark.asyncio
async def test_bad_request_error_returns_friendly_message(monkeypatch):
    """Groq 400 (malformed tool call) → friendly string."""
    from openai import BadRequestError
    monkeypatch.setattr("src.agent.groq_agent.settings.GROQ_API_KEY", "test-key")
    from src.agent.groq_agent import run_agent as run_with_fallback
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": {"message": "tool_use_failed"}}
    err = BadRequestError("tool_use_failed", response=mock_resp, body={})
    with _patched_client(error=err):
        result = await run_with_fallback("What products do I have?")
    assert isinstance(result, str)
    assert "tool_use_failed" not in result  # technical detail hidden


# ── Happy-path tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("prompt", [
    "Which products are running low on stock?",
    "What are my biggest raw material costs?",
    "Who are my top-rated vendors?",
    "How am I tracking against budget this month?",
    "What was my revenue last month?",
    "What's my repeat customer rate?",
    "How is my Meta Ads ROAS trending?",
    "What's my total ad spend this week?",
    "Which vendor delivers fastest?",
    "What are my packaging costs?",
])
async def test_common_prompt_returns_non_empty_response(prompt, monkeypatch):
    """All standard D2C prompts produce a non-empty, non-error response."""
    monkeypatch.setattr("src.agent.groq_agent.settings.GROQ_API_KEY", "test-key")
    from src.agent.groq_agent import run_agent as run_with_fallback
    with _patched_client(_mock_completion("Here is the answer for your question.")):
        result = await run_with_fallback(prompt)
    assert isinstance(result, str)
    assert len(result) > 0


# ── Tool dispatch tests ───────────────────────────────────────────────────────

def test_dispatch_coerces_limit_string_to_int():
    """'10' (string) must be coerced to 10 (int) before calling query_products."""
    from src.agent.groq_agent import _dispatch
    with patch("src.tools.query_tools.query_products") as mock_qp:
        mock_qp.return_value = {"products": [], "citations": []}
        _dispatch("query_products", {"limit": "10"})
        call_kwargs = mock_qp.call_args.kwargs if mock_qp.call_args else {}
        call_args = mock_qp.call_args.args if mock_qp.call_args else ()
        assert call_kwargs.get("limit") == 10 or (call_args and call_args[0] == 10)


def test_dispatch_drops_non_numeric_limit():
    """'all' (non-numeric string) must be dropped, not passed to query_products."""
    from src.agent.groq_agent import _dispatch
    with patch("src.tools.query_tools.query_products") as mock_qp:
        mock_qp.return_value = {"products": [], "citations": []}
        _dispatch("query_products", {"limit": "all"})
        call_kwargs = mock_qp.call_args.kwargs if mock_qp.call_args else {}
        assert "limit" not in call_kwargs


def test_dispatch_unknown_tool_returns_error_dict():
    from src.agent.groq_agent import _dispatch
    result = _dispatch("nonexistent_tool", {})
    assert isinstance(result, dict)
    assert "error" in result


def test_dispatch_tool_exception_returns_error_dict():
    """If the underlying tool raises, _dispatch should return an error dict."""
    from src.agent.groq_agent import _dispatch
    with patch("src.tools.query_tools.query_customers", side_effect=Exception("DB down")):
        result = _dispatch("query_customers", {})
    assert isinstance(result, dict)
    assert "error" in result
