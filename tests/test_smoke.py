from a2a_adapter_core.common.contracts.extensions import SESSION_BINDING_EXTENSION_URI
from a2a_adapter_core.server.response_limits import ResponseLimitConfig, limit_json_response_content


def test_contracts_import():
    assert SESSION_BINDING_EXTENSION_URI == "urn:a2a:session-binding/v1"


def test_response_limits_truncation():
    config = ResponseLimitConfig(max_content_length=50)
    content = {"text": "This is a very long text that should be truncated to fit within the limit."}
    result = limit_json_response_content(content, config)
    assert result.truncated is True
    assert len(str(result.content)) < len(str(content))
