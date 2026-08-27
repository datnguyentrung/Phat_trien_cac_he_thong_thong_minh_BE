import pytest
from google.adk.agents import Agent
from google.adk.models import BaseLlm, LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class ToolFirstFakeModel(BaseLlm):
    async def generate_content_async(self, llm_request, stream=False):
        has_tool_result = any(
            part.function_response is not None
            for content in llm_request.contents
            for part in (content.parts or [])
        )
        if not has_tool_result:
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part.from_function_call(
                            name="fake_consult_medication",
                            args={
                                "condition": "đau đầu",
                                "product_keyword": "paracetamol",
                            },
                        )
                    ],
                )
            )
            return

        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="### Tóm tắt nhu cầu của bạn")],
            )
        )


@pytest.mark.asyncio
async def test_adk_executes_tool_before_product_summary() -> None:
    tool_calls: list[tuple[str, str]] = []

    async def fake_consult_medication(
        condition: str,
        product_keyword: str,
    ) -> dict:
        tool_calls.append((condition, product_keyword))
        return {"status": "success", "products": [{"name": "Sản phẩm A"}]}

    agent = Agent(
        name="tool_first_agent",
        model=ToolFirstFakeModel(model="fake-tool-model"),
        instruction="Luôn gọi tool trước khi trả sản phẩm.",
        tools=[fake_consult_medication],
    )
    sessions = InMemorySessionService()
    session = await sessions.create_session(
        app_name="test",
        user_id="user",
        session_id="session",
    )
    runner = Runner(agent=agent, app_name="test", session_service=sessions)
    events = [
        event
        async for event in runner.run_async(
            user_id="user",
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text="Tư vấn đau đầu")],
            ),
        )
    ]

    function_call_index = next(
        index
        for index, event in enumerate(events)
        if event.get_function_calls()
    )
    final_text_index = next(
        index
        for index, event in enumerate(events)
        if event.content
        and any(part.text for part in (event.content.parts or []))
    )
    assert tool_calls == [("đau đầu", "paracetamol")]
    assert function_call_index < final_text_index
