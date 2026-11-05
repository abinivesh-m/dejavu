# Submission pack

Everything the submission form asks for, with the answers already written.
Fill the four underlined links once the repo, video, article and demo are live.

---

## Links

| Field | Value |
|---|---|
| Team | **NexussForge** |
| Project | **Déjà Vu — the on-call agent that has seen this before** |
| GitHub | `<REPO_URL>` |
| Live demo | `<LIVE_URL>` |
| Demo video (YouTube, public, 1080p) | `<VIDEO_URL>` |
| Hindsight version | open source `v1.2.0`, local server, bank `dejavu-oncall` |

### Member content

| Member | Article | Social post |
|---|---|---|
| Abinivesh M | `<ARTICLE_URL>` | `<POST_URL>` |
| Abhinivesh K | `<ARTICLE_URL>` | `<POST_URL>` |
| Mrittika S | `<ARTICLE_URL>` | `<POST_URL>` |
| Harini E S | `<ARTICLE_URL>` | `<POST_URL>` |

One team video covers all four members.

---

## How Hindsight is used

**This is the answer the judges read first. Keep it at the top of the repo too.**

Déjà Vu is an on-call SRE agent. Every answer it gives is recalled from a
Hindsight memory bank, then re-ranked and cited. Without Hindsight the agent
falls back to generic triage; with it, the same alert resolves to a specific
root cause, a named engineer, a fix time and an outcome.

### One bank

`dejavu-oncall`, created with a mission statement that defines what the memory
is for:

> I am the long-term memory of an on-call SRE team at a payments company. I
> remember every incident, the signals that preceded it, the root cause, the
> fix that actually worked, how long it took, and when a fix failed.

### Retain — one structured document per incident

Every incident is retained with the postmortem text **and** metadata that
survives retrieval: `incident_id`, `service`, `root_cause`, `fix`, `outcome`,
`fix_minutes`, `engineer`, `severity`, plus tags for service, severity and
outcome. That metadata is what turns a recalled paragraph into a **receipt**.

Resolving a live alert calls `retain` again, with `source: live`. The lesson
from this session becomes the first receipt on the next matching alert.

### Recall — the alert fingerprint is the query

Service, title, body and every `key=value` signal are concatenated into the
recall query. Hindsight returns candidates by meaning; the application then
re-ranks them by signal similarity (50%), text (45%) and coverage (5%), with
support, outcome and recency as tie-breakers and a penalty for stale memory.

### Why this is central, not decorative

| Without memory | With Hindsight |
|---|---|
| "Restart the affected pods" | The missing composite index, by name |
| 31% confidence | 87% confidence |
| No incident, no owner, no hours | 3 receipts, Priya Raman, 6 minutes |
| Nothing to audit | Every claim links to an incident |
| Repeat at 09:41 gets the same generic answer | Repeat is answered in milliseconds from the incident just learned |

### Measured improvement

A replay walks the corpus in chronological order and only allows memories that
existed before each incident. 22 graded incidents, no LLM in the grading loop:

- top-1 **50%**, top-3 **64%**
- first six graded alerts **33%**
- last six graded alerts **83%**

The gap is the product. The agent improves because the bank grows.

### Honest failure mode

If the Hindsight server is unreachable, the app serves from a BM25 index over
the same SQLite mirror and the header badge changes from `HINDSIGHT` to
`BM25 FALLBACK`. The trace strip on every answer shows which path served it.

---

## How Band is used

Two Band agents, each with its own identity and API key:

- **DejaVu-Recall** posts the hypothesis, the receipts and the first action.
- **DejaVu-Critic** answers that recall — not the alert — with four checks and
  can **block** the fix before a human sees it.

Then a human approves in the room and the lesson is retained.

The delete test: remove the room and the critic never runs, so a single weak
receipt ships straight to a human at 3 a.m. The gate does not exist without
Band.

Transport: Band Agent API (`POST /api/v1/agent/chats/{id}/events` and
`/messages`). With no credentials the identical transcript is rendered in the
UI and labelled **local preview**; with keys it is posted for real and labelled
**delivered to Band**. Full detail in [BAND.md](BAND.md).

Band Desktop is used as the team's coordination surface during build: the
headless coding agents plan, implement and review in a shared room while the
team follows the plan, ownership and approvals in the desktop app.

---

## Submission checklist

### Repository

- [ ] Public, clean, no `.env`, no API keys in history
- [ ] `README.md` explains the problem, the demo, the metrics and the Hindsight usage
- [ ] `docs/ARCHITECTURE.md` with the data-flow diagram
- [ ] `docs/BAND.md` with setup and screenshots
- [ ] `article.md` at the repo root
- [ ] `LICENSE`
- [ ] `requirements.txt` and `.env.example`
- [ ] One-command run: `scripts/run.ps1`
- [ ] `python -m scripts.verify` passes

### Video

- [ ] 2–5 minutes, 1080p, screen recording + voiceover
- [ ] Shows memory OFF, then memory ON, on the same alert
- [ ] Shows the receipts, the contradiction guard and the learning curve
- [ ] Shows retain happening live and the repeat alert answered from memory
- [ ] Shows the Band room with both agents and a verdict
- [ ] Uploaded to YouTube as **public**, not a Drive link
- [ ] Header badge reads `HINDSIGHT`, not `BM25 FALLBACK`

### Content

- [ ] Everyone published their own article (800–1,500 words, public URL)
- [ ] Everyone published their own social post (<800 chars, 3–5 hashtags)
- [ ] No article or post mentions the event
- [ ] Every article links Hindsight GitHub, Hindsight docs and the Vectorize memory page
- [ ] Article link in the post; Hindsight repo link in the first comment
- [ ] Article submitted to r/llmdevs, r/sideproject, r/aiagents or r/aimemory

### Live demo

- [ ] Open on a fresh database, exactly 34 incidents and 34 memories
- [ ] `HINDSIGHT` badge green and `gpt-oss-120b` badge live
- [ ] Run the story end to end in under 60 seconds without a reload
- [ ] Every link opens in an incognito window

---

## The 30-second pitch (for the finale)

> Every on-call team already has the answer. It is in their own incident
> history — and at 3 a.m. nobody can find it.
>
> Déjà Vu is an on-call agent with a Hindsight memory bank. The same alert,
> answered twice: without memory it says "restart the pods" at 31%. With
> memory it names the missing index, cites three incidents, an engineer and
> six minutes, at 87% — and tells you which look-alike incident it ruled out
> and why.
>
> Then you resolve it, and the lesson is retained. Fire the same fingerprint
> again and it answers from the incident you just closed.
>
> We measured it: 33% on the first six alerts, 83% on the last six. It got
> better because it remembered.
