# Demo video — shot-by-shot script

**Target:** 3:00 (hard limit 5:00). **Format:** 1920×1080, 30 fps, H.264, AAC.
**Voice:** calm, senior engineer. Not a pitch. Explaining something you built and trust.

---

## Before you hit record

- [ ] `python -m dejavu.seed --fresh` — exactly 34 incidents, 34 memories, no live ones
- [ ] Hindsight running; header badge reads **HINDSIGHT** (green), not `BM25 FALLBACK`
- [ ] Groq key set; badge reads **gpt-oss-120b**
- [ ] Band Desktop open on the second monitor (or a second window), room visible
- [ ] Browser at 100% zoom, 1920×1080, bookmarks bar hidden (`Ctrl+Shift+B`), one tab
- [ ] OS notifications off, Slack/Teams closed, taskbar auto-hide
- [ ] Mouse speed normal; move slowly, stop before clicking, click, then pause 1s
- [ ] Record at 1080p; do a 10-second test and listen back before the real take
- [ ] Read the voiceover out loud twice before recording

**Rule:** never scroll while talking. Scroll, stop, then speak.

---

## 0:00 — 0:14 · The hook

**On screen:** the app, idle. Alert queue empty. Slow push-in on the logo.

> "It's 3 a.m. Checkout is down. Somewhere in your company's history, this exact failure has already been solved — by someone who is asleep right now.
>
> The answer exists. Nobody can find it."

**Action:** press `D` — the SEV-1 alert drops into the queue.

---

## 0:14 — 0:28 · What this is

**On screen:** alert summary; signals row.

> "This is Déjà Vu. An on-call agent with long-term incident memory.
>
> Not a chatbot that read your runbooks. An agent that remembers what actually happened here — the fix, the engineer, the minutes it took, and whether it held."

**Action:** hover the signal chips, one slow pass. Do not click.

---

## 0:28 — 0:50 · Memory off

**Action:** click **Run without memory**. Wait for the card. Hold 3 seconds.

> "First, the same alert with memory switched off. This is a competent model with no history. It says: generic triage. Restart the pods. Watch the error rate.
>
> Thirty-one percent confidence. No incident, no owner, no fix time. If this is wrong, there is nothing to check afterwards."

**Action:** move the cursor to the red verdict line — *"No incident, no engineer, no fix time, no outcome."*

---

## 0:50 — 1:20 · Memory on

**Action:** click **Recall with memory**. Let the recall animation play in full. Do not talk over the first two lines; let the room see it.

> "Now the same alert, with memory."

**Wait for the hypothesis to appear, then hold 3 seconds before speaking.**

> "Missing composite index on `orders(created_at, status)`. Eighty-seven percent.
>
> And underneath it — receipts. Incident 1006, six minutes, Priya Raman, resolved. Incident 1001, same cause, resolved. Incident 1002, same class. Two out of two times this fixed it."

**Action:** scroll one notch so the receipts and timeline are centred.

> "Every claim is traceable to a real incident. That is the difference between a suggestion and evidence."

---

## 1:20 — 1:42 · The contradiction guard

**Action:** scroll to the amber card. Pause on it.

> "Here is the part that matters. Incident 1009 looks almost identical — same service, same pool timeout, fifty-three percent similarity. But it had a different cause: the pool size had been capped by a config rollout. The fix was different.
>
> A text search returns the nearest paragraph. Déjà Vu tells you what it ruled out, and why."

---

## 1:42 — 2:00 · The fingerprint and the plan

**Action:** scroll to the signal fingerprint; let it sit.

> "Signal by signal: what matches, what doesn't. The plan is built from the receipts — confirm the signature, apply the migration, watch pool wait. And a warning: a restart only masked this in 1009. It came back."

**Action:** scroll to the plan steps.

---

## 2:00 — 2:24 · Close the loop

**Action:** click **Resolve & retain**. Modal is pre-filled. Change nothing. Click **Retain this lesson**. Wait for the green toast.

> "We fixed it. Six minutes. And the lesson is now a memory — with my name on it."

**Action:** after the toast, the story fires the repeat alert automatically. If driving manually, press `S`. Let the second answer render.

> "Same fingerprint, forty minutes later. It answers instantly, and the first receipt is the incident we just created. That is the loop closing."

---

## 2:24 — 2:45 · The learning curve

**Action:** click the **Learning** tab. Hover one green point, then one red point.

> "This is not a claim, it's a measurement. A replay walks the whole corpus in order, and at each incident the agent may only use memories that existed before it.
>
> Thirty-three percent on the first six alerts. Eighty-three percent on the last six. Top-three, sixty-four percent. It got better because it remembered."

---

## 2:45 — 3:05 · Hindsight, and where the team lives

**Action:** click **Memory** tab; slow scroll of the cards. Then cut to the Band room with the agent's post visible.

> "The memory is Hindsight. A bank called `dejavu-oncall`. Every incident retained with its signals, cause, fix, outcome and responder — so recall is grounded, not generative.
>
> The answer also lands in Band, where the on-call team already is. The agent posts the hypothesis and the receipts into the room, so the human doesn't have to go looking."

---

## 3:05 — 3:18 · Close

**Action:** back to the Live tab, full answer on screen. Hold. End card.

> "Anyone can connect a model to a vector store. Déjà Vu remembers what happened, proves it, and gets better every time it's right.
>
> Repo and live demo in the description."

**End card (4s):** Déjà Vu · repo URL · live demo URL · `dejavu-oncall`

---

## Voiceover script (clean read, no timestamps)

> It's 3 a.m. Checkout is down. Somewhere in your company's history, this exact failure has already been solved — by someone who is asleep right now. The answer exists. Nobody can find it.
>
> This is Déjà Vu. An on-call agent with long-term incident memory. Not a chatbot that read your runbooks. An agent that remembers what actually happened here — the fix, the engineer, the minutes it took, and whether it held.
>
> First, the same alert with memory switched off. A competent model with no history. Generic triage. Restart the pods. Watch the error rate. Thirty-one percent confidence. No incident, no owner, no fix time. If this is wrong, there is nothing to check afterwards.
>
> Now the same alert, with memory. Missing composite index on orders, created-at and status. Eighty-seven percent. And underneath it — receipts. Incident 1006, six minutes, Priya Raman, resolved. Incident 1001, same cause. Incident 1002, same class. Two out of two times this fixed it. Every claim is traceable to a real incident. That is the difference between a suggestion and evidence.
>
> Here is the part that matters. Incident 1009 looks almost identical — same service, same pool timeout, fifty-three percent similarity. But it had a different cause: the pool size had been capped by a config rollout. The fix was different. A text search returns the nearest paragraph. Déjà Vu tells you what it ruled out, and why.
>
> Signal by signal: what matches, what doesn't. The plan is built from the receipts — confirm the signature, apply the migration, watch pool wait. And a warning: a restart only masked this in 1009. It came back.
>
> We fixed it. Six minutes. And the lesson is now a memory, with my name on it. Same fingerprint, forty minutes later — it answers instantly, and the first receipt is the incident we just created. That is the loop closing.
>
> This is not a claim, it's a measurement. A replay walks the whole corpus in order, and at each incident the agent may only use memories that existed before it. Thirty-three percent on the first six alerts. Eighty-three percent on the last six. Top-three, sixty-four percent. It got better because it remembered.
>
> The memory is Hindsight. A bank called dejavu-oncall. Every incident retained with its signals, cause, fix, outcome and responder — so recall is grounded, not generative. The answer also lands in Band, where the on-call team already is.
>
> Anyone can connect a model to a vector store. Déjà Vu remembers what happened, proves it, and gets better every time it's right.

---

## Edit notes

- Cut every pause longer than 0.8s between sentences, but keep 1.5s holds on the receipts and the contradiction card.
- Add a 40% zoom punch-in on the confidence ring and on `INC-1009` when mentioned.
- Subtitles burned in, 2 lines max, bottom-centre, 90% opacity box.
- No background music under speech. If you want music, keep it under −28 dB and only in transitions.
- Colour: leave the UI as recorded. Do not add filters; the orange accent is the brand.
- Export: 1080p, 8–12 Mbps, AAC 192 kbps. Filename `dejavu-demo.mp4`.

## If something fails on camera

| Failure | What to do |
|---|---|
| Badge says `BM25 FALLBACK` | Stop. Start Hindsight. Re-record. Do not explain it away on camera. |
| Groq is slow | Keep rolling — the template narrative still reads well. Do not mention the delay. |
| Story autopilot stalls | Press `S` again after 10s, or drive it manually: `D`, then click both buttons. |
| Wrong root cause on the demo alert | Do not fake it. Cut, restore the DB, re-record. |
