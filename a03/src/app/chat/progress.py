from __future__ import annotations

import asyncio
from contextvars import ContextVar
from typing import Any

_current_queue: ContextVar[asyncio.Queue[dict[str, Any] | None] | None] = (
    ContextVar("_chat_progress_queue", default=None)
)


def bind_queue(queue: asyncio.Queue[dict[str, Any] | None]) -> None:
    """Bind the SSE progress queue to the current async context."""
    _current_queue.set(queue)


def push_progress(status_text: str, progress_percent: int) -> None:
    """Push one progress chunk if a queue is bound; otherwise no-op."""
    queue = _current_queue.get()
    if queue is None:
        return
    queue.put_nowait(
        {
            "type": "progress",
            "statusText": status_text,
            "progressPercent": progress_percent,
        }
    )
