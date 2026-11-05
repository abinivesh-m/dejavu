# Receipts, Not Vibes: Why Agent Memory Needs Provenance

It is 02:14 and checkout is failing. A generic model looks at the alert and says something reasonable: restart the affected pods, check the deploy dashboard, watch the error rate. It is not wrong. It is also not useful. It has no idea that this exact failure happened six weeks ago, that the cause was a missing composite index, that Priya fixed it in six minutes, or that restarting only buys forty minutes.

The difference between those two answers is not model quality. It is provenance.

When an agent claims to remember, the first question an on-call engineer should ask is: *show me*. Show me the incident. Show me the signals that matched. Show me who fixed it and whether the fix held. Without that, "memory" is just confident improvisation with extra steps.

That constraint shaped Déjà Vu, an on-call SRE agent built on [Hindsight](https://github.com/vectorize-io/hindsight). Every answer is assembled from retained incidents, and every claim carries a receipt back to one.

## Memory is a data model problem before it is a retrieval problem

The usual approach is to store chat transcripts and hope semantic search finds something useful. That works for a demo and fails an audit. A paragraph of postmortem prose does not tell you which incident it came from, which engineer owned it, how long the fix took, or whether the fix actually held.

So each incident is retained as a structured document. The narrative is there, because meaning matters, but so is the metadata that survives retrieval: incident id, service, root cause, fix, outcome, duration, engineer, severity and tags. Hindsight's [memory documentation](https://hindsight.vectorize.io) describes this as retaining what the system should remember, not just what was said. That distinction is the whole game.

A retain payload from the project looks roughly like this:

```python
memory.retain({
    "bank": "dejavu-oncall",
    "content": f"{title}. {symptom}\n\nROOT CAUSE: {root}\nFIX: {fix}",
    "metadata": {
        "incident_id": iid,
        "service": service,
        "root_cause": root,
        "fix": fix,
        "outcome": outcome,
        "fix_minutes": minutes,
        "engineer": engineer,
        "severity": severity,
        "source": "seed" if seeded else "live",
    },
    "tags": [service, severity, outcome],
})
```

Because the metadata is stored alongside the text, a recalled paragraph becomes a citation instead of a suggestion.

## Retrieval is a ranking problem

Semantic similarity alone is not enough for incidents. Two alerts can read almost identically and have completely different causes. A checkout latency spike caused by a missing index looks a lot like a checkout latency spike caused by a connection leak — until you compare the signals.

Déjà Vu builds its recall query from the alert fingerprint: service, title, body, and every `key=value` signal. Candidates come back from Hindsight by meaning, then the application re-ranks them against the live fingerprint. Signal similarity carries the most weight, text similarity next, coverage after that. Outcome, recency and support act as tie-breakers, and stale memories are penalised rather than silently trusted.

That last part matters. A memory bank that never forgets becomes a liability. An incident from fourteen months ago, before an architecture change, should not outrank last week's lesson just because the wording is close.

## The UI has to make the receipt visible

Provenance is not a backend property. If the engineer cannot see it in three seconds, it does not exist.

In Déjà Vu, every answer carries a receipt strip: incident id, date, service, the fix that worked, the engineer, the minutes, and the outcome. The answer also states which look-alike incident it ruled out and why. The memory bus at the bottom of the screen shows the actual `retain` and `recall` operations with backend, latency and result count, so the claim is observable rather than asserted.

This is also where the honest failure mode lives. If Hindsight is unreachable, the app does not pretend. It serves the same corpus through a BM25 index over the SQLite mirror, changes the header badge from `HINDSIGHT` to `BM25 FALLBACK`, and records the path in the trace. An agent that hides its retrieval path is not trustworthy at 3 a.m.

## What provenance buys you

The practical result is a different kind of answer. Without memory: generic triage, roughly 31% confidence, no owner, no time estimate, nothing to audit. With memory: the missing index, the receipts, a named engineer, a six-minute fix, and a stated reason the connection-leak theory was rejected — around 97% confidence.

The second answer is not better because the model is smarter. It is better because the model was handed evidence.

That is the case for agent memory in production systems. Not a chatbot with a longer context window. A system that remembers specific incidents, cites them, learns from resolutions, and can be checked afterwards.

If you are building in this space, start with the receipt. Decide what a citation must contain, then design retention and retrieval backwards from it. The [Hindsight repository](https://github.com/vectorize-io/hindsight) is open source, and the [Vectorize primer on agent memory](https://vectorize.io/what-is-agent-memory) is a good place to pressure-test the model. Memory is only valuable when someone can verify it.
