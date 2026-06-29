"""Tests for AnthropicBackend.

Mocks the ``anthropic`` SDK via the ``fake_anthropic`` fixture so tests
run without network or API credentials.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from contemplative_agent.core.llm import BackendResult

from tests._fakes import AnthropicBlock, AnthropicResponse


def test_generate_returns_backend_result(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key", model="claude-opus-4-7")
    result = backend.generate("hello", "system", 256, None)

    assert isinstance(result, BackendResult)
    assert result.text == "hello"
    client = backend._client
    assert len(client.messages.calls) == 1
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-7"
    assert call["system"] == "system"
    assert call["max_tokens"] == 256
    assert call["messages"] == [{"role": "user", "content": "hello"}]


def test_generate_maps_token_usage(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    result = backend.generate("hello", "system", 256, None)

    # The fake reports input_tokens=11, output_tokens=7, no cache fields.
    assert result.eval_count == 7
    assert result.prompt_tokens == 11
    assert result.cached_tokens is None
    assert result.thinking is None


def test_finish_reason_maps_max_tokens_to_length(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    backend._get_client().messages.stop_reason = "max_tokens"

    result = backend.generate("hello", "system", 256, None)

    # Anthropic's "max_tokens" must translate to the core's "length" so the
    # drop_truncated gate fires.
    assert result.finish_reason == "length"


def test_usage_absent_leaves_token_fields_none(fake_anthropic):
    """An SDK response with no usage object must not raise — fields go None."""
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    backend._get_client().messages.create = MagicMock(
        return_value=AnthropicResponse(
            content=[AnthropicBlock(text="hi")], stop_reason="end_turn", usage=None
        )
    )

    result = backend.generate("p", "s", 10, None)

    assert result.text == "hi"
    assert result.eval_count is None
    assert result.prompt_tokens is None
    assert result.cached_tokens is None


def test_finish_reason_passthrough_for_end_turn(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    result = backend.generate("hello", "system", 256, None)

    assert result.finish_reason == "end_turn"


def test_context_window_default(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key", model="claude-opus-4-7")
    assert backend.context_window == 200_000
    # Dated id variants resolve via prefix match, not a fall to a wrong default.
    assert (
        AnthropicBackend(api_key="k", model="claude-opus-4-7-20250101").context_window
        == 200_000
    )


def test_temperature_clamped_to_anthropic_range(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    # Core may pass COMMENT_TEMPERATURE=1.3; Anthropic rejects >1.0.
    backend.generate("hello", "system", 256, None, temperature=1.3)

    call = backend._client.messages.calls[0]
    assert call["temperature"] == 1.0


def test_temperature_forwarded_when_in_range(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    backend.generate("hello", "system", 256, None, temperature=0.0)

    assert backend._client.messages.calls[0]["temperature"] == 0.0


def test_think_kwarg_accepted_and_ignored(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    # The core always passes think=; the backend must accept it without raising.
    result = backend.generate("hello", "system", 256, None, think=True)

    assert result.thinking is None
    assert "think" not in backend._client.messages.calls[0]


def test_generate_injects_json_schema_instruction(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    backend = AnthropicBackend(api_key="fake-key")
    backend.generate("question", "sys", 100, schema)

    call = backend._client.messages.calls[0]
    content = call["messages"][0]["content"]
    assert "question" in content
    assert json.dumps(schema) in content
    assert "Output only the JSON" in content


def test_missing_api_key_raises(fake_anthropic, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend()
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        backend.generate("p", "s", 10, None)


def test_retries_on_rate_limit(fake_anthropic, RateLimitError, monkeypatch):
    monkeypatch.setattr(
        "contemplative_agent_cloud.backends._base.RETRY_BASE_DELAY_SECONDS", 0.0
    )

    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key", max_retries=2)
    client = backend._get_client()
    client.messages.raise_exc = RateLimitError("slow down")

    result = backend.generate("p", "s", 10, None)
    assert result.text == "hello"
    assert len(client.messages.calls) == 2


def test_non_retryable_error_returns_none(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    client = backend._get_client()
    client.messages.raise_exc = ValueError("bad request")

    result = backend.generate("p", "s", 10, None)
    assert result is None


def test_empty_content_returns_none(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key")
    client = backend._get_client()
    client.messages.create = MagicMock(return_value=AnthropicResponse(content=[]))

    result = backend.generate("p", "s", 10, None)
    assert result is None


def test_protocol_conformance(fake_anthropic):
    """AnthropicBackend satisfies the LLMBackend Protocol exported by main repo."""
    from contemplative_agent.core.llm import LLMBackend

    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    assert isinstance(AnthropicBackend(api_key="fake-key"), LLMBackend)
