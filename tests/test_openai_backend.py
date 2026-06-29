"""Tests for OpenAIBackend.

Mocks the ``openai`` SDK via the ``fake_openai`` fixture so tests run
without network or credentials.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from contemplative_agent.core.llm import BackendResult

from tests._fakes import OpenAIChoice, OpenAIMessage, OpenAIResponse


def test_generate_returns_backend_result(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key", model="gpt-5")
    result = backend.generate("hello", "system", 256, None)

    assert isinstance(result, BackendResult)
    assert result.text == "hello"
    call = backend._client.chat.completions.calls[0]
    assert call["model"] == "gpt-5"
    assert call["max_tokens"] == 256
    assert call["messages"][0] == {"role": "system", "content": "system"}
    assert call["messages"][1] == {"role": "user", "content": "hello"}
    assert "response_format" not in call


def test_generate_maps_token_usage(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key")
    result = backend.generate("hello", "system", 256, None)

    # The fake reports prompt_tokens=13, completion_tokens=9, cached_tokens=4.
    assert result.eval_count == 9
    assert result.prompt_tokens == 13
    assert result.cached_tokens == 4
    assert result.thinking is None


def test_finish_reason_passthrough(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key")
    backend._get_client().chat.completions.finish_reason = "length"

    result = backend.generate("hello", "system", 256, None)

    # OpenAI already speaks "length"; it feeds the gate without translation.
    assert result.finish_reason == "length"


def test_usage_absent_leaves_token_fields_none(fake_openai):
    """A ChatCompletion with no usage object must not raise — fields go None."""
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key")
    backend._get_client().chat.completions.create = MagicMock(
        return_value=OpenAIResponse(
            choices=[
                OpenAIChoice(message=OpenAIMessage(content="hi"), finish_reason="stop")
            ],
            usage=None,
        )
    )

    result = backend.generate("p", "s", 10, None)

    assert result.text == "hi"
    assert result.eval_count is None
    assert result.prompt_tokens is None
    assert result.cached_tokens is None


def test_context_window_default_and_gpt5(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    assert OpenAIBackend(api_key="k", model="gpt-5").context_window == 400_000
    # Dated gpt-5 variants resolve via prefix match.
    assert (
        OpenAIBackend(api_key="k", model="gpt-5-2025-08-07").context_window == 400_000
    )
    # The whole GPT-5 family (mini / nano) shares the 400K window, so the
    # gpt-5 prefix intentionally covers them — not a collision.
    assert OpenAIBackend(api_key="k", model="gpt-5-mini").context_window == 400_000
    # GPT-4.1 family carries a ~1M window; an override must not fall to the
    # 128K default or the budget guard would skip valid long-context calls.
    assert OpenAIBackend(api_key="k", model="gpt-4.1").context_window == 1_000_000
    assert OpenAIBackend(api_key="k", model="gpt-4.1-mini").context_window == 1_000_000
    # Unrecognized model falls to the conservative 128K default.
    assert OpenAIBackend(api_key="k", model="gpt-4o").context_window == 128_000


def test_temperature_forwarded(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key")
    # OpenAI accepts [0.0, 2.0], so 1.3 passes through unclamped.
    backend.generate("hello", "system", 256, None, temperature=1.3)

    assert backend._client.chat.completions.calls[0]["temperature"] == 1.3


def test_think_kwarg_accepted_and_ignored(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = OpenAIBackend(api_key="fake-key")
    result = backend.generate("hello", "system", 256, None, think=True)

    assert result.thinking is None
    assert "think" not in backend._client.chat.completions.calls[0]


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
    assert result.text == "hello"
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
