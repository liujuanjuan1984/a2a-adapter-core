import pytest
from a2a_adapter_core.server.response_limits import (
    ResponseLimitConfig,
    limit_json_response_content,
    DEFAULT_TRUNCATED_TEXT_SUFFIX,
)

LONG_TEXT = "adapter-output-" * 256
RESPONSE_LIMIT = 320


def test_limit_json_response_content_no_config():
    content = {"text": LONG_TEXT}
    result = limit_json_response_content(content, None)
    assert result.within_limit is True
    assert result.truncated is False
    assert result.content == content


def test_limit_json_response_content_within_limit():
    content = {"text": "short"}
    config = ResponseLimitConfig(max_content_length=RESPONSE_LIMIT)
    result = limit_json_response_content(content, config)
    assert result.within_limit is True
    assert result.truncated is False
    assert result.content == content


def test_limit_json_response_content_truncates_text():
    content = {"text": LONG_TEXT}
    suffix = " [truncated]"
    config = ResponseLimitConfig(
        max_content_length=RESPONSE_LIMIT,
        oversize_strategy="truncate_text",
        truncated_text_suffix=suffix,
    )
    result = limit_json_response_content(content, config)

    assert result.within_limit is True
    assert result.truncated is True
    assert result.rendered_size <= RESPONSE_LIMIT
    assert result.content["text"].endswith(suffix)


def test_limit_json_response_content_error_strategy():
    content = {"text": LONG_TEXT}
    config = ResponseLimitConfig(max_content_length=RESPONSE_LIMIT, oversize_strategy="error")
    result = limit_json_response_content(content, config)

    assert result.within_limit is False
    assert result.truncated is False
    # Content remains original when strategy is error but limit exceeded
    assert result.content == content


def test_limit_json_response_content_nested_truncation():
    # Increase RESPONSE_LIMIT slightly to ensure suffix fits
    local_limit = 500
    content = {"items": [{"text": LONG_TEXT}, {"markdown": LONG_TEXT}], "other": "constant"}
    config = ResponseLimitConfig(max_content_length=local_limit)
    result = limit_json_response_content(content, config)

    assert result.within_limit is True
    assert result.truncated is True
    assert result.content["other"] == "constant"
    # One of the fields should be truncated (it picks the largest one to truncate first)
    text1 = result.content["items"][0]["text"]
    text2 = result.content["items"][1]["markdown"]
    assert text1.endswith(DEFAULT_TRUNCATED_TEXT_SUFFIX) or text2.endswith(
        DEFAULT_TRUNCATED_TEXT_SUFFIX
    )


def test_limit_json_response_content_binary_search_precision():
    # Use a very tight limit to test the binary search boundary
    text = "a" * 100
    # Limit that forces truncation but allows some text
    config = ResponseLimitConfig(max_content_length=50, truncated_text_suffix="...")
    result = limit_json_response_content({"text": text}, config)

    assert result.within_limit is True
    assert result.truncated is True
    # The result should be as close to 50 as possible without exceeding it
    assert result.rendered_size <= 50
    assert len(result.content["text"]) > 3  # Should have more than just suffix
