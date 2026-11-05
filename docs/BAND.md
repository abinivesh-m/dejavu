# Band: where the answer lands

Déjà Vu does not just compute an answer. It puts the answer in the room where
the on-call team already is, and it lets a second agent disagree with it
before a human sees it.

This is the part of the product that Band makes possible.

---

## The crew

| Agent | Owns | Runs as |
|---|---|---|
| **DejaVu-Recall** | Recalls precedent, states the hypothesis, cites receipts, names the first action | `BAND_API_KEY` |
| **DejaVu-Critic** | Reviews that recall against the receipts. Can **allow**, **review**, or **block** | `BAND_CRITIC_API_KEY` (falls back to the recall key) |
| **On-call engineer** | Approves or rejects the fix in the room. Owns the outcome | a human participant |

Two identities, not one process wearing two hats. Each has its own agent ID
and API key in Band, so each is a real participant in the room.

## The flow

```
Alert fires
  → DejaVu-Recall posts the hypothesis + receipts          (event)
  → DejaVu-Critic answers that post, not the alert          (dependent handoff)
      block   → Recall posts "not escalating", thread ends
      review  → human is asked to confirm
      allow   → Recall @mentions the on-call engineer
  → engineer approves → resolve → the lesson is retained
```

The critic's message is a reply to the recall, not a restatement of the alert.
If the critic blocks, the fix never reaches a human. **Remove the room and that
gate does not exist** — this is the delete test, answered.

## Why the critic is not decoration

It runs four deterministic checks against the evidence the recall agent cited:

| Check | Blocks when |
|---|---|
| At least two independent receipts | `support < 1` |
| No stale precedent in the top receipts | every receipt is stale |
| Precedent fixes actually held | every precedent recurred |
| Confidence above the action threshold | `confidence < 0.55` |

A `review` verdict means the answer is usable but a human should confirm.
An `allow` means every claim is backed by two or more current, successful
receipts. The verdict is shown in the UI next to the room transcript.

This is a real gate, not a status update: a blocked recall changes what the
room does next.

## Exactly what is sent

**Recall agent — event**

```
**Checkout p99 3.9s again, same pool signature** — checkout-api

Hypothesis: **Missing composite index on orders(created_at,status)** (97%)
First action: CREATE INDEX CONCURRENTLY idx_orders_created_status ...

Receipts:
• `INC-1006` Missing composite index on orders(created_at,status) — resolved in 6 min by Priya Raman
• `INC-1001` ... — resolved in 8 min by ...
• `INC-1002` ... — resolved in 11 min by ...

Ruled out `INC-1009` — the pool size was capped by a config rollout...
```

**Critic — event**

```
**ALLOW** — Every claim is backed by two or more current, successful receipts.

✓ at least two independent receipts (receipts)
✓ no stale precedent in the top receipts (all current)
✓ precedent fixes actually held (all resolved)
✓ confidence above the action threshold (97%)
```

**Handoff — message (only when `BAND_HUMAN_ID` is set)**

```
@<engineer> ALLOW. Approve the fix in this room and I will retain the lesson.
```

Band requires at least one mention on a message, which is why the directed
handoff is opt-in. Without a human ID the same text is posted as a visible
event, and the UI still shows the transcript.

## Setup

1. Create a free account at <https://app.band.ai>. No card.
2. **Agents → Remote Agent.** Create `DejaVu-Recall`. Copy the API key
   immediately (it is shown once) and the agent UUID.
3. Repeat for `DejaVu-Critic`, with its own key.
4. Create a room, add both agents **and yourself** as participants.
5. Copy the room id from the URL.
6. Fill in `.env`:

```bash
BAND_API_KEY=<recall key>
BAND_CRITIC_API_KEY=<critic key>
BAND_CHAT_ID=<room id>
BAND_HUMAN_ID=<your participant id>   # optional, enables the @mention
```

7. Restart the app. Fire an alert and run **Recall with memory**.
   The Band panel's transport badge changes from `local preview` to
   `delivered to Band`, and the messages appear in the room.

## Transport

Band Agent API, REST only — no WebSocket needed for this flow, because Déjà Vu
originates the messages rather than waiting to be mentioned.

```
POST https://app.band.ai/api/v1/agent/chats/{chat_id}/events
POST https://app.band.ai/api/v1/agent/chats/{chat_id}/messages
Header: X-API-Key: <agent api key>
```

`events` are informational and need no mention. `messages` are directed and
require at least one mention. Both are visible to every human in the room.

## Honesty

With no credentials the app does not pretend. It writes the identical
transcript to SQLite, renders it in the UI, and labels the transport
**local preview**. When keys are present the same transcript is posted for
real and the badge reads **delivered to Band**.

The answer is never blocked by Band being down: the bridge is wrapped so a
network failure degrades to the local preview and the analysis still returns.

## What to show in the demo

Record the Band console next to the app for ten seconds:

1. The recall post with the receipts.
2. The critic post with the four checks.
3. The verdict badge — green `ALLOW`.
4. Your own reply approving the fix.

That is the multi-agent collaboration made visible, not claimed.
