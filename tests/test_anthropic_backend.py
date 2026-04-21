"""Tests for AnthropicBackend.

Mocks the ``anthropic`` SDK via the ``fake_anthropic`` fixture so tests
run without network or API credentials.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from tests._fakes import AnthropicResponse


def test_generate_returns_text(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="fake-key", model="claude-opus-4-7")
    result = backend.generate("hello", "system", 256, None)

    assert result == "hello"
    client = backend._client
    assert len(client.messages.calls) == 1
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-7"
    assert call["system"] == "system"
    assert call["max_tokens"] == 256
    assert call["messages"] == [{"role": "user", "content": "hello"}]


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
    assert result == "hello"
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
