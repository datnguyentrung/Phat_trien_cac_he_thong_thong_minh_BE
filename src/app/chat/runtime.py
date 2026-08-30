import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Protocol

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

from app.chat.grounding import (
    UNGROUNDED_MEDICATION_MESSAGE,
    requires_medication_grounding,
)
from app.chat.markdown import FinalSummaryMarkdownStream
from app.chat.progress import bind_queue, push_progress
from app.chat.schemas import DoneChunk, ErrorChunk, MessageChunk


class RequestState(Protocol):
    async def is_disconnected(self) -> bool: ...


class SessionNotFoundError(LookupError):
    pass


EMPTY_RESPONSE_MESSAGE = (
    "Mình chưa thể tạo câu trả lời cho yêu cầu này. Vui lòng thử lại."
)

_SECTION_PROGRESS: dict[str, tuple[int, str]] = {
    "### Tóm tắt nhu cầu của bạn": (
        74,
        "Đang viết tóm tắt nhu cầu...",
    ),
    "### Cảnh báo cần ưu tiên": (
        78,
        "Đang viết cảnh báo cần ưu tiên...",
    ),
    "### Các sản phẩm được tìm thấy để tham khảo": (
        82,
        "Đang trình bày sản phẩm tham khảo...",
    ),
    "### Bảng đối chiếu nhanh": (
        86,
        "Đang dựng bảng đối chiếu nhanh...",
    ),
    "### Kết luận an toàn": (
        90,
        "Đang viết kết luận an toàn...",
    ),
    "### Nguồn và giới hạn dữ liệu": (
        94,
        "Đang tổng hợp nguồn và giới hạn...",
    ),
}


def _text_from_event(event: Any) -> str:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) if content else None
    if not parts:
        return ""
    return "".join(
        part.text
        for part in parts
        if isinstance(getattr(part, "text", None), str)
        and not getattr(part, "thought", False)
        and not getattr(part, "function_call", None)
        and not getattr(part, "function_response", None)
    )


class ChatRuntime:
    def __init__(
        self,
        runner: Any,
        session_service: Any,
        app_name: str,
        heartbeat_seconds: float = 5.0,
    ) -> None:
        self._runner = runner
        self._session_service = session_service
        self._app_name = app_name
        self._heartbeat_seconds = heartbeat_seconds

    async def prepare_session(self, user_id: str, session_id: str | None) -> str:
        if session_id:
            session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id=user_id,
                session_id=session_id,
            )
            if session is None:
                raise SessionNotFoundError(session_id)
            return session_id

        new_session_id = str(uuid.uuid4())
        await self._session_service.create_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=new_session_id,
            state={"phase": "INIT"},
        )
        return new_session_id

    async def get_history(
        self,
        user_id: str,
        session_id: str,
    ) -> list[dict[str, str]]:
        """Reconstruct the user/model text history from the ADK session."""
        session = await self._session_service.get_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            raise SessionNotFoundError(session_id)

        messages: list[dict[str, str]] = []
        for event in getattr(session, "events", None) or []:
            if getattr(event, "partial", False):
                continue
            role = getattr(getattr(event, "content", None), "role", None)
            if role not in ("user", "model"):
                continue
            text = _text_from_event(event)
            if not text:
                continue
            created_at = datetime.now(UTC).isoformat()
            timestamp = getattr(event, "timestamp", None)
            if timestamp is not None and callable(getattr(timestamp, "isoformat", None)):
                created_at = timestamp.isoformat()
            messages.append(
                {
                    "id": getattr(event, "id", None) or str(uuid.uuid4()),
                    "role": role,
                    "content": text,
                    "createdAt": created_at,
                }
            )
        return messages

    async def stream(
        self,
        request: RequestState,
        message: str,
        user_id: str,
        session_id: str,
    ) -> AsyncIterator[dict[str, str]]:
        if await request.is_disconnected():
            return

        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        bind_queue(queue)
        push_progress("Đang xử lý câu hỏi của bạn...", 5)
        push_progress("Đang phân tích yêu cầu...", 10)

        events = self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)],
            ),
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )

        events_closed = False

        async def _close_events() -> None:
            nonlocal events_closed
            if events_closed:
                return
            events_closed = True
            close = getattr(events, "aclose", None)
            if close is not None:
                await close()

        async def _produce() -> None:
            streamed_partial_text = False
            streamed_any = False
            tool_called = False
            tool_responded = False
            buffered_text: list[str] = []
            buffered_final = ""
            streamed_chunks = 0
            reasoning_chunks = 0
            highest_percent = 0

            def _progress(status_text: str, progress_percent: int) -> None:
                nonlocal highest_percent
                if progress_percent > highest_percent:
                    highest_percent = progress_percent
                    push_progress(status_text, progress_percent)

            def _on_heading(canonical: str) -> None:
                milestone = _SECTION_PROGRESS.get(canonical)
                if milestone is not None:
                    _progress(milestone[1], milestone[0])

            summary_stream = FinalSummaryMarkdownStream(on_heading=_on_heading)
            next_event: asyncio.Task[Any] | None = None
            try:
                next_event = asyncio.create_task(events.__anext__())
                await asyncio.sleep(0)
                heartbeat_calls = 0
                while True:
                    if await request.is_disconnected():
                        return
                    done, _ = await asyncio.wait(
                        {next_event},
                        timeout=self._heartbeat_seconds,
                    )
                    if next_event not in done:
                        heartbeat_calls += 1
                        if not tool_called:
                            _progress(
                                "Đang suy nghĩ và phân tích câu hỏi...",
                                min(14, 10 + heartbeat_calls),
                            )
                        elif tool_responded and not streamed_any:
                            _progress(
                                "Đang suy nghĩ về dữ liệu...",
                                min(69, 62 + heartbeat_calls),
                            )
                        continue
                    try:
                        event = next_event.result()
                    except StopAsyncIteration:
                        break
                    next_event = asyncio.create_task(events.__anext__())
                    heartbeat_calls = 0

                    parts = (
                        event.content.parts
                        if getattr(event, "content", None) and event.content.parts
                        else []
                    )
                    if any(part.function_call is not None for part in parts):
                        tool_called = True
                        buffered_text.clear()
                        buffered_final = ""
                        _progress(
                            "Đã xác định chủ đề thuốc, đang tra cứu dữ liệu...",
                            15,
                        )
                    if any(part.function_response is not None for part in parts):
                        tool_responded = True
                        _progress(
                            "Đang kiểm tra nguồn và giới hạn dữ liệu...",
                            60,
                        )

                    text = _text_from_event(event)
                    is_partial = getattr(event, "partial", None) is True
                    has_thought = any(
                        getattr(part, "thought", False)
                        or getattr(part, "thought_part", None) is not None
                        for part in parts
                    )
                    if not text and has_thought:
                        reasoning_chunks += 1
                        if not tool_called:
                            _progress(
                                "Đang suy nghĩ và phân tích câu hỏi...",
                                min(14, 11 + reasoning_chunks // 20),
                            )
                        elif tool_responded and not streamed_any:
                            _progress(
                                "Đang phân tích dữ liệu...",
                                min(69, 62 + reasoning_chunks // 30),
                            )
                        continue
                    if not text:
                        continue
                    if not tool_called:
                        if is_partial:
                            buffered_text.append(text)
                        else:
                            buffered_final = text
                        continue
                    if not tool_responded:
                        continue
                    if is_partial or not streamed_partial_text:
                        if not streamed_any:
                            _progress("Đang soạn câu trả lời...", 70)
                        for normalized_text in summary_stream.feed(text):
                            chunk = MessageChunk(
                                content=normalized_text,
                                sessionId=session_id,
                            )
                            await queue.put({"data": chunk.model_dump_json()})
                            streamed_any = True
                            streamed_chunks += 1
                            if streamed_chunks % 3 == 0:
                                fallback = min(72, 70 + streamed_chunks)
                                _progress(
                                    "Đang soạn câu trả lời... "
                                    f"({streamed_chunks} đoạn)",
                                    fallback,
                                )
                        streamed_partial_text = streamed_partial_text or is_partial

                if not tool_called:
                    text = (
                        UNGROUNDED_MEDICATION_MESSAGE
                        if requires_medication_grounding(message)
                        else "".join(buffered_text) or buffered_final
                    )
                    if text:
                        if not streamed_any:
                            _progress("Đang soạn câu trả lời...", 70)
                        chunk = MessageChunk(content=text, sessionId=session_id)
                        await queue.put({"data": chunk.model_dump_json()})
                        streamed_any = True
                elif tool_responded and (remaining := summary_stream.finish()):
                    chunk = MessageChunk(content=remaining, sessionId=session_id)
                    await queue.put({"data": chunk.model_dump_json()})
                    streamed_any = True

                if not streamed_any:
                    chunk = MessageChunk(
                        content=EMPTY_RESPONSE_MESSAGE,
                        sessionId=session_id,
                    )
                    await queue.put({"data": chunk.model_dump_json()})

                _progress("Đang kiểm tra lần cuối...", 96)
                done = DoneChunk(sessionId=session_id)
                await queue.put({"data": done.model_dump_json()})
                await queue.put({"data": "[DONE]"})
            except asyncio.CancelledError:
                raise
            except Exception:
                error = ErrorChunk(
                    error=(
                        "Dịch vụ tư vấn AI tạm thời không khả dụng. "
                        "Vui lòng thử lại."
                    ),
                    sessionId=session_id,
                )
                await queue.put({"data": error.model_dump_json()})
                await queue.put({"data": "[DONE]"})
            finally:
                if next_event is not None and not next_event.done():
                    next_event.cancel()
                queue.put_nowait(None)
                await _close_events()

        producer = asyncio.create_task(_produce())
        await asyncio.sleep(0)
        try:
            while True:
                if await request.is_disconnected():
                    return
                item = await queue.get()
                if item is None:
                    return
                if item.get("type") == "progress":
                    item["sessionId"] = session_id
                    yield {"data": json.dumps(item, ensure_ascii=False)}
                else:
                    yield item
        finally:
            if not producer.done():
                producer.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await producer
            await _close_events()
