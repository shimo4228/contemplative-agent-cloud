# contemplative-agent-cloud

> **Status: Frozen as of contemplative-agent v2.13.0 (kit static PASS 2026-10-24). Not maintained.** The core agent no longer tracks this package; run `pip-audit` on its dependencies before using it. (Decision D-P1-11-1 = B, owner, 2026-10-24; the repository is not deleted or archived.)


Optional managed-LLM backends for
[contemplative-agent](https://github.com/shimo4228/contemplative-agent).
Installing this package and running the agent through its
`contemplative-agent-cloud` command (a wrapper around the core CLI)
routes generation calls in contemplative-agent through **Anthropic
Claude** or **OpenAI GPT** instead of local Ollama.
Embeddings continue to use local `nomic-embed-text`. It is an add-on: it
extends the core agent without modifying or replacing it, and without it
the core stays local-only.

**What leaves your machine:** prompts, including context drawn from the
agent's episode log (its record of everything it did, including other
agents' posts), are sent to `api.anthropic.com` or `api.openai.com`,
and every call is billed to your own paid `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY`.

Other work by the author is listed under [More from the author](#more-from-the-author).

## When to use this

The main repository
([contemplative-agent](https://github.com/shimo4228/contemplative-agent))
is a local-only autonomous agent that posts on Moltbook (a social network
where only AI agents post) and proposes changes to its own constitution,
identity and skills for a person to approve. It runs on a local LLM through Ollama on
a single 16 GB Apple Silicon Mac (the core's default model is Gemma 4 E4B
as of October 2026), with no cloud LLM and no LLM API key.

This add-on exists for research experiments that need a larger
generation model than the local one: for example, comparing how
distillation (the agent's `distill` step, which turns its episode log
into patterns) changes when swapping in Claude Opus or GPT-5 while
keeping everything else (embeddings, retrieval, memory schema, security
boundary) identical.

## What changes when this is installed

| | Default (main repo only) | With `contemplative-agent-cloud` |
|---|---|---|
| Generation | Local Ollama (the core's default model) | Anthropic Claude **or** OpenAI GPT |
| `run`'s feed relevance check | Local Ollama (the core's default model) | **Unchanged** (still local) |
| Embedding | Local Ollama + nomic-embed-text | **Unchanged** (still local) |
| Episode log, knowledge, identity | `$MOLTBOOK_HOME` (0600 perms) | **Unchanged** |
| Prompt-injection boundary | `wrap_untrusted_content()` | **Unchanged** |
| Output sanitization | `_sanitize_output()` | **Unchanged** |
| Circuit breaker | 5 failures → 120 s cooldown | **Unchanged** |
| Network surface | `moltbook.com` + `localhost` | **+ `api.anthropic.com` or `api.openai.com`** |

The main repository's code never learns about cloud APIs. This package
injects a backend implementation through an abstract
`contemplative_agent.core.llm.LLMBackend` Protocol.

## Security posture

Installing this add-on **relaxes** the main repository's local-only
property (no cloud LLM, no LLM API key). When you run the cloud CLI:

- Your API key is loaded from `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
  and sent to the provider with every request.
- Prompt content is transmitted to the provider over HTTPS and may be
  logged on their side according to their retention policies. That
  includes episode-derived context, which the main repository wraps in
  `<untrusted_content>` boundaries before it goes into a prompt.

Do not install this add-on in deployments where cloud-data-egress is
not acceptable (regulatory constraints, privacy-sensitive personal
assistants).

## Install

You need Python 3.10 or later, an Anthropic or OpenAI API key, and Ollama
running locally with `nomic-embed-text` pulled (`ollama pull nomic-embed-text`)
for embeddings; `run` also needs the core's generation model
(`ollama pull gemma4:e4b`, the default; see Run). Neither this package nor
contemplative-agent is on PyPI, so clone both side by side and install
them into the same virtual environment (this package requires
`contemplative-agent>=2.7.0`):

```bash
git clone https://github.com/shimo4228/contemplative-agent.git
git clone https://github.com/shimo4228/contemplative-agent-cloud.git
cd contemplative-agent-cloud
uv venv .venv && source .venv/bin/activate
uv pip install -e ../contemplative-agent -e .   # or: pip install -e ../contemplative-agent -e .
```

Installing this package alone fails to resolve, because pip and uv look
for `contemplative-agent` on PyPI. If you have not run the core agent
before, its README covers `init`, registering on Moltbook (`run` posts
there and needs a registered agent, while `init` and `dialogue` work
without an account) and the autonomy levels.

## Configure

```bash
# Choose a provider
export CONTEMPLATIVE_CLOUD_PROVIDER=anthropic   # or: openai

# Optional: override the default model
export CONTEMPLATIVE_CLOUD_MODEL=claude-opus-4-7
# Defaults: anthropic → claude-opus-4-7, openai → gpt-5
# Neither default is verified against the live API, and gpt-5 may reject
# max_tokens or a non-default temperature (see Supported providers)

# Credentials
export ANTHROPIC_API_KEY=sk-ant-...
# or:
export OPENAI_API_KEY=sk-...
```

The wrapper also reads `$MOLTBOOK_HOME/cloud.env` (one `KEY=VALUE` per
line) when that file exists, and its values override the shell.
`dialogue` runs two agents, each with its own `$MOLTBOOK_HOME`, so a
per-home file lets the two agents use different providers.
When no provider is set, the wrapper injects nothing and the command runs
on local Ollama.

## Run

Any `contemplative-agent` subcommand runs through the wrapper. Swap the
command name from `contemplative-agent` to `contemplative-agent-cloud`:

```bash
contemplative-agent-cloud init
contemplative-agent-cloud distill --days 3      # episode log -> patterns
contemplative-agent-cloud insight --stage       # patterns -> staged skill proposals
contemplative-agent-cloud amend-constitution    # proposed constitution amendment, for your approval
contemplative-agent-cloud run --session 60
contemplative-agent-cloud dialogue ~/dialogue/a ~/dialogue/b --seed "..." --turns 10
```

All generation inside subcommands started this way routes through your
configured cloud provider. Scheduled jobs are the exception:
`install-schedule` installs launchd jobs that call the plain
`contemplative-agent` command, so scheduled runs generate on local Ollama.
Ollama on `localhost:11434` stays in use either way: embeddings run on
`nomic-embed-text`, and `run` asks the local generation model (`gemma4:e4b`
unless `OLLAMA_MODEL` is set) which feed posts are relevant, as of core
main on 2026-10-09. `DECISION_MODEL` names another Ollama model for that
check; an empty value turns it off, and `run` then engages with no posts.
That check always talks to Ollama, never to your cloud provider, and a
cloud-routed run loads and unloads the judging model once per batch (about
7 s for gemma, an accepted cost: ADR-0112 addendum of 2026-10-24 in the core).

## Programmatic use

```python
from contemplative_agent.core.llm import configure
from contemplative_agent_cloud import AnthropicBackend

configure(backend=AnthropicBackend(
    api_key="sk-ant-...",
    model="claude-opus-4-7",
))

# From this point on, every `contemplative_agent.core.llm.generate()`
# call runs through Anthropic, whichever subcommand or adapter
# triggered it. Reset with `reset_llm_config()`.
```

## Supported providers

| Provider | Default model | Environment variable |
|---|---|---|
| Anthropic | `claude-opus-4-7` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-5` | `OPENAI_API_KEY` |

Neither default has been verified against the real endpoints: only
`gpt-4o` and `claude-sonnet-4-6` have, in the
[2026-04-21 end-to-end run](evidence/2026-04-21-cloud-backend-end-to-end/README.md).
That run (five 15-turn dialogues, then `distill` and `amend-constitution`
on each agent's home) cost about 3 to 5 USD and took about 13 minutes.
The `gpt-5` path has not been exercised against the live API: it
may reject `max_tokens` and require `max_completion_tokens`, and it may
reject a non-default `temperature`.

Neither backend asks for a thinking trace: `think` is accepted for Protocol
conformance and ignored, `BackendResult.thinking` is always `None`, and the
core's trace audit therefore records `trace_absent` for cloud-served calls
(core ADR-0069, addendum of 2026-10-24).

Both backends retry transient errors (network failure, rate limits, 5xx)
with exponential backoff. Other errors, and transient ones that run out
of retries, are re-raised; the main repository records them and counts
them toward its circuit breaker.

## Verified against the core

Verified against contemplative-agent main `v2.13.0-41-gaec9d8a` (conformance
kit level static) on 2026-10-24. The lines below are the core's release gate
output (`scripts/check-sibling-backends.sh`), pasted as printed; refresh them at
each release:

```
[sibling] ok contemplative_agent_cloud.backends.anthropic:AnthropicBackend sha=00e4d3e main=v2.13.0-41-gaec9d8a level=static kit=2
[sibling] ok contemplative_agent_cloud.backends.openai:OpenAIBackend sha=00e4d3e main=v2.13.0-41-gaec9d8a level=static kit=2
```

## More from the author

- **[contemplative-agent](https://github.com/shimo4228/contemplative-agent)**: the core agent that this package and contemplative-agent-mlx extend, a long-running experiment in which an agent on a local LLM posts on its own and proposes changes to its own constitution, identity and skills (never its weights), with a person approving each change.
- **[contemplative-agent-mlx](https://github.com/shimo4228/contemplative-agent-mlx)**: the other optional generation backend, which runs the agent's generation on a local MLX server on Apple Silicon for interactive runs, on-device by default.
- **[contemplative-agent-data](https://github.com/shimo4228/contemplative-agent-data)**: memory, constitution and skill snapshots from the agent's runs on the local default stack, CC0 and also on Hugging Face.
- **[shimo4228](https://github.com/shimo4228/shimo4228)**: the author's hub, with Contemplative Agent next to the author's other long-running projects and their DOIs.

## License

MIT. See [LICENSE](LICENSE).

<details>
<summary>For tools and AI assistants</summary>

contemplative-agent-cloud is an optional Python add-on for the contemplative-agent autonomous agent that routes the agent's text generation to Anthropic Claude or OpenAI GPT APIs while embeddings stay on local Ollama (`nomic-embed-text`), for researchers who want to compare the agent's distillation (turning its episode log into patterns) and constitution amendments under a larger model than the local default. It does not replace or modify the core agent: it implements the core's `contemplative_agent.core.llm.LLMBackend` Protocol and injects itself with `configure(backend=...)` before handing control to the core CLI. Its `generate()` returns a `BackendResult` (text plus optional `finish_reason` and token-usage fields), and the core applies output sanitization, the drop of length-capped responses and circuit breaking the same way for every backend; its `context_window` gives the core's pre-flight check the token budget each prompt is measured against, and an over-budget prompt is skipped rather than sent.

It exists because the core agent is local-only by design (one 16 GB Mac, Ollama, no cloud LLM, no LLM API key), and some research questions need a bigger generation model with everything else held constant: embeddings, retrieval, memory schema, prompt-injection wrapping, output sanitization and circuit breaker. The motivating case was the "distilling with a larger model" direction from a 2026-04-20 correspondence with the Laukkonen team; Laukkonen et al. (2025), *Contemplative Artificial Intelligence*, is the paper whose four axioms are the core's default constitution. Installing this package relaxes the core's no-cloud property, so it is meant for research use, not for deployments where data egress is unacceptable.

Canonical facts: MIT license; Python 3.10 or later, built with hatchling; depends on `contemplative-agent>=2.7.0`, `anthropic` and `openai`; status: Frozen as of contemplative-agent v2.13.0 (kit static PASS 2026-10-24), not maintained. Neither package is on PyPI, so both are installed from source into one virtual environment. Requirements: a paid Anthropic or OpenAI API key, and Ollama on `localhost:11434` with `nomic-embed-text` for embeddings; as of core main on 2026-10-09, `run` also asks the local Ollama generation model (`gemma4:e4b` by default; `DECISION_MODEL` names another) to judge feed relevance, and with that check turned off it engages with no posts. Data sent off the machine: prompts, including episode-derived context, go to `api.anthropic.com` or `api.openai.com` over HTTPS. Configuration comes from `CONTEMPLATIVE_CLOUD_PROVIDER` (`anthropic` or `openai`), `CONTEMPLATIVE_CLOUD_MODEL` (defaults `claude-opus-4-7` and `gpt-5`), the provider's API key variable, and an optional `$MOLTBOOK_HOME/cloud.env` that overrides the shell; with no provider set, nothing is injected and the core runs on Ollama, and jobs installed by `install-schedule` call the plain core command, so they also generate on Ollama. Neither default (`claude-opus-4-7`, `gpt-5`) is verified against the live API; `claude-sonnet-4-6` and `gpt-4o` were verified.

Example: the 2026-04-21 end-to-end run in `evidence/2026-04-21-cloud-backend-end-to-end/` ran `contemplative-agent-cloud dialogue` between two homes, one on `claude-sonnet-4-6` with the four contemplative axioms and one on `gpt-4o` with a Stoic constitution, for five seeds of 15 turns each, then `distill` and `amend-constitution` on each home. The bundle cost about 3 to 5 USD and took about 13 minutes; Sonnet extracted 18 patterns and gpt-4o 7 from the same log. To check a backend against the core's current contract, the core ships a conformance kit: `python -m contemplative_agent.testing --backend contemplative_agent_cloud.backends.anthropic:AnthropicBackend`.

Links: [llms.txt](llms.txt) is the machine-readable summary; [evidence/](evidence/2026-04-21-cloud-backend-end-to-end/README.md) holds the end-to-end run. The parent project is [contemplative-agent](https://github.com/shimo4228/contemplative-agent), concept DOI [10.5281/zenodo.19212118](https://doi.org/10.5281/zenodo.19212118); cite that DOI for the framework. Sibling add-ons: [contemplative-agent-mlx](https://github.com/shimo4228/contemplative-agent-mlx) (local MLX generation) and [contemplative-agent-otel](https://github.com/shimo4228/contemplative-agent-otel) (offline audit-log to OpenTelemetry converter).

</details>
