"""CLI wrapper that injects a managed-LLM backend before delegating to
the main ``contemplative-agent`` CLI.

Reads configuration in this precedence (last one wins):

1. Shell environment (``CONTEMPLATIVE_CLOUD_PROVIDER``,
   ``CONTEMPLATIVE_CLOUD_MODEL``, ``ANTHROPIC_API_KEY``,
   ``OPENAI_API_KEY``)
2. ``$MOLTBOOK_HOME/cloud.env`` if the file exists (simple
   ``KEY=VALUE`` per line; overrides shell env for those keys)

When ``CONTEMPLATIVE_CLOUD_PROVIDER`` resolves to empty after both
sources, **no backend is injected** and the call simply forwards to
the main CLI as-is. That path is used for the dialogue orchestrator
(which never calls an LLM directly — each peer reads its own
``MOLTBOOK_HOME/cloud.env``) and for any subcommand the user wants to
run against local Ollama alongside the add-on being installed.

Peer subprocesses spawned by ``contemplative-agent dialogue`` are
re-routed through this same wrapper by setting
``CONTEMPLATIVE_DIALOGUE_PEER_MODULE``; the main repository's
``_spawn_dialogue_peer`` respects that env var.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from contemplative_agent.core.llm import LLMBackend, configure

from contemplative_agent_cloud.backends.anthropic import AnthropicBackend
from contemplative_agent_cloud.backends.openai import OpenAIBackend


_BACKENDS = {"anthropic": AnthropicBackend, "openai": OpenAIBackend}

_CLOUD_ENV_FILENAME = "cloud.env"


def _load_home_cloud_env() -> None:
    """Source ``$MOLTBOOK_HOME/cloud.env`` into ``os.environ`` if present.

    File format: one ``KEY=VALUE`` per line. Surrounding whitespace and
    matching pairs of single/double quotes around the value are
    stripped. Lines that are blank or start with ``#`` are ignored.
    Missing file is silently ignored — callers may set the same vars
    via the shell.
    """
    home = os.environ.get("MOLTBOOK_HOME")
    if not home:
        return
    path = Path(home) / _CLOUD_ENV_FILENAME
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (len(value) >= 2) and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            os.environ[key] = value


def _build_backend_or_none() -> Optional[LLMBackend]:
    """Build a backend from env vars, or return None if provider unset.

    Returns ``None`` when ``CONTEMPLATIVE_CLOUD_PROVIDER`` is empty —
    the caller should then skip ``configure(backend=...)`` and let the
    main CLI run with whatever default is configured (typically local
    Ollama). Unknown providers still raise ``SystemExit`` so typos
    surface immediately.
    """
    provider = os.environ.get("CONTEMPLATIVE_CLOUD_PROVIDER", "").strip().lower()
    if not provider:
        return None

    backend_cls = _BACKENDS.get(provider)
    if backend_cls is None:
        raise SystemExit(
            f"Unknown CONTEMPLATIVE_CLOUD_PROVIDER={provider!r}. "
            f"Supported: {sorted(_BACKENDS)}."
        )

    model: Optional[str] = os.environ.get("CONTEMPLATIVE_CLOUD_MODEL")
    return backend_cls(model=model) if model else backend_cls()


def main(argv: Optional[list] = None) -> None:
    # Per-home config may carry a different provider + model than the
    # shell env. Load it before reading any env-driven settings.
    _load_home_cloud_env()

    # Peer subprocesses spawned by the main CLI's dialogue handler
    # should route through this wrapper so the same per-home
    # configuration path runs inside each peer.
    os.environ["CONTEMPLATIVE_DIALOGUE_PEER_MODULE"] = "contemplative_agent_cloud.cli"

    backend = _build_backend_or_none()
    if backend is not None:
        configure(backend=backend)

    # Delegate everything else to the main CLI, which picks up the
    # backend via the module-level state in core/llm.py.
    from contemplative_agent.cli import main as _main

    if argv is not None:
        sys.argv = ["contemplative-agent", *argv]
    _main()


if __name__ == "__main__":
    main()
