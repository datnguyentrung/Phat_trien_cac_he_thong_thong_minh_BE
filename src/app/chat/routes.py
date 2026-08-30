import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette import EventSourceResponse

from app.chat.runtime import ChatRuntime, SessionNotFoundError
from app.chat.schemas import ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)


def _runtime(request: Request) -> ChatRuntime:
    return request.app.state.chat_runtime


@router.post("/chat")
async def stream_chat(request: Request, payload: ChatRequest) -> EventSourceResponse:
    runtime = _runtime(request)
    try:
        session_id = await runtime.prepare_session(
            user_id=payload.user_id,
            session_id=payload.session_id,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    except Exception as exc:
        logger.exception("Failed to prepare chat session")
        raise HTTPException(
            status_code=503,
            detail="Dịch vụ tư vấn tạm thời không khả dụng. Vui lòng thử lại.",
        ) from exc

    return EventSourceResponse(
        runtime.stream(
            request=request,
            message=payload.message,
            user_id=payload.user_id,
            session_id=session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
        ping=15,
    )


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    request: Request,
    user_id: str = "guest",
) -> dict[str, object]:
    runtime = _runtime(request)
    try:
        messages = await runtime.get_history(
            user_id=user_id,
            session_id=session_id,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    return {"sessionId": session_id, "messages": messages}
