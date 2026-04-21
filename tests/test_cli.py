"""Tests for the contemplative-agent-cloud CLI wrapper."""

from __future__ import annotations

import sys
import types

import pytest


def test_build_backend_or_none_anthropic(fake_sdks, monkeypatch):
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    from contemplative_agent_cloud.cli import _build_backend_or_none
    from contemplative_agent_cloud.backends.anthropic import AnthropicBackend

    backend = _build_backend_or_none()
    assert isinstance(backend, AnthropicBackend)


def test_build_backend_or_none_openai(fake_sdks, monkeypatch):
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "k")

    from contemplative_agent_cloud.cli import _build_backend_or_none
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    backend = _build_backend_or_none()
    assert isinstance(backend, OpenAIBackend)


def test_build_backend_or_none_model_override(fake_sdks, monkeypatch):
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_PROVIDER", "anthropic")
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    from contemplative_agent_cloud.cli import _build_backend_or_none

    backend = _build_backend_or_none()
    assert backend.model == "claude-haiku-4-5"


def test_build_backend_or_none_missing_provider_returns_none(monkeypatch):
    monkeypatch.delenv("CONTEMPLATIVE_CLOUD_PROVIDER", raising=False)
    from contemplative_agent_cloud.cli import _build_backend_or_none

    assert _build_backend_or_none() is None


def test_build_backend_or_none_unknown_provider_exits(monkeypatch):
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_PROVIDER", "cohere")
    from contemplative_agent_cloud.cli import _build_backend_or_none

    with pytest.raises(SystemExit, match="Unknown"):
        _build_backend_or_none()


def test_load_home_cloud_env_applies_keys(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "cloud.env").write_text(
        'CONTEMPLATIVE_CLOUD_PROVIDER=openai\n'
        'CONTEMPLATIVE_CLOUD_MODEL="gpt-4o"\n'
        '# comment line\n'
        '\n'
        "IGNORED_NO_EQUALS\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MOLTBOOK_HOME", str(home))
    monkeypatch.delenv("CONTEMPLATIVE_CLOUD_PROVIDER", raising=False)
    monkeypatch.delenv("CONTEMPLATIVE_CLOUD_MODEL", raising=False)

    from contemplative_agent_cloud.cli import _load_home_cloud_env

    _load_home_cloud_env()

    import os as _os
    assert _os.environ["CONTEMPLATIVE_CLOUD_PROVIDER"] == "openai"
    assert _os.environ["CONTEMPLATIVE_CLOUD_MODEL"] == "gpt-4o"


def test_load_home_cloud_env_missing_home_noop(monkeypatch):
    monkeypatch.delenv("MOLTBOOK_HOME", raising=False)
    from contemplative_agent_cloud.cli import _load_home_cloud_env

    # Should not raise; should not mutate anything.
    _load_home_cloud_env()


def test_load_home_cloud_env_missing_file_noop(monkeypatch, tmp_path):
    home = tmp_path / "empty"
    home.mkdir()
    monkeypatch.setenv("MOLTBOOK_HOME", str(home))

    from contemplative_agent_cloud.cli import _load_home_cloud_env

    _load_home_cloud_env()  # No cloud.env present — silent


def test_load_home_cloud_env_overrides_shell_env(monkeypatch, tmp_path):
    """cloud.env takes precedence over inherited shell env."""
    home = tmp_path / "h"
    home.mkdir()
    (home / "cloud.env").write_text(
        "CONTEMPLATIVE_CLOUD_PROVIDER=openai\n", encoding="utf-8"
    )
    monkeypatch.setenv("MOLTBOOK_HOME", str(home))
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_PROVIDER", "anthropic")

    from contemplative_agent_cloud.cli import _load_home_cloud_env

    _load_home_cloud_env()

    import os as _os
    assert _os.environ["CONTEMPLATIVE_CLOUD_PROVIDER"] == "openai"


def test_main_sets_peer_module_env(fake_sdks, monkeypatch):
    """main() must set CONTEMPLATIVE_DIALOGUE_PEER_MODULE so the main
    CLI re-enters this wrapper when spawning dialogue peers."""
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.delenv("CONTEMPLATIVE_DIALOGUE_PEER_MODULE", raising=False)

    fake_cli_module = types.ModuleType("contemplative_agent.cli")
    fake_cli_module.main = lambda: None
    monkeypatch.setitem(sys.modules, "contemplative_agent.cli", fake_cli_module)

    from contemplative_agent_cloud.cli import main

    main(argv=["distill"])

    import os as _os
    assert _os.environ["CONTEMPLATIVE_DIALOGUE_PEER_MODULE"] == "contemplative_agent_cloud.cli"

    from contemplative_agent.core import llm as _llm_module
    _llm_module.reset_llm_config()


def test_main_injects_backend_when_provider_set(fake_sdks, monkeypatch):
    monkeypatch.setenv("CONTEMPLATIVE_CLOUD_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    called = {"hit": False}

    def fake_main():
        called["hit"] = True

    fake_cli_module = types.ModuleType("contemplative_agent.cli")
    fake_cli_module.main = fake_main
    monkeypatch.setitem(sys.modules, "contemplative_agent.cli", fake_cli_module)

    captured: dict = {}

    from contemplative_agent.core import llm as _llm_module

    orig_configure = _llm_module.configure

    def fake_configure(**kwargs):
        captured.update(kwargs)
        return orig_configure(**kwargs)

    monkeypatch.setattr(_llm_module, "configure", fake_configure)
    monkeypatch.setattr(
        "contemplative_agent_cloud.cli.configure", fake_configure
    )

    from contemplative_agent_cloud.cli import main

    main(argv=["distill", "--days", "1"])

    assert called["hit"]
    assert "backend" in captured
    _llm_module.reset_llm_config()


def test_main_skips_backend_when_provider_absent(fake_sdks, monkeypatch):
    """Orchestrator path: no provider configured, no backend injected."""
    monkeypatch.delenv("CONTEMPLATIVE_CLOUD_PROVIDER", raising=False)
    monkeypatch.delenv("MOLTBOOK_HOME", raising=False)

    called = {"hit": False}

    def fake_main():
        called["hit"] = True

    fake_cli_module = types.ModuleType("contemplative_agent.cli")
    fake_cli_module.main = fake_main
    monkeypatch.setitem(sys.modules, "contemplative_agent.cli", fake_cli_module)

    captured: dict = {}

    def fake_configure(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "contemplative_agent_cloud.cli.configure", fake_configure
    )

    from contemplative_agent_cloud.cli import main

    main(argv=["dialogue", "/tmp/a", "/tmp/b", "--seed", "x", "--turns", "1"])

    assert called["hit"]
    assert captured == {}  # backend was not injected

    from contemplative_agent.core import llm as _llm_module
    _llm_module.reset_llm_config()


def test_main_home_env_drives_provider(fake_sdks, monkeypatch, tmp_path):
    """End-to-end per-home config: $MOLTBOOK_HOME/cloud.env chooses provider."""
    home = tmp_path / "peer-a"
    home.mkdir()
    (home / "cloud.env").write_text(
        "CONTEMPLATIVE_CLOUD_PROVIDER=openai\n"
        "CONTEMPLATIVE_CLOUD_MODEL=gpt-4o\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MOLTBOOK_HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.delenv("CONTEMPLATIVE_CLOUD_PROVIDER", raising=False)
    monkeypatch.delenv("CONTEMPLATIVE_CLOUD_MODEL", raising=False)

    fake_cli_module = types.ModuleType("contemplative_agent.cli")
    fake_cli_module.main = lambda: None
    monkeypatch.setitem(sys.modules, "contemplative_agent.cli", fake_cli_module)

    captured: dict = {}

    def fake_configure(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "contemplative_agent_cloud.cli.configure", fake_configure
    )

    from contemplative_agent_cloud.cli import main
    from contemplative_agent_cloud.backends.openai import OpenAIBackend

    main(argv=["distill"])

    backend = captured.get("backend")
    assert isinstance(backend, OpenAIBackend)
    assert backend.model == "gpt-4o"

    from contemplative_agent.core import llm as _llm_module
    _llm_module.reset_llm_config()
