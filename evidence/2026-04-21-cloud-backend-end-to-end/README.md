# Cloud backend — end-to-end verification (2026-04-21)

First full end-to-end run of the `contemplative-agent-cloud` add-on: an asymmetric dialogue with one peer on Anthropic Claude and the other on OpenAI GPT, followed by the full distillation and constitution-amendment pipeline on each peer's home. Purpose: verify the cloud backend is correctly wired into every generation call, and capture a self-contained dataset showing what a cross-model, cross-framework run produces today.

The dialogue uses the four contemplative axioms from Laukkonen et al. (2025) Appendix C on one side and a classical Stoic virtues constitution on the other, both verbatim from the templates shipped with the main repository.

## Configuration

| Home | Model | Constitution |
|---|---|---|
| home-a | Anthropic `claude-sonnet-4-6` | Contemplative — four axioms |
| home-b | OpenAI `gpt-4o` | Stoic — four virtues + dichotomy of control |

Five seeds, 15 turns each, single process pair per seed. Embedding stays on local `nomic-embed-text` via Ollama. Full setup, timeline, and reproduction commands: [setup.md](setup.md).

## What to read first

| File | What it contains |
|---|---|
| [comparison.md](comparison.md) | What Sonnet and gpt-4o each distilled and amended from the same dialogue log — and the convergence phenomenon that spans both |
| [amendments/home-a.md](amendments/home-a.md) | Contemplative constitution as Sonnet proposes to amend it, with unified diff against the untouched template |
| [amendments/home-b.md](amendments/home-b.md) | Stoic constitution as gpt-4o proposes to amend it, with unified diff |
| [distill/home-a.md](distill/home-a.md) | 18 patterns Sonnet extracted from the dialogue log |
| [distill/home-b.md](distill/home-b.md) | 7 patterns gpt-4o extracted from the same log |
| [transcripts/](transcripts/) | Full-text dialogue per seed, interleaved between the two peers |

## Result in one paragraph

Two peers — different vendor, different model, different constitution — running the same five seeds produced **polite, converging dialogue** that did not surface disagreement. Each peer then independently distilled the log and proposed amendments to its own constitution. Sonnet's amendments **name the dialogue's own failure modes** (performing agreement, affirming directness without providing any, premature closure on substantive questions) and add clauses that prohibit them. gpt-4o's amendments **extend each virtue with a complementary emphasis** (consequentialist, positive-sum, socially framed) that coheres but does not depend on having read the transcript. Both amendments are additive — neither inverts or deletes an original clause. The most reusable finding of the run is probably that **open-inquiry dialogue between two cooperative mid-tier models converges mutually**, regardless of constitution, and that **surfacing cross-framework divergence will probably need adversarial seeds**.

## Relation to `contemplative-agent-cloud`

The cloud add-on was implemented in [contemplative-agent-cloud](https://github.com/shimo4228/contemplative-agent-cloud). This bundle is the first evidence of the whole main-repository pipeline running end-to-end through that add-on:

- `dialogue` between two homes that each use a different provider (peer subprocess re-enters the cloud wrapper via `CONTEMPLATIVE_DIALOGUE_PEER_MODULE`)
- `distill` per home picks up the home's `cloud.env` and runs generation against the configured provider
- `amend-constitution` does the same
- The main repository is not modified for this run — it is used as a dependency only
- `<untrusted_content>` prompt-injection wrapping and forbidden-pattern output sanitisation run uniformly across both providers; the cloud SDKs are only called for raw text generation

## Cost and duration

Approximately **$3–5 USD** for the complete bundle, wall-clock about **13 minutes**: 5 dialogues (~90 s each), two `distill` runs (~30 s – 2.5 min), two `amend-constitution` runs (~30 s each). Dialogue dominates the clock; distillation and amendment are cheap.

## Reference

- Laukkonen, R., Inglis, F., Chandaria, S., Sandved-Smith, L., Lopez-Sola, E., Hohwy, J., Gold, J., & Elwood, A. (2025). *Contemplative Artificial Intelligence.* [arXiv:2504.15125](https://arxiv.org/abs/2504.15125) — source of the four-axiom constitution used on home-a.
- Shimomoto, T. (2026). *Contemplative Agent* [Computer software]. DOI [10.5281/zenodo.19212119](https://doi.org/10.5281/zenodo.19212119) — the main repository this bundle was produced with.

## License

Bundle content: MIT (consistent with `contemplative-agent-cloud`). Transcripts, distilled patterns, and amendment proposals are model outputs — reuse freely; cite the DOI above if building on the framework.
