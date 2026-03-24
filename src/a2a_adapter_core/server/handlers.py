from __future__ import annotations

from typing import Any

from a2a.server.request_handlers.default_request_handler import (
    TERMINAL_TASK_STATES,
    DefaultRequestHandler,
)
from a2a.types import (
    MessageSendParams,
    Task,
    TaskIdParams,
    TaskNotCancelableError,
    TaskNotFoundError,
    TaskState,
)
from a2a.utils.errors import ServerError


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

    async def on_message_send(
        self,
        params: MessageSendParams,
        context: Any = None,
    ):
        result = await super().on_message_send(params, context)
        if isinstance(result, Task):
            return sanitize_task_metadata(result)
        return result

    async def on_tasks_get(
        self,
        params: TaskIdParams,
        context: Any = None,
    ) -> Task | None:
        result = await super().on_tasks_get(params, context)
        if isinstance(result, Task):
            return sanitize_task_metadata(result)
        return result

    async def on_cancel_task(
        self,
        params: TaskIdParams,
        context: Any = None,
    ) -> Task | None:
        """Idempotent cancel implementation."""
        task = await self.task_store.get(params.id, context)
        if not task:
            raise ServerError(error=TaskNotFoundError())

        # Idempotent contract:
        # repeated cancel on already-canceled task returns current terminal state.
        if task.status.state == TaskState.canceled:
            return task

        if task.status.state in TERMINAL_TASK_STATES:
            raise ServerError(
                error=TaskNotCancelableError(
                    message=f"Task cannot be canceled - current state: {task.status.state.value}"
                )
            )
        try:
            return await super().on_cancel_task(params, context)
        except ServerError as exc:
            # Race-safe idempotency: task may become canceled between pre-check and super call.
            if isinstance(exc.error, TaskNotCancelableError):
                refreshed = await self.task_store.get(params.id, context)
                if refreshed and refreshed.status.state == TaskState.canceled:
                    return refreshed
            raise

    async def on_resubscribe_to_task(
        self,
        params: TaskIdParams,
        context: Any = None,
    ):
        """Standard resubscribe contract: terminal tasks replay once then close."""
        task = await self.task_store.get(params.id, context)
        if not task:
            raise ServerError(error=TaskNotFoundError())

        if task.status.state in TERMINAL_TASK_STATES:
            yield task
            return

        async for event in super().on_resubscribe_to_task(params, context):
            yield event
