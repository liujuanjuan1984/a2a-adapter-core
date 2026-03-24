from __future__ import annotations

from typing import Any

from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.types import JSONRPCError, JSONRPCResponse
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from .response_limits import (
    TRUNCATED_RESPONSE_HEADER,
    ResponseLimitConfig,
    coerce_response_limit_config,
    limit_json_response_content,
)


class BaseA2AFastAPIApplication(A2AFastAPIApplication):
    """Enhanced A2A JSON-RPC application with common gateway features."""

    def __init__(
        self,
        *args: Any,
        response_limit: ResponseLimitConfig | dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._response_limit = coerce_response_limit_config(response_limit)

    def _build_oversize_response(
        self,
        *,
        request_id: Any,
        max_bytes: int,
        actual_bytes: int,
    ) -> Response:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": (
                        "Gateway response exceeded the configured size limit. "
                        "Retry with streaming for full output."
                    ),
                    "data": {
                        "code": "response_too_large",
                        "max_bytes": max_bytes,
                        "actual_bytes": actual_bytes,
                    },
                },
            }
        )

    def _generate_success_response(
        self,
        request_id: Any,
        result: Any,
        *,
        headers: dict[str, str] | None = None,
    ) -> Response:
        response_headers = dict(headers or {})
        content = JSONRPCResponse(id=request_id, result=result).model_dump(
            mode="json", exclude_none=True
        )

        limited = limit_json_response_content(content, self._response_limit)
        if not limited.within_limit:
            return self._build_oversize_response(
                request_id=request_id,
                max_bytes=self._response_limit.max_content_length if self._response_limit else 0,
                actual_bytes=limited.original_size,
            )

        if limited.truncated:
            response_headers[TRUNCATED_RESPONSE_HEADER] = "true"

        return JSONResponse(content=limited.content, headers=response_headers)


class BaseA2ARESTFastAPIApplication(A2ARESTFastAPIApplication):
    """Enhanced A2A REST application with common gateway features."""

    def __init__(
        self,
        *args: Any,
        response_limit: ResponseLimitConfig | dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._response_limit = coerce_response_limit_config(response_limit)

    def _build_oversize_response(
        self,
        *,
        max_bytes: int,
        actual_bytes: int,
    ) -> Response:
        return JSONResponse(
            {
                "message": (
                    "Gateway response exceeded the configured size limit. "
                    "Retry with streaming for full output."
                ),
                "code": "response_too_large",
                "max_bytes": max_bytes,
                "actual_bytes": actual_bytes,
            },
            status_code=502,
        )

    def _generate_success_response(
        self,
        content: Any,
        *,
        headers: dict[str, str] | None = None,
    ) -> Response:
        response_headers = dict(headers or {})
        limited = limit_json_response_content(content, self._response_limit)
        if not limited.within_limit:
            return self._build_oversize_response(
                max_bytes=self._response_limit.max_content_length if self._response_limit else 0,
                actual_bytes=limited.original_size,
            )

        if limited.truncated:
            response_headers[TRUNCATED_RESPONSE_HEADER] = "true"

        return JSONResponse(content=limited.content, headers=response_headers)
