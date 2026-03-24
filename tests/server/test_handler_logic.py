import pytest
from unittest.mock import AsyncMock, MagicMock
from a2a.types import Task, TaskStatus, TaskState, TaskIdParams, TaskNotCancelableError
from a2a.utils.errors import ServerError
from a2a_adapter_core.server.handlers import BaseA2ARequestHandler


@pytest.mark.asyncio
async def test_handler_cancel_task_idempotency_already_canceled():
    task_store = MagicMock()
    # Mock a task that is already canceled
    canceled_task = Task(
        id="task-123", context_id="ctx", status=TaskStatus(state=TaskState.canceled)
    )
    task_store.get = AsyncMock(return_value=canceled_task)

    handler = BaseA2ARequestHandler(
        agent_executor=MagicMock(),
        task_store=task_store,
        queue_manager=MagicMock(),
        request_context_builder=MagicMock(),
    )

    # Should return the task immediately without calling super().on_cancel_task
    result = await handler.on_cancel_task(TaskIdParams(id="task-123"))
    assert result == canceled_task
    task_store.get.assert_called_once()


@pytest.mark.asyncio
async def test_handler_resubscribe_terminal_task():
    task_store = MagicMock()
    # Mock a terminal task (completed)
    terminal_task = Task(
        id="task-123", context_id="ctx", status=TaskStatus(state=TaskState.completed)
    )
    task_store.get = AsyncMock(return_value=terminal_task)

    handler = BaseA2ARequestHandler(
        agent_executor=MagicMock(),
        task_store=task_store,
        queue_manager=MagicMock(),
        request_context_builder=MagicMock(),
    )

    # Use list() to consume the async generator
    events = []
    async for event in handler.on_resubscribe_to_task(TaskIdParams(id="task-123")):
        events.append(event)

    assert len(events) == 1
    assert events[0] == terminal_task
