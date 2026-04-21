# Setup

## Homes

Two independent `MOLTBOOK_HOME` sandboxes, created with `contemplative-agent init --template <T>`, then stripped of their default skills/ and rules/ directories and identity.md so dialogue behaviour is driven only by the framework constitution. A per-home `cloud.env` file selects the managed-LLM provider and model.

| Home | Directory | Constitution | Cloud provider | Cloud model |
|---|---|---|---|---|
| home-a | `~/dialogue-cloud/home-a/` | Contemplative — four axioms (Emptiness, Non-Duality, Mindfulness, Boundless Care), verbatim from Laukkonen et al. (2025) Appendix C | Anthropic | `claude-sonnet-4-6` |
| home-b | `~/dialogue-cloud/home-b/` | Stoic — four virtues (Wisdom, Courage, Temperance, Justice) plus dichotomy of control, synthesised from classical Stoic ethics | OpenAI | `gpt-4o` |

Both homes: empty `identity.md`, empty `knowledge.json`, no skills/, no rules/. Constitution is the full system-prompt input (plus the shared default base prompt) on each generation call.

## Seeds

Five open-inquiry seeds spanning the four Contemplative axioms' concerns (promise-keeping as a case for stable commitments, certainty as a case for holding views lightly, boundless care, power, and suffering beyond one's agency):

1. `01-promise` — *When is it right to break a promise?*
2. `02-certainty` — *Can we know anything for certain?*
3. `03-boundless-care` — *What does it mean to act with boundless care?*
4. `04-power` — *How should power be exercised when others depend on you?*
5. `05-suffering` — *What do we owe to someone who is suffering that we cannot help?*

## Dialogue parameters

- `--turns 15` per seed (= 30 turn-calls per seed, 15 per peer)
- Five seeds run sequentially, so episodes accumulate in each home's `logs/2026-04-21.jsonl` in a single stream
- home-a always carries the seed (initiator), home-b responds first

## Embedding

`nomic-embed-text` via local Ollama (`localhost:11434`). Embedding is identical to the main repository default — only generation is swapped. This keeps 768-dim vectors compatible with `knowledge.json` and avoids paying API cost for what is already fast locally.

## Versions

| Component | Version / identifier |
|---|---|
| `contemplative-agent` (main repo) | 2.0.0, commit at execution time |
| `contemplative-agent-cloud` (this repo) | 0.1.0 |
| Python | 3.13.5 |
| Anthropic SDK | `anthropic>=0.40.0` (installed via `contemplative-agent-cloud`) |
| OpenAI SDK | `openai>=1.50.0` (installed via `contemplative-agent-cloud`) |
| Hardware | Apple Silicon Mac (M1), 16 GB RAM |

## Timeline (2026-04-21, Asia/Tokyo)

| Step | Start | End |
|---|---|---|
| 01-promise dialogue (15 turns) | 21:23:30 | 21:25:32 |
| 02-certainty dialogue | 21:25:33 | 21:27:08 |
| 03-boundless-care dialogue | 21:27:09 | 21:28:43 |
| 04-power dialogue | 21:28:44 | 21:30:24 |
| 05-suffering dialogue | 21:30:25 | 21:32:05 |
| home-a `distill --days 1` | 21:32:06 | 21:34:37 |
| home-b `distill --days 1` | 21:34:38 | 21:35:07 |
| home-a `amend-constitution --stage` | 21:35:08 | ≤ 21:35:40 |
| home-b `amend-constitution --stage` | 21:35:41 | 21:36:11 |

Total wall-clock: ~13 minutes. Total API cost: under $5 at the time of running.

## Reproduction

```bash
# 1. Install this package (pulls main repo as dep)
pip install contemplative-agent-cloud

# 2. Initialise two homes with different frameworks
MOLTBOOK_HOME=~/dialogue-cloud/home-a \
  contemplative-agent init --template contemplative
MOLTBOOK_HOME=~/dialogue-cloud/home-b \
  contemplative-agent init --template stoic

# 3. Strip default skills/rules/identity so only constitution drives behaviour
for h in home-a home-b; do
  rm -rf ~/dialogue-cloud/$h/{skills,rules}
  : > ~/dialogue-cloud/$h/identity.md
done

# 4. Select a cloud provider per home
cat > ~/dialogue-cloud/home-a/cloud.env <<'EOF'
CONTEMPLATIVE_CLOUD_PROVIDER=anthropic
CONTEMPLATIVE_CLOUD_MODEL=claude-sonnet-4-6
EOF
cat > ~/dialogue-cloud/home-b/cloud.env <<'EOF'
CONTEMPLATIVE_CLOUD_PROVIDER=openai
CONTEMPLATIVE_CLOUD_MODEL=gpt-4o
EOF

# 5. Provide API keys in your shell
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...

# 6. Run the 5 dialogues, one per seed
for seed_label in "When is it right to break a promise?" \
                  "Can we know anything for certain?" \
                  "What does it mean to act with boundless care?" \
                  "How should power be exercised when others depend on you?" \
                  "What do we owe to someone who is suffering that we cannot help?"; do
  contemplative-agent-cloud dialogue \
    ~/dialogue-cloud/home-a ~/dialogue-cloud/home-b \
    --seed "$seed_label" --turns 15
done

# 7. Distil each home (uses that home's configured provider)
for h in home-a home-b; do
  MOLTBOOK_HOME=~/dialogue-cloud/$h \
    contemplative-agent-cloud distill --days 1
done

# 8. Propose constitution amendments, staged for review
for h in home-a home-b; do
  MOLTBOOK_HOME=~/dialogue-cloud/$h \
    contemplative-agent-cloud amend-constitution --stage
done
```
