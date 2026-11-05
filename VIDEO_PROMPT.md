# Déjà Vu — AI Video Generation Prompt (for Sora / Veo / Runway / Pika)

Paste the block below into your AI video generator. It produces a 3-minute
1080p screen-recorded-style demo with voiceover, in the style of the
PayerLine / Lifeline AI winning demos.

---

## PROMPT (copy everything between the lines)

```
Create a 3-minute 1080p demo video for "Déjà Vu", an on-call SRE agent with
long-term incident memory powered by Hindsight. Style: screen recording of a
web app with calm senior-engineer voiceover, no music, no logo sting, no
clickbait. Tone: technical, credible, slightly opinionated. Dark-to-light
editorial UI with orange accent #ff5c1a.

SCENE 1 (0:00-0:14) — THE HOOK
Visual: idle web app, alert queue empty, slow push-in on the logo "Déjà Vu".
Voiceover: "It's 3 a.m. Checkout is down. Somewhere in your company's
history, this exact failure has already been solved — by someone who is
asleep right now. The answer exists. Nobody can find it."

SCENE 2 (0:14-0:28) — WHAT THIS IS
Visual: a SEV-1 alert drops into the queue. Alert summary with signals:
p99_ms=3900, pool_wait_ms=1240, db_cpu_pct=91, err_pct=4.
Voiceover: "This is Déjà Vu. An on-call agent with long-term incident
memory. Not a chatbot that read your runbooks. An agent that remembers
what actually happened here — the fix, the engineer, the minutes it took,
and whether it held."

SCENE 3 (0:28-0:50) — MEMORY OFF
Visual: click "Run without memory". Card appears: "Generic triage for
checkout-api", 31% confidence, no receipts, no owner. Red verdict line:
"No incident, no engineer, no fix time, no outcome."
Voiceover: "First, the same alert with memory switched off. A competent
model with no history. Generic triage. Restart the pods. Watch the error
rate. Thirty-one percent confidence. No incident, no owner, no fix time. If
this is wrong, there is nothing to check afterwards."

SCENE 4 (0:50-1:20) — MEMORY ON
Visual: click "Recall with memory". Animated recall steps play:
"encoding the alert signature", "hindsight.recall(bank=dejavu-oncall)",
"reranking by signal fingerprint + outcome", "synthesising the narrative".
Then hypothesis appears: "Missing composite index on
orders(created_at,status)", 97% confidence, confidence ring fills.
Receipts appear: INC-1006 (6 min, Priya Raman, resolved), INC-1001 (resolved),
INC-1002 (resolved). Timeline strip shows incidents over time.
Voiceover: "Now the same alert, with memory. Missing composite index on
orders, created-at and status. Eighty-seven percent. And underneath it —
receipts. Incident 1006, six minutes, Priya Raman, resolved. Incident 1001,
same cause. Incident 1002, same class. Two out of two times this fixed it.
Every claim is traceable to a real incident."

SCENE 5 (1:20-1:42) — CONTRADICTION GUARD
Visual: scroll to amber card. "INC-1009 looks almost identical — same
service, same pool timeout, 53% similarity — but it had a different cause:
the pool size was capped by a config rollout. The fix was different."
Voiceover: "Here is the part that matters. Incident 1009 looks almost
identical. But it had a different cause: the pool size had been capped by
a config rollout. The fix was different. A text search returns the nearest
paragraph. Déjà Vu tells you what it ruled out, and why."

SCENE 6 (1:42-2:00) — FINGERPRINT + PLAN
Visual: signal fingerprint table (p99_ms 3900 vs 3800, pool_wait_ms 1240
vs 1180, db_cpu_pct 91 vs 88, cert_age_days 2 vs 61). Plan steps:
"confirm the signature", "apply the migration", "watch pool wait". Avoid
card: "a restart only masked this in 1009. It came back."
Voiceover: "Signal by signal: what matches, what doesn't. The plan is built
from the receipts. And a warning: a restart only masked this in 1009. It
came back."

SCENE 7 (2:00-2:24) — CLOSE THE LOOP
Visual: click "Resolve & retain". Modal pre-filled. Click "Retain this
lesson". Green toast: "Retained INC-LIVE-...". Then the repeat alert fires
automatically. Second answer renders instantly, first receipt is the
incident just created.
Voiceover: "We fixed it. Six minutes. And the lesson is now a memory, with
my name on it. Same fingerprint, forty minutes later — it answers instantly,
and the first receipt is the incident we just created. That is the loop
closing."

SCENE 8 (2:24-2:45) — LEARNING CURVE
Visual: click "Learning" tab. Chart shows cumulative accuracy rising from
33% to 83%. Hover one green point, then one red point.
Voiceover: "This is not a claim, it's a measurement. A replay walks the
whole corpus in order, and at each incident the agent may only use memories
that existed before it. Thirty-three percent on the first six alerts.
Eighty-three percent on the last six. Top-three, sixty-four percent. It got
better because it remembered."

SCENE 9 (2:45-3:05) — HINDSIGHT + BAND
Visual: click "Memory" tab, slow scroll of cards. Cut to Band room with the
agent's post visible: DejaVu-Recall posts hypothesis + receipts,
DejaVu-Critic posts ALLOW with 4 checks.
Voiceover: "The memory is Hindsight. A bank called dejavu-oncall. Every
incident retained with its signals, cause, fix, outcome and responder — so
recall is grounded, not generative. The answer also lands in Band, where
the on-call team already is."

SCENE 10 (3:05-3:18) — CLOSE
Visual: back to Live tab, full answer on screen. Hold 4 seconds. End card:
"Déjà Vu · repo URL · live demo URL · dejavu-oncall".
Voiceover: "Anyone can connect a model to a vector store. Déjà Vu remembers
what happened, proves it, and gets better every time it's right. Repo and
live demo in the description."

END CARD (4s): Déjà Vu · https://dejavu-tau.vercel.app · dejavu-oncall
```

## Edit notes
- Cut every pause longer than 0.8s between sentences, keep 1.5s holds on receipts and contradiction card.
- Add 40% zoom punch-in on the confidence ring and on INC-1009 when mentioned.
- Burned-in subtitles, 2 lines max, bottom-centre, 90% opacity box.
- No background music under speech. If music, keep under -28 dB, only in transitions.
- Leave the UI as recorded. Do not add filters; the orange accent is the brand.
- Export: 1080p, 8-12 Mbps, AAC 192 kbps. Filename: dejavu-demo.mp4.

## If something fails on camera
| Failure | What to do |
|---|---|
| Badge says BM25 FALLBACK | Stop. Start Hindsight. Re-record. Do not explain it away. |
| Groq is slow | Keep rolling — template narrative still reads well. Don't mention the delay. |
| Story autopilot stalls | Press S again after 10s, or drive manually: D, then click both buttons. |
| Wrong root cause on demo alert | Do not fake it. Cut, restore DB, re-record. |

## Thumbnail prompt (for Nano Banana)
"Generate a viral thumbnail for this YouTube video. Make it attention
grabbing. Aspect ratio 16:9. Show a dark-to-light split: left side a
generic 'restart the pods' alert, right side a specific database index
migration with 3 receipt cards. Orange accent #ff5c1a. Text overlay:
'Remembered in 6 minutes'."

## Video titles (pick one)
1. Your On-Call Agent Needs Hindsight, Not a Bigger Model
2. I Gave an On-Call Agent Hindsight. Here's What It Recalled.
3. Hindsight Turned My Incident Bot Into an On-Call Colleague
4. The On-Call Agent That Remembers What Broke Last Time
5. 33% to 83%: How Memory Made My SRE Agent Smarter

---

## Live URLs
- 24/7 password-free: https://dejavu-tau.vercel.app
- Local (HINDSIGHT badge green): https://sweet-ideas-jam.loca.lt (password: 152.57.197.146)
- GitHub: (push to public repo and add URL here)

## Files to read for context
1. HANDOFF.md — full project state
2. README.md — product overview
3. docs/DEMO_SCRIPT.md — detailed shot-by-shot script
4. docs/ARCHITECTURE.md — data flow, ranking math
5. dejavu/agent.py — core logic
6. static/app.js + static/style.css — UI

## Verification
python -m scripts.verify → 37/37 pass
