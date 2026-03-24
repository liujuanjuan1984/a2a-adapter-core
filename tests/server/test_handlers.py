import pytest
from a2a.types import Task, TaskStatus, TaskState, Message, Role, Part, TextPart, Artifact
from a2a_adapter_core.server.handlers import sanitize_task_metadata


def test_sanitize_task_metadata_removes_internal_fields():
    task = Task(
        id="task-123",
        context_id="ctx-123",
        status=TaskStatus(state=TaskState.completed),
        metadata={"stats": {"duration_ms": 1500, "internal_debug": "secret"}, "internal_id": "999"},
        history=[
            Message(
                message_id="msg-1",
                role=Role.agent,
                parts=[Part(root=TextPart(text="hi"))],
                metadata={"debug": "hidden"},
            )
        ],
        artifacts=[
            Artifact(
                artifact_id="art-1",
                parts=[Part(root=TextPart(text="data"))],
                metadata={"internal_path": "/tmp"},
            )
        ],
    )

    sanitized = sanitize_task_metadata(task)

    # Check stats (it should be exactly {"stats": {"duration_ms": 1500}})
    assert sanitized.metadata["stats"] == {"duration_ms": 1500}
    assert "internal_id" not in sanitized.metadata

    # Check history and artifacts
    assert sanitized.history[0].metadata is None
    assert sanitized.artifacts[0].metadata is None

    # Check original is not modified (deep copy)
    assert task.metadata["stats"]["internal_debug"] == "secret"
    assert task.history[0].metadata is not None
