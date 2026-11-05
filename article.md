# Your On-Call Agent Needs Hindsight, Not a Bigger Model

It is 02:14. Checkout p99 has gone from 400 ms to 3.9 seconds, the payment provider is retrying, and an alert is burning through the error budget.

The engineer who fixed this exact failure six weeks ago is asleep. The postmortem exists somewhere. The migration that actually solved it was applied by hand and never written down. So the person on call does what everyone does at 2 a.m.: they search, they guess, and then they restart the pods.

The restart works for forty minutes.

I kept coming back to that gap. The model is not the bottleneck. A good model has read every runbook and every public postmortem. What it does not have is *your* history: this failure, on this service, with these signals, fixed in six minutes by a specific person, and whether the fix held.

I built Déjà Vu to test that claim seriously — an on-call SRE agent whose entire value comes from remembering incidents, and whose memory layer is [Hindsight](https://github.com/vectorize-io/hindsight).

## What the system actually does

Déjà Vu watches a queue of alerts. When one fires, it builds a query from the alert's service, title, body and full signal fingerprint, recalls candidate incidents from a Hindsight bank called `dejavu-oncall`, re-ranks them, and answers with evidence attached.

The answer is not a paragraph. It is a hypothesis plus receipts:

- `INC-1006` — missing composite index on `orders(created_at, status)` — 6 minutes — Priya Raman — resolved
- `INC-1001` — same cause class — resolved
- `INC-1002` — same class — resolved

Same alert, memory off: *"generic triage, restart the affected pods"*, 31% confidence, no incident, no owner, no fix time. Memory on: the index migration, 97% confidence, the receipts, a named engineer. The second answer is not smarter. It is informed.

## Making memory the actual product

The naive version of this is a vector store full of postmortems with a prompt that says "use the context below." It demos well and fails quietly, for three reasons.

It retrieves paragraphs, not incidents — so nothing is auditable. It treats similarity as identity — so a look-alike incident with a different cause gets recommended with full confidence. And it never learns from what happened after the fix.

So the memory is structured, not chunked. One document per incident, with metadata that survives retrieval:

```python
resp = client().retain(
    bank_id="dejavu-oncall",
    content=text,                       # symptom, signals, cause, fix, time, outcome
    document_id=incident_id,
    context=f"{inc.get('service')} {inc.get('severity')} incident on {ts[:10]}",
    metadata={
        "incident_id": incident_id,
        "service": inc.get("service"),
        "root_cause": inc.get("root_cause"),
        "fix": inc.get("fix"),
        "outcome": inc.get("outcome"),
        "fix_minutes": str(inc.get("fix_minutes")),
        "engineer": inc.get("engineer"),
        "severity": inc.get("severity"),
    },
    tags=[inc["service"], inc["severity"], inc["outcome"]],
)
```

That metadata is the difference between a receipt and a rumour. When the agent says "six minutes, Priya Raman, resolved," those values came back from memory, not from the model's imagination.

Recall is equally deliberate. The alert's fingerprint becomes the query, and Hindsight returns candidates by meaning. Then the application re-ranks them, because retrieval similarity and operational similarity are not the same thing:

```python
similarity = 0.50 * signal_similarity + 0.45 * text_similarity + 0.05 * coverage
score = 0.82 * similarity
score += 0.10 * min(1.0, support / 3)      # how many incidents back this cause
score += 0.08 * success_rate               # did the fix actually hold
score += 0.02 * recency                    # recent precedent wins ties
if stale:
    score -= 0.06                          # flag it, do not trust it
```

Fifty percent of the decision is the signal fingerprint — the numbers, not the prose. `p99_ms 3900` against `3800`. `pool_wait_ms 1240` against `1180`. `cert_age_days 2` against `61`. That last one is why a certificate incident gets ruled out even when the text looks identical.

## The part that matters: the contradiction guard

Two incidents can share every word and need opposite fixes. Incident `INC-1009` has the same service, the same pool timeout, the same graph shape, and 53% similarity to the live alert. But its cause was a pool size capped during a config rollout, and its fix was a config change plus a redeploy — not an index.

Before committing, Déjà Vu checks the runner-up failure class. If a different cause is close, it surfaces the look-alike explicitly: the incident ID, the similarity, the one signal that separates them, and the different fix it required.

This is the failure mode of every naive retrieval system. A text search returns the nearest paragraph. The agent has to tell you what it ruled out, and why.

## Measurement, not a claim

Every memory product says it improves. Almost none measure it, because measuring it honestly is uncomfortable.

The repo includes a replay that walks the incident corpus in chronological order. At each incident, the agent may only use memories that existed **before** that timestamp. No peeking. No LLM in the grading loop.

Across 22 graded incidents: **50% top-1**, **64% top-3**. First six graded alerts: **33%**. Last six: **83%**.

That last pair is the whole thesis. The agent is measurably better at the end of the quarter than at the start, because it lived through the quarter. The Learning screen plots every graded incident, including the ones it got wrong. A memory system that only shows its wins is a marketing surface.

## The loop has to close

Resolving an alert is not the end of the interaction. It is the write. When an engineer resolves an incident, Déjà Vu stores a postmortem, retains it with `source: live`, and marks the alert closed. Fire the same fingerprint again and the first receipt is the incident that was just created, answered in milliseconds.

That closed loop is also where a second agent earns its place. In the Band room, `DejaVu-Recall` posts the hypothesis and receipts, then `DejaVu-Critic` answers the recall — not the alert — with four deterministic checks: at least two receipts, no stale precedent, precedent fixes that held, confidence above threshold. It can block the fix from ever reaching a human.

I wrote the critic as code, not as another model call, because a reviewer should check evidence, not generate more of it.

## What I got wrong

Three things, in order of embarrassment.

First, I scoped recall to the same service. That hid the useful lesson: a missing index on `payments-api` is the same failure as a missing index on `checkout-api`. Cross-service transfer is where most of the late-corpus accuracy came from.

Second, I graded at string level before switching to failure classes. "Missing index on orders" and "missing index on settlement_date" are different strings and the same lesson. String-level grading made the agent look worse than it was, and would have made me tune the wrong thing.

Third, I trusted retrieval scores for too long. The signal fingerprint is weighted above text on purpose now. The text is how you find candidates; the numbers are how you decide.

## Where it still breaks

First-time failures cannot be recalled. If the team has never seen it, memory has nothing, and the Learning screen shows exactly those incidents as misses.

Per-service histories are small — eight to ten incidents each — so cross-service transfer helps but is not evidence of production-scale performance. The corpus is synthetic, because real incident data is confidential, and the ranking weights were tuned on it. A production deployment needs re-tuning against real signals and a plan for the long tail of incidents that happen once.

And memory can be wrong. Precedent is not proof. That is why every answer carries confidence, receipts, and a visible trace of which path served it. When Hindsight is unreachable, the app serves from a BM25 index over the same SQLite mirror and the header badge changes from `HINDSIGHT` to `BM25 FALLBACK`. A demo should not die because a service did not start, but it should never pretend which path answered.

## What I took away

The next improvement in on-call tooling is not a bigger context window. It is a memory that is specific to your systems, weighted by what actually worked, honest about what it does not know, and measured against its own past.

Hindsight made the memory layer the easy part: a bank, a retain with real metadata, a recall that returns meaning. The hard part was deciding what counts as the same failure — and being willing to show the moment the agent gets it wrong.

At 2 a.m., the question is not "what does a good SRE do?" It is "what did we do last time, did it work, and who can I ask?"

If you are building agents with memory, start with [Hindsight's open-source memory engine](https://github.com/vectorize-io/hindsight) and read the [Hindsight documentation](https://hindsight.vectorize.io/). It is also worth getting clear on [what agent memory actually means](https://vectorize.io/what-is-agent-memory) before you design a schema you will regret.
