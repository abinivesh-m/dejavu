# Final Submission Pack — NexussForge

**Deadline: November 7, 2026, 11:59 PM.** One submission per team.

## Status board

| Form field | Status | Action |
|---|---|---|
| Email ID | Ready | `abinivesh.1203@gmail.com` |
| Phone Number | Ready | team leader enters |
| Team Name | Ready | `NexussForge` (code `e06cce29`) |
| Team Members | Ready | Abinivesh M, Abhinivesh K, Mrittika S, HARINI E S |
| GitHub Repository | **Ready** | https://github.com/abinivesh-m/dejavu |
| Social Media Post on LinkedIn | **Needs action** | publish post 1, paste URL |
| Article link | **Needs action** | publish the builder article, paste URL |
| Video Link | **Needs action** | record 2–5 min demo, upload to YouTube public |
| Reddit Post Link | **Needs action** | post article link to r/llmdevs or r/aiagents |
| Feedback | Ready | fill in honestly |

**Mandatory:** every member must complete the profile form:
https://forms.gle/BGcky3M6Nw1pBEPw6

**Submit here:** https://forms.gle/7eSw5Dz2oT2MhymX7

---

## Links to submit

- Live demo: https://dejavu-tau.vercel.app
- Judge tour (auto-runs the story): https://dejavu-tau.vercel.app/?tour=1
- GitHub repository: https://github.com/abinivesh-m/dejavu
- LinkedIn post: `[PASTE POST URL]`
- Article: `[PASTE ARTICLE URL]`
- Video: `[PASTE YOUTUBE URL]`
- Reddit: `[PASTE REDDIT URL]`

Required links inside every article:
- Hindsight GitHub: https://github.com/vectorize-io/hindsight
- Hindsight docs: https://hindsight.vectorize.io/
- Vectorize agent memory: https://vectorize.io/what-is-agent-memory

---

## What judges should see in 60 seconds

Open https://dejavu-tau.vercel.app/?tour=1 and let it run.

1. **Act 1** — SEV-1 on checkout-api at 02:14.
2. **Act 2** — memory off: "Generic triage", 31% confidence, restart the pods.
3. **Act 3** — Hindsight recall: the same fingerprint, the receipts, the engineer, the six-minute fix.
4. **Act 4** — resolve and retain: the lesson is written back with the responder's name.
5. **Act 5** — fire the repeat: the agent cites the incident it learned minutes ago, in milliseconds.

Then open **Memory** to show the bank, **Learning** for the replay curve (33% early → 83% late), and **Incidents** for the source records.

---

## 3-minute video plan

Record 1080p, terminal/editor font enlarged, notifications off. Screen + voice, conversational.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:20 | `dejavu-tau.vercel.app/?tour=1` hero | Who you are, one sentence: an on-call agent that remembers your incidents. |
| 0:20–0:50 | Memory OFF pane | "This is what every model does without memory: generic triage, restart pods, 31%." |
| 0:50–1:40 | Memory ON pane, receipts, fingerprint | Point at incident IDs, engineer, fix time, the contradiction guard. |
| 1:40–2:30 | Resolve modal → repeat alert | "The lesson is retained. Same fingerprint again — it answers from memory and cites the incident we just wrote." |
| 2:30–2:50 | Memory tab / bank counts | "One Hindsight bank, one document per incident, metadata on every memory." |
| 2:50–3:00 | Learning tab | "Replay with no future knowledge: 33% early, 83% late. That is the learning curve." |

Close with: "The model didn't get smarter. The team's memory did."

Upload to YouTube as **Public**, title: `Déjà Vu — the on-call agent that remembers every incident`. Use `docs/assets/thumbnail.png`.

---

## LinkedIn post (post 1)

Your on-call agent doesn't need a bigger model. It needs a memory.

I built Déjà Vu: an SRE agent that recalls your own incidents before it answers.

No memory → "restart the pods", 31% confidence, nothing to audit.
Hindsight memory → the missing composite index on orders(created_at,status), 97%, receipts, 6 minutes, an owner.

What matters is what it rules out. A near-identical incident needed a different fix. The agent surfaces it, the one signal that separates them, and why it isn't this one.

Memory: one Hindsight bank, one document per incident — cause, fix, outcome, responder as metadata, so every claim is a receipt.

Replayed 22 incidents blind: 33% early, 83% late.

Repo: [PASTE REPO URL]

#AIAgents #AgentMemory #Hindsight #LLM #SRE

**First comment:** Here's Hindsight if you want to check it out: https://github.com/vectorize-io/hindsight

---

## Reddit post

Subreddit: r/llmdevs (or r/aiagents, r/aimemory, r/sideproject)

Title: `I gave an on-call agent long-term incident memory. It started ruling out look-alike incidents.`

Body: 3–4 sentences on the problem, the before/after numbers (31% vs 97%, 33% → 83% replay), then the article link. Add the live demo and repo link in a comment, not the body, if the subreddit restricts self-promotion.

---

## Articles

Four drafts, one per member. Publish each on Dev.to, Hashnode, Medium, or LinkedIn Articles — public and linkable.

| Member | Draft | Words |
|---|---|---|
| Abinivesh M | `article.md` | 1455 |
| Abhinivesh K | `docs/articles/abhinivesh-k.md` | 831 |
| Mrittika S | `docs/articles/mrittika-s.md` | 918 |
| HARINI E S | `docs/articles/harini-e-s.md` | 944 |

Each includes the three required Hindsight links, a code snippet, and no event name.

---

## The one requirement still not proven

**Band AI Desktop.** The app has a two-agent Band room (`DejaVu-Recall` + `DejaVu-Critic`) and posts to Band when these env vars are set:

```
BAND_API_URL
BAND_API_KEY
BAND_CHAT_ID
BAND_CRITIC_API_KEY
```

They are not configured in production, so the room is simulated. Before submitting, either configure real Band credentials and capture a screenshot of the room, or remove the "we run it in Band" claim from the social post. Do not claim desktop usage without a screenshot.

---

## Pre-submit checklist

- [ ] All 4 members completed the profile form
- [ ] Public GitHub repo contains the full project (no `.env` files)
- [ ] 4 articles published, each with the 3 Hindsight links
- [ ] 4 LinkedIn posts published; Hindsight repo link in first comment
- [ ] 2–5 min YouTube video is Public and the link opens in incognito
- [ ] Reddit link post is live
- [ ] Live demo opens cold and `?tour=1` runs end to end
- [ ] Band evidence captured or the claim removed
- [ ] One team member submits the form before Nov 7, 11:59 PM
