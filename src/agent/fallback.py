# Re-exports for backward compatibility — logic lives in groq_agent.py
from src.agent.groq_agent import run_agent as run_with_fallback, _dispatch  # noqa: F401
