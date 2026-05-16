"""
Autonomous agent checks powered by Groq.
Run manually:  python -m src.agent.runner
Scheduled:     added to APScheduler in src/api.py startup (every 24 h)
"""
import asyncio
import logging
from src.agent.groq_agent import run_agent

logger = logging.getLogger(__name__)

CHECKS = [
    "Check if ROAS dropped more than 20% week-over-week on any platform. "
    "Propose a concrete action and log it using log_agent_run.",

    "Check if any products have fewer than 10 units of inventory. "
    "Propose a reorder action and log it using log_agent_run.",

    "Check the repeat customer rate for the last 30 days. "
    "If it is below 20%, propose a retention action and log it using log_agent_run.",

    "Review the monthly budget vs actual for the most recent month. "
    "Flag any category more than 10% over budget and log findings using log_agent_run.",
]


async def run_autonomous_checks():
    logger.info("Starting autonomous agent checks (%d checks)", len(CHECKS))
    for i, prompt in enumerate(CHECKS, 1):
        logger.info("Check %d/%d: %s", i, len(CHECKS), prompt[:60])
        try:
            result = await run_agent(prompt)
            logger.info("Check %d result: %s", i, result[:120])
        except Exception as e:
            logger.error("Check %d failed: %s", i, e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(run_autonomous_checks())
