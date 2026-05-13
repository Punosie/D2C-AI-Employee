import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from src.agent.agent import root_agent

CHECKS = [
    "Check if ROAS dropped more than 20% week-over-week on any platform. Propose a concrete action and log it.",
    "Check if any products have fewer than 10 units of inventory. Propose a reorder action and log it.",
    "Check the repeat customer rate for the last 30 days. If it is below 20%, propose a retention action and log it.",
]


async def run_autonomous_checks():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="d2c_agent",
        session_service=session_service,
    )

    for prompt in CHECKS:
        session = await session_service.create_session(
            app_name="d2c_agent",
            user_id="autonomous",
        )
        message = Content(role="user", parts=[Part(text=prompt)])

        print(f"\n--- CHECK: {prompt[:60]} ---")
        async for event in runner.run_async(
            user_id="autonomous",
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response():
                print(event.content.parts[0].text)


if __name__ == "__main__":
    asyncio.run(run_autonomous_checks())
