"""Tests for OpenAIBackend.

Mocks the ``openai`` SDK via the ``fake_openai`` fixture so tests run
without network or credentials.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests._fakes import OpenAIResponse


def test_generate_returns_text(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key", model="gpt-5")
    result = backend.generate("hello", "system", 256, None)

    assert result == "hello"
    call = backend._client.chat.completions.calls[0]
    assert call["model"] == "gpt-5"
    assert call["max_tokens"] == 256
    assert call["messages"][0] == {"role": "system", "content": "system"}
    assert call["messages"][1] == {"role": "user", "content": "hello"}
    assert "response_format" not in call


def test_generate_uses_json_schema_response_format(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    backend = OpenAIBackend(api_key="fake-key")
    backend.generate("q", "s", 100, schema)

    call = backend._client.chat.completions.calls[0]
    assert call["response_format"]["type"] == "json_schema"
    assert call["response_format"]["json_schema"]["schema"] == schema
    assert call["response_format"]["json_schema"]["strict"] is True


def test_missing_api_key_raises(fake_openai, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        backend.generate("p", "s", 10, None)


def test_retries_on_rate_limit(fake_openai, RateLimitError, monkeypatch):
    monkeypatch.setattr(
        "contemplative_agent_cloud.backends._base.RETRY_BASE_DELAY_SECONDS", 0.0
    )

    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key", max_retries=2)
    client = backend._get_client()
    client.chat.completions.raise_exc = RateLimitError("slow down")

    result = backend.generate("p", "s", 10, None)
    assert result == "hello"
    assert len(client.chat.completions.calls) == 2


def test_non_retryable_error_returns_none(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key")
    client = backend._get_client()
    client.chat.completions.raise_exc = ValueError("bad request")

    result = backend.generate("p", "s", 10, None)
    assert result is None


def test_empty_choices_returns_none(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key")
    client = backend._get_client()
    client.chat.completions.create = MagicMock(return_value=OpenAIResponse(choices=[]))

    result = backend.generate("p", "s", 10, None)
    assert result is None


def test_protocol_conformance(fake_openai):
    from contemplative_agent.core.llm import LLMBackend

    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    assert isinstance(OpenAIBackend(api_key="fake-key"), LLMBackend)
