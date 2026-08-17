# contemplative-agent-cloud

Optional managed-LLM backends for
[contemplative-agent](https://github.com/shimo4228/contemplative-agent).
Installing this package routes generation calls in contemplative-agent
through **Anthropic Claude** or **OpenAI GPT** instead of local Ollama.
Embeddings continue to use local `nomic-embed-text`.

## When to use this

The main repository
([contemplative-agent](https://github.com/shimo4228/contemplative-agent))
is defined as a local-only autonomous agent running on a single Apple
Silicon Mac with Qwen3.5 9B via Ollama. Its headline properties —
"No cloud. No API keys in transit. Local Ollama only" — hold as long as
you stay with the default stack.

This add-on exists for research experiments that need a larger
generation model than 9B — for example, comparing how distillation
behavior changes when swapping in Claude Opus or GPT-5 while keeping
everything else (embeddings, retrieval, memory schema, security
boundary) identical. The "distilling with larger model" direction from
the Laukkonen team correspondence (2026-04-20) is the motivating use
case.

## What changes when this is installed

| | Default (main repo only) | With `contemplative-agent-cloud` |
|---|---|---|
| Generation | Local Ollama + Qwen3.5 9B | Anthropic Claude **or** OpenAI GPT |
| Embedding | Local Ollama + nomic-embed-text | **Unchanged** (still local) |
| Episode log, knowledge, identity | `$MOLTBOOK_HOME` (0600 perms) | **Unchanged** |
| Prompt-injection boundary | `wrap_untrusted_content()` | **Unchanged** |
| Output sanitization | `_sanitize_output()` | **Unchanged** |
| Circuit breaker | 5 failures → 120 s cooldown | **Unchanged** |
| Network surface | `moltbook.com` + `localhost` | **+ `api.anthropic.com` or `api.openai.com`** |

The main repository is **not modified** when you install this add-on.
Its code never learns about cloud APIs — this package injects a backend
implementation through an abstract
`contemplative_agent.core.llm.LLMBackend` Protocol. If this package is
not installed and no backend is explicitly configured, the main
repository continues to run exactly as before: local only, no cloud
traffic.

## Security posture

Installing this add-on **relaxes** the main repository's "No cloud. No
API keys in transit" property. When you run the cloud CLI:

- Your API key is loaded from `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
  and sent to the provider with every request.
- Prompt content — including episode-derived context that was wrapped
  with `<untrusted_content>` boundaries by the main repository — is
  transmitted to the provider over HTTPS and may be logged on their
  side according to their retention policies.
- Generation output comes back over HTTPS, passes through the same
  `_sanitize_output()` forbidden-pattern filter as local output, and is
  stored in your local `$MOLTBOOK_HOME` the same way as Ollama output.

Do not install this add-on in deployments where cloud-data-egress is
not acceptable (regulatory constraints, air-gapped research,
privacy-sensitive personal assistants). The main repository remains
the right choice there.

## Install

```bash
pip install contemplative-agent-cloud
# or, from source:
git clone https://github.com/shimo4228/contemplative-agent-cloud
cd contemplative-agent-cloud
pip install -e .
```

Installing this package pulls in `contemplative-agent>=2.0` as a
dependency automatically.

## Configure

```bash
# Choose a provider
export CONTEMPLATIVE_CLOUD_PROVIDER=anthropic   # or: openai

# Optional: override the default model
export CONTEMPLATIVE_CLOUD_MODEL=claude-opus-4-7
# Defaults: anthropic → claude-opus-4-7, openai → gpt-5

# Credentials
export ANTHROPIC_API_KEY=sk-ant-...
# or:
export OPENAI_API_KEY=sk-...
```

## Run

Any `contemplative-agent` subcommand works — simply swap the command
name from `contemplative-agent` to `contemplative-agent-cloud`:

```bash
contemplative-agent-cloud init
contemplative-agent-cloud distill --days 3
contemplative-agent-cloud insight --stage
contemplative-agent-cloud rules-distill --full
contemplative-agent-cloud amend-constitution
contemplative-agent-cloud run --session 60
contemplative-agent-cloud dialogue ~/dialogue/a ~/dialogue/b --seed "..." --turns 10
```

All generation inside those subcommands now routes through your
configured cloud provider. Ollama is still contacted for embeddings —
make sure `nomic-embed-text` is available on `localhost:11434`.

## Programmatic use

```python
from contemplative_agent.core.llm import configure
from contemplative_agent_cloud import AnthropicBackend

configure(backend=AnthropicBackend(
    api_key="sk-ant-...",
    model="claude-opus-4-7",
))

# From this point on, every `contemplative_agent.core.llm.generate()`
# call — no matter which subcommand or adapter triggered it — runs
# through Anthropic. Reset with `reset_llm_config()`.
```

## Supported providers

| Provider | Default model | Environment variable |
|---|---|---|
| Anthropic | `claude-opus-4-7` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-5` | `OPENAI_API_KEY` |

The `gpt-5` path has not been exercised against the live API: it may
reject `max_tokens` and require `max_completion_tokens`, and it may
reject a non-default `temperature`. Only `gpt-4o` and
`claude-sonnet-4-6` have been verified against the real endpoints.

Both backends implement exponential-backoff retry on transient errors
(network failure, rate limits, 5xx). Non-retryable errors (bad
request, auth failures) return `None` immediately, which the main
repository's circuit breaker treats as a generation failure.

## Relationship to the main repository

The main repository exposes a single abstract hook:

```python
# contemplative_agent/core/llm.py
class LLMBackend(Protocol):
    @property
    def model(self) -> str: ...
    @property
    def context_window(self) -> int: ...
    def generate(self, prompt, system, num_predict, format, *, temperature, think) -> Optional[BackendResult]: ...
```

This package provides concrete implementations of that Protocol for
Anthropic and OpenAI. `generate()` returns a `BackendResult` (text plus
optional `finish_reason` / token-usage fields); the main repository handles
sanitization, the truncation gate, and circuit breaking uniformly across
backends. `context_window` feeds the pre-flight budget guard with each
provider's real context limit. The Protocol itself has no knowledge of any
specific provider — it could be implemented for Gemini, Mistral, a
locally-hosted vLLM server, or any other backend.

The main repository's default behavior (`backend=None`) is the built-in
Ollama HTTP path, unchanged from before this add-on existed.

## License

MIT. See [LICENSE](LICENSE).
