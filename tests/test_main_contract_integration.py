"""Integration: cloud backends consumed by the main repo's generate() path.

Regression guard for the contract drift this package was fixed for — the
backends returned a bare ``str`` while main's ``_generate_via_backend`` did
``result.text`` / ``result.finish_reason`` / ``result.eval_count`` on it.
The AttributeError was swallowed into a circuit failure, so every cloud
generation silently returned ``None``.

These tests run the *real* backend through ``contemplative_agent.core.llm``
with only the provider SDK stubbed (via the shared fake fixtures), so a future
return-type regression fails here instead of disappearing into the breaker.
"""

from __future__ import annotations

import pytest

from contemplative_agent.core import llm


@pytest.fixture(autouse=True)
def _reset_llm_config():
    """Drop any injected backend so configure() in one test never leaks."""
    yield
    llm.reset_llm_config()


def test_anthropic_routes_through_main_generate(fake_anthropic):
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    llm.configure(backend=AnthropicBackend(api_key="k"))
    out = llm.generate("ping", system="You are a test. Reply pong.")

    # Sanitized passthrough of the fake's response_text — proves main read
    # result.text (and the usage/finish_reason fields) without AttributeError.
    assert out == "hello"
    assert not llm._circuit.is_open


def test_openai_routes_through_main_generate(fake_openai):
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    llm.configure(backend=OpenAIBackend(api_key="k"))
    out = llm.generate("ping", system="You are a test. Reply pong.")

    assert out == "hello"
    assert not llm._circuit.is_open


def test_truncation_gate_drops_max_tokens_generation(fake_anthropic):
    """Anthropic max_tokens -> "length" must drive main's drop_truncated gate.

    With drop_truncated=True, a length-truncated generation returns None *and*
    records a circuit success (deliberate drop, not a fault). This only works
    because the backend translates stop_reason="max_tokens" to the "length"
    vocabulary the gate keys on.
    """
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = AnthropicBackend(api_key="k")
    llm.configure(backend=backend)
    backend._get_client().messages.stop_reason = "max_tokens"

    out = llm.generate(
        "ping", system="You are a test. Reply pong.", drop_truncated=True
    )

    assert out is None
    # Dropped truncation is scored as a success, not a failure.
    assert not llm._circuit.is_open
