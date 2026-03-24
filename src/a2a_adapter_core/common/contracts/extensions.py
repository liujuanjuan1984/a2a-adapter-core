from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Shared Metadata Fields
SHARED_SESSION_BINDING_FIELD = "metadata.shared.session.id"
SHARED_SESSION_METADATA_FIELD = "metadata.shared.session"
SHARED_MODEL_SELECTION_FIELD = "metadata.shared.model"
SHARED_STREAM_METADATA_FIELD = "metadata.shared.stream"
SHARED_PROGRESS_METADATA_FIELD = "metadata.shared.progress"
SHARED_INTERRUPT_METADATA_FIELD = "metadata.shared.interrupt"
SHARED_USAGE_METADATA_FIELD = "metadata.shared.usage"

# Standard A2A Extension URIs
SESSION_BINDING_EXTENSION_URI = "urn:a2a:session-binding/v1"
MODEL_SELECTION_EXTENSION_URI = "urn:a2a:model-selection/v1"
STREAMING_EXTENSION_URI = "urn:a2a:stream-hints/v1"
INTERRUPT_CALLBACK_EXTENSION_URI = "urn:a2a:interactive-interrupt/v1"
COMPATIBILITY_PROFILE_EXTENSION_URI = "urn:a2a:compatibility-profile/v1"
WIRE_CONTRACT_EXTENSION_URI = "urn:a2a:wire-contract/v1"

# Service Behavior Constants
SERVICE_BEHAVIOR_CLASSIFICATION = "service-level-semantic-enhancement"
CANCEL_IDEMPOTENCY_BEHAVIOR = "return_current_terminal_task"
TERMINAL_RESUBSCRIBE_BEHAVIOR = "replay_terminal_task_once_then_close"


@dataclass(frozen=True)
class SessionQueryMethodContract:
    method: str
    required_params: tuple[str, ...] = ()
    optional_params: tuple[str, ...] = ()
    unsupported_params: tuple[str, ...] = ()
    result_fields: tuple[str, ...] = ()
    items_type: str | None = None
    items_field: str | None = None
    notification_response_status: int | None = None
    pagination_mode: str | None = None
    execution_binding: str | None = None
    session_binding: str | None = None
    uses_upstream_session_context: bool | None = None
    notes: tuple[str, ...] = ()


SESSION_QUERY_PAGINATION_MODE = "limit"
SESSION_QUERY_PAGINATION_BEHAVIOR = "mixed"
SESSION_QUERY_DEFAULT_LIMIT = 20
SESSION_QUERY_MAX_LIMIT = 100
SESSION_QUERY_PAGINATION_PARAMS: tuple[str, ...] = ("limit",)
SESSION_QUERY_PAGINATION_UNSUPPORTED: tuple[str, ...] = ("cursor", "page", "size")

SESSION_QUERY_METHOD_CONTRACTS: dict[str, SessionQueryMethodContract] = {
    "list_sessions": SessionQueryMethodContract(
        method="a2a.sessions.list",
        optional_params=("limit", "query.limit"),
        unsupported_params=SESSION_QUERY_PAGINATION_UNSUPPORTED,
        result_fields=("items",),
        items_type="Task[]",
        items_field="items",
        notification_response_status=204,
        pagination_mode=SESSION_QUERY_PAGINATION_MODE,
    ),
    "get_session_messages": SessionQueryMethodContract(
        method="a2a.sessions.messages.list",
        required_params=("session_id",),
        optional_params=("limit", "query.limit"),
        unsupported_params=SESSION_QUERY_PAGINATION_UNSUPPORTED,
        result_fields=("items",),
        items_type="Message[]",
        items_field="items",
        notification_response_status=204,
        pagination_mode=SESSION_QUERY_PAGINATION_MODE,
    ),
    "prompt_async": SessionQueryMethodContract(
        method="a2a.sessions.prompt_async",
        required_params=("session_id", "request.parts"),
        optional_params=(
            "request.messageID",
            "request.agent",
            "request.system",
            "request.variant",
        ),
        result_fields=("ok", "session_id", "turn_id"),
        notification_response_status=204,
    ),
    "command": SessionQueryMethodContract(
        method="a2a.sessions.command",
        required_params=("session_id", "request.command"),
        optional_params=(
            "request.arguments",
            "request.messageID",
        ),
        result_fields=("item",),
        notification_response_status=204,
    ),
}

SESSION_QUERY_METHODS: dict[str, str] = {
    key: contract.method for key, contract in SESSION_QUERY_METHOD_CONTRACTS.items()
}

SESSION_CONTROL_METHOD_KEYS: tuple[str, ...] = ("prompt_async", "command")
SESSION_CONTROL_METHODS: dict[str, str] = {
    key: SESSION_QUERY_METHODS[key] for key in SESSION_CONTROL_METHOD_KEYS
}

SESSION_QUERY_ERROR_BUSINESS_CODES: dict[str, int] = {
    "SESSION_NOT_FOUND": -32001,
    "SESSION_FORBIDDEN": -32006,
    "UPSTREAM_UNREACHABLE": -32002,
    "UPSTREAM_HTTP_ERROR": -32003,
    "UPSTREAM_PAYLOAD_ERROR": -32005,
}


@dataclass(frozen=True)
class InterruptMethodContract:
    method: str
    required_params: tuple[str, ...] = ()
    optional_params: tuple[str, ...] = ()
    notification_response_status: int | None = None


@dataclass(frozen=True)
class ProviderDiscoveryMethodContract:
    method: str
    required_params: tuple[str, ...] = ()
    optional_params: tuple[str, ...] = ()
    result_fields: tuple[str, ...] = ()
    items_type: str | None = None
    notification_response_status: int | None = None


# Core JSON-RPC Methods Baseline
CORE_JSONRPC_METHODS: tuple[str, ...] = (
    "message/send",
    "message/stream",
    "tasks/get",
    "tasks/cancel",
    "tasks/resubscribe",
)

CORE_HTTP_ENDPOINTS: tuple[str, ...] = (
    "POST /v1/message:send",
    "POST /v1/message:stream",
    "GET /v1/tasks/{id}",
    "POST /v1/tasks/{id}:cancel",
    "GET /v1/tasks/{id}:subscribe",
)

# Shared Interrupt Callbacks
INTERRUPT_CALLBACK_METHOD_CONTRACTS: dict[str, InterruptMethodContract] = {
    "reply_permission": InterruptMethodContract(
        method="a2a.interrupt.permission.reply",
        required_params=("request_id", "reply"),
        optional_params=("message", "metadata"),
        notification_response_status=204,
    ),
    "reply_question": InterruptMethodContract(
        method="a2a.interrupt.question.reply",
        required_params=("request_id", "answers"),
        optional_params=("metadata",),
        notification_response_status=204,
    ),
    "reject_question": InterruptMethodContract(
        method="a2a.interrupt.question.reject",
        required_params=("request_id",),
        optional_params=("metadata",),
        notification_response_status=204,
    ),
}

INTERRUPT_CALLBACK_METHODS: dict[str, str] = {
    key: contract.method for key, contract in INTERRUPT_CALLBACK_METHOD_CONTRACTS.items()
}
