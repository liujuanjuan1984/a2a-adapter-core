from __future__ import annotations

from typing import Any

from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.types import Task


def sanitize_task_metadata(task: Task) -> Task:
    """Removes sensitive or internal metadata from Task objects before returning to client."""
    sanitized = task.model_copy(deep=True)
    duration_ms: int | float | None = None

    if isinstance(sanitized.metadata, dict):
        stats = sanitized.metadata.get("stats")
        if isinstance(stats, dict):
            duration = stats.get("duration_ms")
            if isinstance(duration, int | float):
                duration_ms = duration
    # Keep only duration_ms in metadata.stats
    sanitized.metadata = (
        {"stats": {"duration_ms": duration_ms}} if duration_ms is not None else None
    )

    if sanitized.history:
        for item in sanitized.history:
            if hasattr(item, "metadata"):
                item.metadata = None
    if sanitized.artifacts:
        for artifact in sanitized.artifacts:
            if hasattr(artifact, "metadata"):
                artifact.metadata = None
    return sanitized


class BaseA2ARequestHandler(DefaultRequestHandler):
    """Base A2A request handler with common cleaning and safety logic."""

    async def on_message_send(self, *args: Any, **kwargs: Any):
        result = await super().on_message_send(*args, **kwargs)
        if isinstance(result, Task):
            return sanitize_task_metadata(result)
        return result

    async def on_tasks_get(self, *args: Any, **kwargs: Any):
        result = await super().on_tasks_get(*args, **kwargs)
        if isinstance(result, Task):
            return sanitize_task_metadata(result)
        return result
