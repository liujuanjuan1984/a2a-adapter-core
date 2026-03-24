"""Helpers for limiting oversized non-stream JSON responses."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any, Literal, cast

DEFAULT_RESPONSE_MAX_CONTENT_LENGTH = 10 * 1024 * 1024
DEFAULT_OVERSIZE_RESPONSE_STRATEGY = "truncate_text"
DEFAULT_TRUNCATED_TEXT_SUFFIX = (
    "\n\n[Response truncated by a2a adapter. Retry with streaming for full output.]"
)
TRUNCATED_RESPONSE_HEADER = "X-A2A-Response-Truncated"

OversizeResponseStrategy = Literal["truncate_text", "error"]
_TRUNCATABLE_TEXT_KEYS = frozenset({"text", "markdown"})


@dataclass(frozen=True)
class ResponseLimitConfig:
    max_content_length: int
    oversize_strategy: OversizeResponseStrategy = "truncate_text"
    truncated_text_suffix: str = DEFAULT_TRUNCATED_TEXT_SUFFIX


@dataclass(frozen=True)
class ResponseLimitResult:
    content: Any
    rendered_size: int
    original_size: int
    within_limit: bool
    truncated: bool


@dataclass
class _TextRef:
    container: dict[str, Any]
    key: str

    def get(self) -> str:
        value = self.container.get(self.key)
        return value if isinstance(value, str) else ""

    def set(self, value: str) -> None:
        self.container[self.key] = value


def coerce_response_limit_config(
    value: ResponseLimitConfig | dict[str, Any] | None,
) -> ResponseLimitConfig | None:
    if value is None:
        return None
    if isinstance(value, ResponseLimitConfig):
        return value
    max_content_length = int(value.get("max_content_length") or 0)
    if max_content_length <= 0:
        return None
    oversize_strategy = (
        str(value.get("oversize_strategy") or DEFAULT_OVERSIZE_RESPONSE_STRATEGY).strip().lower()
    )
    if oversize_strategy not in {"truncate_text", "error"}:
        raise RuntimeError("response limit oversize_strategy must be one of: error, truncate_text")
    suffix = value.get("truncated_text_suffix")
    if suffix is None:
        suffix = DEFAULT_TRUNCATED_TEXT_SUFFIX
    if not isinstance(suffix, str):
        raise RuntimeError("response limit truncated_text_suffix must be a string")
    return ResponseLimitConfig(
        max_content_length=max_content_length,
        oversize_strategy=cast(OversizeResponseStrategy, oversize_strategy),
        truncated_text_suffix=suffix,
    )


def render_json_bytes(content: Any) -> bytes:
    return json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def limit_json_response_content(
    content: Any,
    config: ResponseLimitConfig | dict[str, Any] | None,
) -> ResponseLimitResult:
    limit_config = coerce_response_limit_config(config)
    payload = render_json_bytes(content)
    original_size = len(payload)
    if limit_config is None or original_size <= limit_config.max_content_length:
        return ResponseLimitResult(
            content=content,
            rendered_size=original_size,
            original_size=original_size,
            within_limit=True,
            truncated=False,
        )
    if limit_config.oversize_strategy != "truncate_text":
        return ResponseLimitResult(
            content=content,
            rendered_size=original_size,
            original_size=original_size,
            within_limit=False,
            truncated=False,
        )

    truncated_content = _truncate_text_fields(
        content,
        max_content_length=limit_config.max_content_length,
        suffix=limit_config.truncated_text_suffix,
    )
    if truncated_content is None:
        return ResponseLimitResult(
            content=content,
            rendered_size=original_size,
            original_size=original_size,
            within_limit=False,
            truncated=False,
        )
    rendered_size = len(render_json_bytes(truncated_content))
    return ResponseLimitResult(
        content=truncated_content,
        rendered_size=rendered_size,
        original_size=original_size,
        within_limit=rendered_size <= limit_config.max_content_length,
        truncated=True,
    )


def _truncate_text_fields(content: Any, *, max_content_length: int, suffix: str) -> Any | None:
    candidate = deepcopy(content)
    refs = _collect_text_refs(candidate)
    if not refs:
        return None

    while refs:
        rendered_size = len(render_json_bytes(candidate))
        if rendered_size <= max_content_length:
            return candidate
        ref = max(refs, key=lambda item: len(item.get().encode("utf-8")))
        original = ref.get()
        if not original:
            refs.remove(ref)
            continue
        best = _find_best_truncation(
            candidate,
            ref,
            original,
            max_content_length=max_content_length,
            suffix=suffix,
        )
        if best is None:
            ref.set("")
            if ref.get() == original:
                refs.remove(ref)
                continue
        else:
            ref.set(best)

    rendered_size = len(render_json_bytes(candidate))
    if rendered_size <= max_content_length:
        return candidate
    return None


def _collect_text_refs(node: Any) -> list[_TextRef]:
    refs: list[_TextRef] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _TRUNCATABLE_TEXT_KEYS and isinstance(value, str):
                refs.append(_TextRef(node, key))
                continue
            refs.extend(_collect_text_refs(value))
    elif isinstance(node, list):
        for item in node:
            refs.extend(_collect_text_refs(item))
    return refs


def _find_best_truncation(
    content: Any,
    ref: _TextRef,
    original: str,
    *,
    max_content_length: int,
    suffix: str,
) -> str | None:
    best: str | None = None
    low = 0
    high = len(original)

    while low <= high:
        keep = (low + high) // 2
        candidate = _build_truncated_text(original, keep, suffix=suffix)
        ref.set(candidate)
        rendered_size = len(render_json_bytes(content))
        if rendered_size <= max_content_length:
            best = candidate
            low = keep + 1
        else:
            high = keep - 1

    ref.set(original)
    if best is not None:
        return best

    ref.set("")
    if len(render_json_bytes(content)) <= max_content_length:
        ref.set(original)
        return ""
    ref.set(original)
    return None


def _build_truncated_text(original: str, keep: int, *, suffix: str) -> str:
    if keep >= len(original):
        return original
    truncated = original[:keep].rstrip()
    if not suffix:
        return truncated
    return f"{truncated}{suffix}" if truncated else suffix


__all__ = [
    "DEFAULT_OVERSIZE_RESPONSE_STRATEGY",
    "DEFAULT_RESPONSE_MAX_CONTENT_LENGTH",
    "DEFAULT_TRUNCATED_TEXT_SUFFIX",
    "ResponseLimitConfig",
    "ResponseLimitResult",
    "TRUNCATED_RESPONSE_HEADER",
    "coerce_response_limit_config",
    "limit_json_response_content",
    "render_json_bytes",
]
