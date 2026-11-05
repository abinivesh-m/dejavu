# Social posts

Rules from the content guide, applied to every post below:

- No mention of a competition or event, anywhere.
- Under 800 characters.
- Hindsight named positively in the body.
- 3–5 hashtags on the last line only.
- No hashtags or links in the first two lines.
- Project link in the post body; Hindsight repo link in the first comment.

Replace `<REPO_URL>` with the public repository before publishing.

---

## 1 · Abinivesh M — the builder

Your on-call agent doesn't need a bigger model. It needs a memory.

I built Déjà Vu: an SRE agent that recalls your own incidents before it answers.

No memory → "restart the pods", 31% confidence, nothing to audit.
Hindsight memory → the missing composite index on orders(created_at,status), 87%, 3 receipts, 6 minutes, a named engineer.

The important part is what it rules out. A near-identical incident needed a different fix. The agent surfaces it, the one signal that separates them, and why it isn't this one.

Memory: one Hindsight bank, one document per incident — cause, fix, outcome, responder as metadata, so every claim is a receipt.

Replayed over 22 incidents with no future knowledge: 33% early, 83% late.

Repo: <REPO_URL>

#AIAgents #AgentMemory #Hindsight #LLM #SRE

---

## 2 · Abhinivesh K — the collaboration

The hardest part of on-call isn't the fix. It's finding the person who already did it.

Déjà Vu is an on-call agent that remembers every incident — the signals, the cause, the fix, the engineer, the minutes, and whether the fix held.

We run it as two agents in a Band room:

DejaVu-Recall posts the hypothesis and the receipts.
DejaVu-Critic answers the recall, not the alert, with four checks: two receipts, no stale precedent, fixes that held, confidence above threshold.

The critic can block the fix before a human ever sees it. That gate is the reason the room exists.

The answer lands where the team already is, with the evidence attached.

Memory: Hindsight. Coordination: Band.

Repo: <REPO_URL>

#AIAgents #AgentMemory #Hindsight #MultiAgent #SRE

---

## 3 · Mrittika S — the product angle

Most "AI for ops" tools give you a confident paragraph you can't check.

Déjà Vu gives you a hypothesis with receipts.

Incident ID. Root cause. Engineer. Fix time. Outcome. On every claim.

Then it does the thing I didn't expect: it shows the look-alike incident it rejected, and the signal that separates them. Two incidents can read identically and need opposite fixes. A text search returns the nearest paragraph. This tells you what it ruled out.

Behind it is Hindsight: a memory bank where each incident keeps its signals, fix and outcome, so recall is grounded rather than generated.

Replaying 22 incidents with no future knowledge: 33% accuracy early, 83% late. It improved because it remembered.

Repo: <REPO_URL>

#AIAgents #AgentMemory #Hindsight #AIMemory #SRE

---

## 4 · Harini E S — the human angle

Every on-call engineer has had this night: the alert looks familiar, the fix is somewhere in Slack, and the person who solved it is asleep.

Déjà Vu remembers for them.

It recalls the actual incident — the fix, the owner, how long it took, whether it held — and puts the evidence next to the answer instead of asking you to trust it.

It also remembers the failures. A fix that didn't hold gets demoted, not recommended again. Old memories get flagged for revalidation instead of pretending to be certain.

And when you resolve something at 3 a.m., it keeps that lesson for the next person.

The memory layer is Hindsight. The difference is not more confidence. It is more context.

Repo: <REPO_URL>

#AIAgents #AgentMemory #Hindsight #LLM #SRE

---

## First comment (every member)

> Here's Hindsight, the memory layer behind this: https://github.com/vectorize-io/hindsight
>
> Docs: https://hindsight.vectorize.io/

## Posting notes

- Article goes live first; put the article URL in the post body and the repo in the first comment, or repo in the body and Hindsight in the first comment — pick one and keep all four consistent.
- Post 9:30–11:00 IST on a Tuesday–Thursday, spaced 2–3 hours apart.
- Reply to every comment in the first 90 minutes.
- Image 1: the OFF/ON verdict strip. Image 2: the learning curve. Image 3: the Band room.
- Tag nothing student-related. No event tags, ever.
