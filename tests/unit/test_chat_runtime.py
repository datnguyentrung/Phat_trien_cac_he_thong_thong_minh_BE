import asyncio
import json
from types import SimpleNamespace

import pytest
from google.adk.events import Event
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from app.chat.progress import push_progress
from app.chat.runtime import ChatRuntime, SessionNotFoundError


class FakeSessionService:
    def __init__(self) -> None:
        self.sessions = {}

    async def create_session(self, *, app_name, user_id, session_id, state):
        session = SimpleNamespace(id=session_id, state=state)
        self.sessions[(app_name, user_id, session_id)] = session
        return session

    async def get_session(self, *, app_name, user_id, session_id):
        return self.sessions.get((app_name, user_id, session_id))


class EventHistorySessionService(FakeSessionService):
    def __init__(self, events: list[Event]) -> None:
        super().__init__()
        self._events = events

    async def create_session(self, *, app_name, user_id, session_id, state):
        session = SimpleNamespace(id=session_id, state=state, events=list(self._events))
        self.sessions[(app_name, user_id, session_id)] = session
        return session


class FakeRunner:
    async def run_async(self, **kwargs):
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="consult_medication",
                        args={"condition": "đau đầu", "product_keyword": "thuốc"},
                    )
                ],
            ),
        )
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name="consult_medication",
                        response={"status": "success"},
                    )
                ],
            ),
        )
        yield Event(
            author="medication_consultation_agent",
            partial=True,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="### Tóm tắt ")],
            ),
        )
        yield Event(
            author="medication_consultation_agent",
            partial=False,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="### Tóm tắt nhu cầu")],
            ),
        )
        yield Event(
            author="medication_consultation_agent",
            partial=True,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="nhu cầu")],
            ),
        )


class ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


class DisconnectingRequest:
    def __init__(self) -> None:
        self.calls = 0

    async def is_disconnected(self) -> bool:
        self.calls += 1
        return self.calls > 1


class CloseAwareRunner:
    def __init__(self) -> None:
        self.closed = False

    async def run_async(self, **kwargs):
        try:
            yield Event(
                author="medication_consultation_agent",
                partial=True,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="không được gửi")],
                ),
            )
        finally:
            self.closed = True


class FailingRunner:
    async def run_async(self, **kwargs):
        raise RuntimeError(
            "401 https://secret.example/v1 key=do-not-leak internal prompt"
        )
        yield


class NormalChatRunner:
    async def run_async(self, **kwargs):
        for text in ("Xin ", "chào"):
            yield Event(
                author="medication_consultation_agent",
                partial=True,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=text)],
                ),
            )
        yield Event(
            author="medication_consultation_agent",
            partial=False,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="Xin chào")],
            ),
        )


class EmptyRunner:
    async def run_async(self, **kwargs):
        return
        yield  # pragma: no cover


class HeadingRunner:
    async def run_async(self, **kwargs):
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="consult_medication",
                        args={"condition": "đau đầu", "product_keyword": "thuốc"},
                    )
                ],
            ),
        )
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name="consult_medication",
                        response={"status": "success"},
                    )
                ],
            ),
        )
        for text in (
            "### Tóm tắt nhu cầu của bạn\n",
            "Nội dung tóm tắt.\n",
            "### Cảnh báo cần ưu tiên\n",
            "Nội dung cảnh báo.\n",
            "### Kết luận an toàn\n",
            "Kết luận.\n",
        ):
            yield Event(
                author="medication_consultation_agent",
                partial=True,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=text)],
                ),
            )


class ProgressPushingRunner:
    async def run_async(self, **kwargs):
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="consult_medication",
                        args={"condition": "đau đầu", "product_keyword": "thuốc"},
                    )
                ],
            ),
        )
        push_progress("Đang tra cứu Knowledge Graph...", 20)
        await asyncio.sleep(0.01)
        push_progress("Đang tìm kiếm sản phẩm tham khảo trên Long Châu...", 30)
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name="consult_medication",
                        response={"status": "success"},
                    )
                ],
            ),
        )
        yield Event(
            author="medication_consultation_agent",
            partial=True,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="### Tóm tắt nhu cầu của bạn\n")],
            ),
        )


class ThoughtRunner:
    async def run_async(self, **kwargs):
        for text in ("đang suy nghĩ", "về câu hỏi"):
            yield Event(
                author="medication_consultation_agent",
                partial=True,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=text, thought=True)],
                ),
            )
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="consult_medication",
                        args={"condition": "đau đầu", "product_keyword": "thuốc"},
                    )
                ],
            ),
        )
        yield Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name="consult_medication",
                        response={"status": "success"},
                    )
                ],
            ),
        )
        for text in ("suy nghĩ thêm", "về dữ liệu"):
            yield Event(
                author="medication_consultation_agent",
                partial=True,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=text, thought=True)],
                ),
            )
        yield Event(
            author="medication_consultation_agent",
            partial=True,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="### Tóm tắt nhu cầu của bạn\n")],
            ),
        )


class SlowStartRunner:
    def __init__(self, delay: float) -> None:
        self.delay = delay

    async def run_async(self, **kwargs):
        await asyncio.sleep(self.delay)
        yield Event(
            author="medication_consultation_agent",
            partial=True,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="Xin chào\n")],
            ),
        )


@pytest.mark.asyncio
async def test_prepare_session_creates_and_resumes_for_same_user() -> None:
    sessions = FakeSessionService()
    runtime = ChatRuntime(FakeRunner(), sessions, app_name="app")

    session_id = await runtime.prepare_session(user_id="u1", session_id=None)
    resumed = await runtime.prepare_session(user_id="u1", session_id=session_id)

    assert resumed == session_id


@pytest.mark.asyncio
async def test_prepare_session_rejects_session_owned_by_another_user() -> None:
    sessions = FakeSessionService()
    runtime = ChatRuntime(FakeRunner(), sessions, app_name="app")
    session_id = await runtime.prepare_session(user_id="u1", session_id=None)

    with pytest.raises(SessionNotFoundError):
        await runtime.prepare_session(user_id="u2", session_id=session_id)


@pytest.mark.asyncio
async def test_get_history_returns_only_user_and_model_text_in_order() -> None:
    events = [
        Event(
            author="user",
            content=types.Content(
                role="user",
                parts=[types.Part.from_text(text="Tôi cần tư vấn")],
            ),
        ),
        Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="consult_medication",
                        args={"condition": "đau đầu", "product_keyword": "thuốc"},
                    )
                ],
            ),
        ),
        Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(text="### Tóm tắt nhu cầu của bạn\n")
                ],
            ),
        ),
        Event(
            author="medication_consultation_agent",
            partial=True,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="bản nháp không lưu")],
            ),
        ),
        Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[types.Part(text="suy nghĩ bị lọc", thought=True)],
            ),
        ),
        Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name="consult_medication",
                        response={"status": "success"},
                    )
                ],
            ),
        ),
        Event(
            author="medication_consultation_agent",
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text="Kết luận an toàn.")],
            ),
        ),
    ]
    service = EventHistorySessionService(events)
    runtime = ChatRuntime(FakeRunner(), service, app_name="app")
    session_id = await runtime.prepare_session(user_id="u1", session_id=None)

    history = await runtime.get_history(user_id="u1", session_id=session_id)

    assert [(message["role"], message["content"]) for message in history] == [
        ("user", "Tôi cần tư vấn"),
        ("model", "### Tóm tắt nhu cầu của bạn\n"),
        ("model", "Kết luận an toàn."),
    ]
    assert all(message["id"] for message in history)
    assert all(message["createdAt"] for message in history)


@pytest.mark.asyncio
async def test_get_history_rejects_session_owned_by_another_user() -> None:
    service = EventHistorySessionService([])
    runtime = ChatRuntime(FakeRunner(), service, app_name="app")
    session_id = await runtime.prepare_session(user_id="u1", session_id=None)

    with pytest.raises(SessionNotFoundError):
        await runtime.get_history(user_id="u2", session_id=session_id)


@pytest.mark.asyncio
async def test_stream_emits_only_text_then_done_marker() -> None:
    sessions = FakeSessionService()
    runtime = ChatRuntime(FakeRunner(), sessions, app_name="app")
    session_id = await runtime.prepare_session(user_id="u1", session_id=None)

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Tôi cần tư vấn",
            user_id="u1",
            session_id=session_id,
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    assert payloads[0]["type"] == "progress"
    assert payloads[0]["progressPercent"] == 5
    messages = [payload for payload in payloads if payload["type"] != "progress"]
    assert [payload["type"] for payload in messages] == ["message", "done"]
    assert messages[0]["content"] == "### Tóm tắt nhu cầu của bạn"
    assert all(payload["sessionId"] == session_id for payload in payloads)
    assert events[-1] == {"data": "[DONE]"}


@pytest.mark.asyncio
async def test_disconnect_closes_adk_generator_without_emitting_content() -> None:
    runner = CloseAwareRunner()
    runtime = ChatRuntime(runner, FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=DisconnectingRequest(),
            message="Tư vấn",
            user_id="u1",
            session_id="s1",
        )
    ]

    assert events == []
    assert runner.closed is True


@pytest.mark.asyncio
async def test_upstream_error_is_sanitized_in_sse() -> None:
    runtime = ChatRuntime(FailingRunner(), FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Tư vấn",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    error_payload = next(payload for payload in payloads if payload["type"] == "error")
    assert "secret.example" not in error_payload["error"]
    assert "do-not-leak" not in error_payload["error"]
    assert events[-1] == {"data": "[DONE]"}


@pytest.mark.asyncio
async def test_normal_chat_is_not_duplicated_by_aggregated_final_event() -> None:
    runtime = ChatRuntime(NormalChatRunner(), FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Xin chào",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    messages = [payload for payload in payloads if payload["type"] == "message"]
    assert [message["content"] for message in messages] == ["Xin chào"]


@pytest.mark.asyncio
async def test_medication_question_fails_closed_when_model_skips_tool() -> None:
    runtime = ChatRuntime(NormalChatRunner(), FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Tôi cần tư vấn thuốc đau đầu",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    message = next(payload["content"] for payload in payloads if payload["type"] == "message")
    assert "chưa đối chiếu được dữ liệu" in message
    assert "Xin chào" not in message


@pytest.mark.asyncio
async def test_empty_response_emits_fallback_message() -> None:
    runtime = ChatRuntime(EmptyRunner(), FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Xin chào",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    messages = [payload for payload in payloads if payload["type"] != "progress"]
    assert [payload["type"] for payload in messages] == ["message", "done"]
    assert "chưa thể tạo câu trả lời" in messages[0]["content"]
    assert events[-1] == {"data": "[DONE]"}


@pytest.mark.asyncio
async def test_stream_reports_section_milestones_while_writing() -> None:
    runtime = ChatRuntime(HeadingRunner(), FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Tôi cần tư vấn",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    progress = [payload for payload in payloads if payload["type"] == "progress"]
    statuses = [payload["statusText"] for payload in progress]
    assert "Đang viết tóm tắt nhu cầu..." in statuses
    assert "Đang viết cảnh báo cần ưu tiên..." in statuses
    assert "Đang viết kết luận an toàn..." in statuses
    percents = [payload["progressPercent"] for payload in progress]
    assert percents == sorted(percents)
    assert percents[-1] == 96


@pytest.mark.asyncio
async def test_stream_surfaces_tool_phases_before_any_message() -> None:
    runtime = ChatRuntime(ProgressPushingRunner(), FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Tư vấn thuốc đau đầu",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    progress = [payload for payload in payloads if payload["type"] == "progress"]
    statuses = [payload["statusText"] for payload in progress]
    first_message_index = next(
        index for index, payload in enumerate(payloads) if payload["type"] == "message"
    )
    assert "Đang tra cứu Knowledge Graph..." in statuses
    assert "Đang tìm kiếm sản phẩm tham khảo trên Long Châu..." in statuses
    assert all(payload["type"] == "progress" for payload in payloads[:first_message_index])


@pytest.mark.asyncio
async def test_stream_reports_thinking_progress_during_reasoning() -> None:
    runtime = ChatRuntime(ThoughtRunner(), FakeSessionService(), app_name="app")

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Tư vấn thuốc đau đầu",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    progress = [payload for payload in payloads if payload["type"] == "progress"]
    statuses = [payload["statusText"] for payload in progress]
    assert "Đang suy nghĩ và phân tích câu hỏi..." in statuses
    assert "Đang phân tích dữ liệu..." in statuses
    percents = [payload["progressPercent"] for payload in progress]
    assert percents == sorted(percents)


@pytest.mark.asyncio
async def test_stream_heartbeat_keeps_progress_moving_while_waiting() -> None:
    runtime = ChatRuntime(
        SlowStartRunner(delay=0.08),
        FakeSessionService(),
        app_name="app",
        heartbeat_seconds=0.02,
    )

    events = [
        event
        async for event in runtime.stream(
            request=ConnectedRequest(),
            message="Tư vấn thuốc đau đầu",
            user_id="u1",
            session_id="s1",
        )
    ]

    payloads = [json.loads(event["data"]) for event in events[:-1]]
    progress = [payload for payload in payloads if payload["type"] == "progress"]
    thinking = [
        payload
        for payload in progress
        if payload["statusText"] == "Đang suy nghĩ và phân tích câu hỏi..."
    ]
    assert thinking
    assert any(payload["progressPercent"] >= 11 for payload in thinking)


@pytest.mark.asyncio
async def test_prepare_session_with_real_session_service(tmp_path) -> None:
    db_path = tmp_path / "adk_sessions.db"
    session_service = DatabaseSessionService(
        db_url=f"sqlite+aiosqlite:///{db_path.as_posix()}"
    )
    runtime = ChatRuntime(FakeRunner(), session_service, app_name="app")
    try:
        session_id = await runtime.prepare_session(user_id="u1", session_id=None)
        assert session_id

        resumed = await runtime.prepare_session(
            user_id="u1",
            session_id=session_id,
        )
        assert resumed == session_id

        with pytest.raises(SessionNotFoundError):
            await runtime.prepare_session(user_id="u2", session_id=session_id)
    finally:
        await session_service.close()
