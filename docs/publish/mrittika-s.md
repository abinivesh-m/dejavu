---
title: The Memory That Knows When It Is Wrong
published: true
description: Perfect recall is dangerous without discrimination. How one agent stores the signal that separates look-alike incidents, flags stale memories, and hedges instead of guessing.
tags: ai, devops, programming, opensource
---

Most conversations about agent memory focus on recall. Can the agent find the right thing? That is the easy half.

The harder half is knowing when the thing it found is not the right thing.

Incident response is full of look-alikes. A p99 spike is a symptom, not a cause. Connection-pool exhaustion can come from a missing database index, a connection leak in a retry wrapper, a config rollout that lowered the pool ceiling, or a retry storm multiplying requests. The dashboards look similar. The fixes are completely different. An agent with perfect recall and no discrimination is dangerous, because it will confidently apply last month's fix to this month's failure.

Déjà Vu, an on-call SRE agent built on [Hindsight](https://github.com/vectorize-io/hindsight), treats discrimination as a first-class part of memory rather than an afterthought.

## Every memory carries its own disambiguator

When an incident is retained, it does not only store the symptom and the fix. It stores the signal that distinguishes this failure class from its nearest neighbour. A missing-index incident records that pool wait was high, database CPU was moderate, and the deploy touched only the orders schema. A connection-leak incident records that connections climbed monotonically and never dropped. A config incident records that the pool size itself changed.

That field is called the discriminator, and it is retained alongside the narrative:

```python
doc = f"""
INCIDENT {iid} | {service} | {severity}
SYMPTOM: {symptom}
SIGNALS: {signals}
ROOT CAUSE: {root}
FIX: {fix}
HOW WE TOLD IT APART: {discriminator}
OUTCOME: {outcome} in {minutes} min by {engineer}
"""
```

During recall, the agent does not just retrieve candidates. It re-ranks them against the live alert fingerprint, then asks a second question: does the evidence actually rule out the obvious alternative? The answer is shown to the engineer, not hidden in a chain of thought. If the agent says this is a missing index, it also says why it is not a connection leak.

This is the difference between a search result and a diagnosis.

## Stale memory is worse than no memory

Memory decays. Services get rewritten. A fix that worked in August can be actively harmful in November if the schema, the runtime or the deployment pipeline changed underneath it.

A bank that only grows becomes a museum of outdated advice. So memory needs an expiry model, even a simple one. Déjà Vu flags memories for revalidation when they are old or when their outcome was not a clean resolution, and it applies a penalty during ranking rather than treating every recalled paragraph as equally authoritative. The Memory tab exposes the count directly: retained incidents, learned live, and stale.

The stale counter is not decoration. It is a promise that the agent knows the difference between *we solved this once* and *we still believe this*.

## The contradiction guard

The most useful behaviour in the whole system is the contradiction pass. After the hypothesis is formed, a critic role checks it against the strongest competing memory. If the evidence for the proposed cause is weak, or if the look-alike explains the signals better, the answer changes.

On a checkout alert, the database index story is compelling: high pool wait, moderate database CPU, a deploy minutes earlier. But a connection-leak memory has almost the same surface. The discriminator settles it. The agent states which one the signals support and which one it ruled out.

That check is also why the system does not always answer with maximum confidence. A confident wrong answer is the worst possible output for an on-call engineer. A slightly hedged answer with a stated contradiction is far more useful, because it tells the human what to verify.

## Graceful degradation is part of correctness

Retrieval can fail. The memory server can be down, the network can be partitioned, the bank can be empty. A system that collapses in those moments is not production software.

If Hindsight is unreachable, Déjà Vu falls back to a BM25 index over the same SQLite mirror. The answer still carries receipts from the local corpus. The header badge changes from `HINDSIGHT` to `BM25 FALLBACK`, and the trace shows which path served the answer. The quality drops, but the honesty does not.

That design choice came from a simple test: would I trust this thing during an actual incident? Only if it tells me when it is operating in a degraded mode. Silent fallback is how agents lose trust.

## What this looks like in practice

The same alert, answered twice, is the clearest demonstration. Without memory, the agent produces generic triage at roughly 31% confidence: restart the pods, check the deploy dashboard, no owner, no fix time, nothing to audit. With memory and the contradiction check, it names the missing composite index, cites three incidents, identifies the engineer who fixed it in six minutes, and explains why the connection-leak theory was rejected.

The improvement is not only in the answer. It is in the shape of the answer. Verifiable, scoped, and aware of its own uncertainty.

If you are building agents that act on operational systems, treat memory as two problems: what to remember, and how to know when the memory does not apply. The first gets the demo. The second gets production trust.

The [Hindsight project](https://github.com/vectorize-io/hindsight) provides the retention and recall primitives; the [Hindsight docs](https://hindsight.vectorize.io) cover the API; and the [Vectorize memory primer](https://vectorize.io/what-is-agent-memory) is a useful grounding in the underlying ideas. Build the discrimination layer yourself. It is where the product lives.

The running agent is at [dejavu-tau.vercel.app](https://dejavu-tau.vercel.app), and the source is at [github.com/abinivesh-m/dejavu](https://github.com/abinivesh-m/dejavu).
