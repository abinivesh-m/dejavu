# 33% to 83%: How to Measure Whether Agent Memory Actually Works

Every memory product claims to get better over time. Very few show the curve.

That is a problem, because "it remembers" is easy to demo and hard to prove. A retrieved paragraph can look impressive in a screenshot while adding nothing to the answer. The only honest question is: compared with the same agent before it had this memory, does it solve the next problem better?

Déjà Vu is an on-call SRE agent built on [Hindsight](https://github.com/vectorize-io/hindsight). To answer that question we built a replay harness instead of a highlight reel.

## The replay rule: no future memories

The corpus contains incidents ordered by time, many of which share failure classes. The replay walks that corpus chronologically. At each incident, the agent may only use memories that existed before that incident. Nothing from the future. No LLM in the grading loop. The retrieval path is a deterministic BM25 index over the same documents the production system would have had at that moment.

That single constraint turns a demo into an experiment. If the agent scores well, it is not because it saw the answer earlier in the list. It is because earlier incidents taught it something that transferred.

A simplified version of the loop:

```python
for i, incident in enumerate(corpus):
    known = corpus[:i]                 # as-of memory only
    predicted = rank(incident.query, known)
    actual = incident.cause_class
    correct = predicted[0].cause_class == actual
    graded.append({
        "n": i + 1,
        "predicted": predicted[0].title,
        "actual": incident.title,
        "correct": correct,
        "accuracy": mean(g["correct"] for g in graded),
    })
```

The output is a sequence of predictions with a running accuracy, not a single aggregate that hides the shape of learning.

## What the numbers say

Across 22 graded incidents:

- **top-1 accuracy: 50%** — the correct failure class on the first guess
- **top-3 accuracy: 64%** — the correct class in the top three
- **first six graded alerts: 33%**
- **last six graded alerts: 83%**

The aggregate is deliberately unglamorous. Fifty percent top-1 is not a victory lap. But the gap between the first six and the last six is the product thesis: as the bank accumulates specific, structured incidents, the agent stops guessing generically and starts recognising patterns.

The early failures are instructive. The first graded alert is a Redis eviction problem. The agent predicts a Kafka consumer rebalance loop, because it has no relevant precedent and the surface vocabulary points at streaming infrastructure. That is what a cold start looks like. By the end of the replay, a config-driven pool ceiling is matched to the same failure class seen earlier, and a month-end reporting query is recognised immediately.

We surface both sides in the product. The Learning tab shows the cumulative curve, the early and late windows, and a "Same agent, three moments" strip: alert #1 with zero memories, a middle alert with eleven, and the final alert with twenty-one. The first card is a cold miss. The last two are matches. That progression is more convincing than any single accuracy number, because it shows the mechanism.

## Why not just ask an LLM to grade it?

Because the point is to test memory, not model capability. An LLM grader introduces its own priors, its own variance and its own cost. A deterministic ranker over the as-of corpus is reproducible: the same corpus produces the same curve. If the curve improves, the improvement came from retrieval, which is what the memory layer controls.

This does not mean the production agent is deterministic. In production, Hindsight recalls candidates by meaning, the application re-ranks them against the live signal fingerprint, and a language model writes the final hypothesis from the receipts. The replay isolates one variable — whether the right past incident was available and ranked highly — so the rest of the system can be evaluated separately.

## Measure the failure modes too

A learning curve that only shows wins is marketing. The interesting questions are about what goes wrong.

Three failure modes matter in practice. First, **cold start**: with an empty bank, the agent is generic, and it should say so rather than invent confidence. Second, **look-alikes**: two incidents with similar symptoms and different causes. Re-ranking by signals and forcing a stated contradiction is what prevents a confident wrong answer. Third, **stale memory**: an old fix that no longer applies. A bank that never expires becomes a source of harm, so stale memories are flagged and penalised rather than trusted.

We also test degradation. If Hindsight is unreachable, the agent falls back to the local BM25 index and labels the path. The receipts remain; the quality drops; the user is told. A memory system that hides its failure mode is not measurable, because you cannot tell when it is lying.

## What we would measure next

The replay measures cause-class retrieval, which is the core of the value proposition. The next step is outcome-weighted evaluation: did the recalled fix actually resolve the incident, and how many minutes did it save compared with the generic baseline? That requires more resolved incidents and a way to attribute time saved without confounding variables.

Until then, the honest claim is narrow and testable: on a chronological replay with no future knowledge, the same agent improves from 33% to 83% as its memory bank grows, and every prediction is backed by a retrievable incident.

That is a better claim than "it remembers." It is falsifiable.

The [Hindsight repository](https://github.com/vectorize-io/hindsight) is open source, the [documentation](https://hindsight.vectorize.io) covers retention and recall, and the [Vectorize primer](https://vectorize.io/what-is-agent-memory) is a good conceptual starting point. Build the replay harness before you build the landing page. The curve will tell you whether you have a product.

The running agent is at [dejavu-tau.vercel.app](https://dejavu-tau.vercel.app), and the source, including the replay harness, is at [github.com/abinivesh-m/dejavu](https://github.com/abinivesh-m/dejavu).
