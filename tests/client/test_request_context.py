import pytest
from a2a.client.middleware import ClientCallContext
from a2a_adapter_core.client.request_context import HeaderInterceptor, build_call_context


@pytest.mark.asyncio
async def test_header_interceptor_injects_default_headers():
    interceptor = HeaderInterceptor(default_headers={"X-Test": "Value"})
    payload = {"some": "data"}
    http_kwargs = {"headers": {"Existing": "Head"}}

    new_payload, new_kwargs = await interceptor.intercept(
        method_name="test",
        request_payload=payload,
        http_kwargs=http_kwargs,
        agent_card=None,
        context=None,
    )

    assert new_kwargs["headers"]["X-Test"] == "Value"
    assert new_kwargs["headers"]["Existing"] == "Head"
    assert new_payload == payload


@pytest.mark.asyncio
async def test_header_interceptor_injects_dynamic_headers_from_context():
    interceptor = HeaderInterceptor(default_headers={"Static": "Old"})
    payload = {}
    http_kwargs = {}
    context = ClientCallContext(state={"headers": {"Dynamic": "New", "Static": "Override"}})

    _, new_kwargs = await interceptor.intercept(
        method_name="test",
        request_payload=payload,
        http_kwargs=http_kwargs,
        agent_card=None,
        context=context,
    )

    assert new_kwargs["headers"]["Static"] == "Override"
    assert new_kwargs["headers"]["Dynamic"] == "New"


def test_build_call_context_with_bearer_and_extra():
    context = build_call_context(
        bearer_token="secret-token", extra_headers={"X-Custom": "CustomValue"}
    )

    assert context is not None
    assert context.state["headers"]["Authorization"] == "Bearer secret-token"
    assert context.state["headers"]["X-Custom"] == "CustomValue"
