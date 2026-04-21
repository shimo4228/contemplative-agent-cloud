"""Shared fixtures for contemplative-agent-cloud tests.

The two cloud SDKs (``anthropic``, ``openai``) are installed as real
dependencies, but in tests we replace them with in-memory module stubs
so request construction can be inspected without network or credentials.
"""

from __future__ import annotations

import sys
import types
from typing import Iterator

import pytest


class _StubError(Exception):
    """Generic exception used for every SDK-specific error class."""


def _install_stub_sdk(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    client_attr: str,
    client_cls: type,
) -> types.ModuleType:
    module = types.ModuleType(module_name)
    setattr(module, client_attr, client_cls)
    module.APIConnectionError = _StubError
    module.APITimeoutError = _StubError
    module.RateLimitError = _StubError
    module.InternalServerError = _StubError
    monkeypatch.setitem(sys.modules, module_name, module)
    return module


@pytest.fixture
def RateLimitError() -> type:
    """The error class retry tests raise to simulate transient failures."""
    return _StubError


@pytest.fixture
def fake_anthropic(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.ModuleType]:
    from tests._fakes import FakeAnthropicClient

    module = _install_stub_sdk(
        monkeypatch, "anthropic", "Anthropic", FakeAnthropicClient
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    yield module


@pytest.fixture
def fake_openai(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.ModuleType]:
    from tests._fakes import FakeOpenAIClient

    module = _install_stub_sdk(
        monkeypatch, "openai", "OpenAI", FakeOpenAIClient
    )
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    yield module


@pytest.fixture
def fake_sdks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install both SDK stubs. Useful for CLI tests that touch both."""
    from tests._fakes import FakeAnthropicClient, FakeOpenAIClient

    _install_stub_sdk(monkeypatch, "anthropic", "Anthropic", FakeAnthropicClient)
    _install_stub_sdk(monkeypatch, "openai", "OpenAI", FakeOpenAIClient)
