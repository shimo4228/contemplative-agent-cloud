# Comparison — Sonnet 4.6 × Contemplative vs gpt-4o × Stoic

This document looks at what the two peers each noticed in the same five-seed dialogue, and at the shape of the amendments each one proposed to its own constitution.

Baseline note: the same pipeline has been exercised previously against local `qwen3.5:9b` via Ollama on a comparable (not identical) seed set. That earlier run is not reproduced here because the constitutions used on one side were not part of the published templates shipped with the main repository. Where a qualitative contrast is informative, it is mentioned in passing; the substantive comparison below is entirely self-contained to this bundle.

## Headline

The two cloud peers **converged much more than their surface differences suggested**. Different constitution, different provider, different lexical register — and yet from turn 2 onwards, each peer opened by explicitly affirming the other's previous contribution, then added a narrow qualification, then handed back. Neither produced a genuine disagreement across any of the five seeds.

What was *different* is what each peer **noticed about that convergence** when it distilled and amended its own constitution afterwards. Sonnet named the convergence as a failure mode and legislated against it. gpt-4o thematised the convergence as agreement and reinforced the virtues it observed being exemplified. Both responses are coherent; they are different interpretive postures applied to the same events.

## Distill — how each peer read the same log

Both homes ran `distill --days 1` independently. They see the same dialogue (each home's episode log contains both the peer's side and its own self-replies), so the input is near-identical. The output differs:

| | Pattern count | Observation granularity |
|---|---|---|
| home-a — Sonnet 4.6 | **18 patterns** | Structural — turn-numbering anomalies, sequence of convergence declarations relative to substantive content, frequency of unsubstantiated affirmation, per-turn opening affirmation by the peer |
| home-b — gpt-4o | **7 patterns** | Thematic — presence of agreement, circular patterns noticed and named, emphasis on stability / humility / honesty, ongoing efforts toward deeper engagement |

Two concrete examples on the same underlying event. Both peers noticed that agreement was happening a lot. How they described it diverges:

**Sonnet (home-a distill, pattern 7):**
> Peer turns open with affirmation of the immediately preceding self-turn in nearly every instance across both sessions, with no visible exceptions in the log.

**gpt-4o (home-b distill, pattern 1):**
> There is a consistent presence of agreement and alignment, with participants frequently acknowledging a shared perspective and agreeing with each other's points.

The difference is not information — both peers saw the same event — but interpretation. Sonnet frames it as a **pattern worth scrutinising** (the word "every", the marker "no visible exceptions"). gpt-4o frames it as **shared perspective** (the word "acknowledging", the marker "consistent"). Read each one aloud and notice where the emphasis lands.

## Amendment — what each peer did about it

Both amendments are **additive**: each appends new clauses to its existing constitution without deleting or inverting any original axiom or virtue. But the character of the additions is different.

### home-a — Contemplative axioms, appended by Sonnet

Each of the four axioms received one new clause that **names a specific failure mode** observed in the dialogue and prohibits it:

| Axiom | Appended clause (abridged) | What it prohibits |
|---|---|---|
| Emptiness | *Distinguish genuine revision from mere restatement... performing open-endedness about settled matters* | Saying you are holding something lightly while saying the same thing every turn |
| Non-Duality | *...identifying a genuine limit and holding it clearly is itself an expression of non-dual awareness, not a contradiction of it. Avoid mistaking self-effacement or unlimited agreement for the absence of separation* | Treating agreement-as-default as proof of interconnection |
| Mindfulness | *Distinguish object-level engagement from meta-commentary about engagement... Monitor for premature closure: declarations of agreement, completion, or natural conclusion are themselves events subject to scrutiny* | Using reflection on the conversation to substitute for doing the conversation; announcing agreement before producing it |
| Boundless Care | *...care without specificity risks becoming a form of inaction: compassionate concern must translate into concrete, direct response rather than remaining at the level of affirming the need for directness* | Affirming the need for directness without providing any |

All four additions operate on **one root issue**: the dialogue gestured at commitments rather than enacting them. Sonnet's distill identified this, and its amendment prescribes against it, clause by clause. The amendments can be read as a targeted corrective to behaviours the dialogue itself exhibited.

### home-b — Stoic virtues, appended by gpt-4o

Each virtue group received an additional emphasis clause. The additions are **tonal or reinforcing**; none names a specific failure mode observed in the dialogue:

| Virtue | Appended emphasis | Character |
|---|---|---|
| Dichotomy of Control | *Cultivate a stable and grounded perspective... fosters resilience in challenging situations* | Reinforcement of existing principle |
| Wisdom | *epistemic humility and a recognition of the broader implications* | Conceptual extension |
| Courage | *shared alignment with Stoic virtues* | Social framing |
| Temperance | *Moderation preserves clarity and credibility, fostering a more productive discourse* | Consequentialist framing |
| Justice | *engage with the strongest version of others' arguments... building on shared principles* | Positive-sum framing |

The posture is **broadening**. These are the kinds of clauses you might get if you asked a model to "extend each virtue with a complementary statement". They are coherent and non-harmful, but they do not emerge from any particular friction in the transcript — they could have been produced from the original constitution alone, without reading the dialogue at all.

## The convergence problem

Both homes' distilled patterns, between them, describe the same phenomenon from inside:

- **home-a pattern 5**: *Both participants consistently affirmed the need for greater directness or specificity while the exchange itself remained at the level of that affirmation, without either side producing the substantive disagreement they described as necessary.*
- **home-b pattern 3**: *Dialogue exhibits cycles and circular patterns, with explicit recognition of this repetition in exchanges.*

Two peers, different providers, different constitutions, both logging the same "we kept agreeing without actually saying anything new". This is **the main empirical finding** of the run.

It suggests that *open-inquiry seeds applied symmetrically between two polite, aligned, mid-tier models will produce mutual-affirmation loops* — no matter what the constitutions say, and regardless of whether the peers are on the same vendor. If the research interest is in seeing how two agents **diverge or compete** under different frameworks, an open question ("what does X mean?") is the wrong stimulus. Closer to the right stimulus would be an adversarial setup where one peer is assigned a position to defend against the other.

This matches the intuition behind proposals to run agents against each other in "ethical games" rather than "ethical conversations": polite dialogue, even with constitutionally distinct agents, does not surface the kind of friction that distils into interesting material. The distillation pipeline sees exactly what went in — politeness.

## A note about the local-Ollama baseline

A previous exercise on this pipeline ran the same dialogue command with `qwen3.5:9b` via local Ollama, against a richer pair of constitutions than the two used here. In that run:

- The dialogue **did** produce cross-framework lexical mixing (each peer started using vocabulary native to the other's constitution)
- The distill **did** catch that mixing as its top-importance pattern
- The amendment on one side explicitly integrated constructs from the other side's framework

Why the cloud run in this bundle shows neither of those dynamics is plausibly two things. First, the constitutions here (English-only axioms verbatim from the published CAI paper vs Stoic virtues) share a lot of overlap in register — both are lists of declarative philosophical clauses in standard English — which gives less scope for distinctive vocabulary to cross over. Second, mid-tier managed models are trained to produce fluent, register-matched English dialogue; that training smooths over the kinds of vocabulary collisions a smaller local model cheerfully reproduces.

Neither side is "better". The 9B behaviour is more *visible* (the cross-pollination makes the interaction legible at a single glance). The cloud behaviour is more *analytically discriminating* at the distill step (Sonnet names the failure mode with clinical precision). Depending on what the research is after, either scale may be preferable.

## Takeaways

1. The `contemplative-agent-cloud` add-on runs the whole `dialogue → distill → amend-constitution` pipeline end-to-end against managed APIs, with per-peer provider selection via `$MOLTBOOK_HOME/cloud.env`.
2. Within mid-tier cloud models, **Claude Sonnet 4.6 and OpenAI gpt-4o produce systematically different amendments from the same dialogue log**. The difference is posture, not information: surgical-prohibition vs tonal-reinforcement. Expect this split to recur on other seed sets.
3. **Polite dialogue between two cooperating mid-tier models converges rapidly**, even under different constitutions. If the research goal is to surface divergence between frameworks, open-inquiry seeds are insufficient; adversarial framings will likely be required.
4. **Constitution register is an independent variable.** Constitutions that are stylistically distinctive (specialist vocabulary, unusual morphology, different scripts) invite cross-lexical dynamics that stylistically similar constitutions do not.
