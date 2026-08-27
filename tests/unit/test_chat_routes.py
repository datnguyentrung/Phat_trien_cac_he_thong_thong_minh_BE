from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.chat.routes import router
from app.chat.runtime import SessionNotFoundError


class FakeChatRuntime:
    def __init__(
        self,
        *,
        prepare_error: Exception | None = None,
        history_error: Exception | None = None,
    ) -> None:
        self.prepare_error = prepare_error
        self.history_error = history_error

    async def prepare_session(self, user_id: str, session_id: str | None) -> str:
        if self.prepare_error is not None:
            raise self.prepare_error
        assert user_id == "guest"
        return session_id or "new-session"

    async def stream(self, **kwargs) -> AsyncIterator[dict[str, str]]:
        yield {
            "data": (
                '{"type":"message","content":"### Tóm tắt",'
                '"sessionId":"new-session","phase":"FINAL_SUMMARY"}'
            )
        }
        yield {"data": '{"type":"done","sessionId":"new-session"}'}
        yield {"data": "[DONE]"}

    async def get_history(self, user_id: str, session_id: str) -> list[dict[str, str]]:
        if self.history_error is not None:
            raise self.history_error
        return []


def test_chat_route_exposes_public_sse_contract() -> None:
    app = FastAPI()
    app.state.chat_runtime = FakeChatRuntime()
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Tôi cần tư vấn", "userId": "guest"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type":"message"' in response.text
    assert '"phase":"FINAL_SUMMARY"' in response.text
    assert '"type":"done"' in response.text
    assert "data: [DONE]" in response.text


def test_chat_route_returns_404_when_session_missing() -> None:
    app = FastAPI()
    app.state.chat_runtime = FakeChatRuntime(
        prepare_error=SessionNotFoundError("missing-session")
    )
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Tôi cần tư vấn", "userId": "guest"},
        )

    assert response.status_code == 404


def test_chat_route_sanitizes_prepare_session_failure() -> None:
    app = FastAPI()
    app.state.chat_runtime = FakeChatRuntime(
        prepare_error=RuntimeError("db password leaked in error")
    )
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Tôi cần tư vấn", "userId": "guest"},
        )

    assert response.status_code == 503
    assert "password" not in response.text


def test_chat_route_rejects_blank_message() -> None:
    app = FastAPI()
    app.state.chat_runtime = FakeChatRuntime()
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "   ", "userId": "guest"},
        )

    assert response.status_code == 422


def test_chat_history_route_returns_messages() -> None:
    app = FastAPI()
    app.state.chat_runtime = FakeChatRuntime()
    app.include_router(router)

    with TestClient(app) as client:
        response = client.get("/chat/history/new-session")

    assert response.status_code == 200
    assert response.json() == {"sessionId": "new-session", "messages": []}


def test_chat_history_route_returns_404_when_session_missing() -> None:
    app = FastAPI()
    app.state.chat_runtime = FakeChatRuntime(
        history_error=SessionNotFoundError("missing-session")
    )
    app.include_router(router)

    with TestClient(app) as client:
        response = client.get("/chat/history/missing-session")

    assert response.status_code == 404
