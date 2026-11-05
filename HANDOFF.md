# Déjà Vu — Project Handoff

Everything below is the current state of the project as of the last commit. An AI agent taking over should read this first, then the files referenced.

## 1. What this project is

**Déjà Vu** — an on-call SRE agent with long-term incident memory. When a SEV-1 fires at 3 a.m., the agent recalls past incidents (root cause, fix, engineer, time, outcome), cites receipts, flags look-alikes via a contradiction guard, and visibly improves over time.

**Hackathon:** Hack With Bangalore 4.0 (team NexussForge, code e06cce29). Deadline 7 Nov 2026. Judging: Innovation 30%, Hindsight memory 25%, Technical 20%, UX 15%, Real-world impact 10%.

**Required tech:** Hindsight (memory) + Band AI desktop (collaboration). Groq recommended (openai/gpt-oss-120b).

**Location:** `C:\Users\abini\OneDrive\Desktop\DejaVu` (git repo, master branch, 5 commits).

**Live URLs:**
- Vercel (24/7, password-free): https://dejavu-tau.vercel.app (badge shows BM25 FALLBACK — needs Hindsight Cloud env vars for HINDSIGHT badge)
- Local tunnel (HINDSIGHT badge green): https://sweet-ideas-jam.loca.lt (password: 152.57.197.146)

## 2. Tech stack

- Python 3.14 (app) + Python 3.11 venv `.venv-hindsight` (Hindsight server)
- FastAPI + uvicorn (web)
- Hindsight (local server on port 8888, bank `dejavu-oncall`, 34 docs retained)
- Groq (openai/gpt-oss-120b) for narrative synthesis
- Ollama (qwen3:4b-instruct) as Hindsight's extraction model
- SQLite (operational mirror: incidents, memories, alerts, analyses, bus, band)
- Vanilla JS + CSS (4-tab UI: Live, Memory, Learning, Incidents)

## 3. File map

```
dejavu/
  agent.py       — alert → recall → rank → contradiction → plan → resolve/retain → replay
  memory.py      — Hindsight adapter, BM25 fallback, memory bus, stats, _enrich
  seed.py        — 34-incident synthetic corpus + failure-class map + memory_text
  db.py          — SQLite schema + helpers (incidents, memories, alerts, analyses, bus, band)
  web.py         — FastAPI routes (14 endpoints)
  config.py      — no-dep .env loader + paths
  band.py        — Band bridge (recall + critic + dispatch + transcript)
  __init__.py

static/
  index.html     — 4-tab UI shell
  style.css      — light editorial theme, glassmorphism, 3D hover, animations
  app.js         — UI logic: comparison, recall animation, receipts, replay chart, memory cards, band room

scripts/
  smoke.py       — end-to-end: off → on → resolve → repeat → replay
  verify.py      — 37-check verification (all pass)
  push_memories.py — retain all 34 incidents into Hindsight
  run.ps1        — one-command local run
  debug_rank.py  — single-incident ranking debugger

docs/
  ARCHITECTURE.md — data flow, ranking math, API surface
  DEMO_SCRIPT.md  — shot-by-shot video script + voiceover (3:18)
  ARTICLE.md      — 1,500-word article (no "hackathon", Hindsight links, code snippets)
  SOCIAL.md       — 4 LinkedIn posts (<800 chars, hashtags, Hindsight in body)
  BAND.md         — Band setup, API, screenshots guide
  SUBMISSION.md   — submission checklist + pitch

article.md       — copy of docs/ARTICLE.md at repo root
README.md        — product README, quickstart, Hindsight usage
Dockerfile       — container for Render/Vercel
render.yaml      — Render deploy config
vercel.json      — Vercel deploy config
api/index.py     — Vercel serverless entry point
.dockerignore, .vercelignore, .gitignore, .env.example, LICENSE, requirements.txt
```

## 4. Key numbers (verified)

- 34 incidents, 4 services (checkout-api, payments-api, auth-api, ledger-worker)
- 34 memories retained in Hindsight (100 memory units after extraction)
- Replay: 22 graded, top-1 50%, top-3 64%, early 33%, late 83%
- Memory off confidence: 31%, Memory on: 97%
- Memory recall latency: ~9s (Hindsight with local qwen3:4b-instruct)
- Resolve → retain → repeat: works, repeat cites the live incident first

## 5. How the memory works

1. **Bank**: `dejavu-oncall`, mission statement defines what matters.
2. **Retain**: one doc per incident with postmortem text + metadata (incident_id, service, root_cause, fix, outcome, fix_minutes, engineer, severity) + tags.
3. **Recall**: alert's signal fingerprint → Hindsight query → re-ranked by signal sim (50%) + text (45%) + coverage (5%), then support/outcome/recency, stale penalty -0.06.
4. **Contradiction guard**: if runner-up class has different root cause and is within 0.18 similarity, surface it with the discriminator and different fix.
5. **Closed loop**: resolve → retain with source=live → next matching alert cites the live incident.
6. **Replay**: chronological, only memories before each incident, no LLM, no future knowledge.

## 6. How Band works

- Two agents: DejaVu-Recall (posts hypothesis + receipts) and DejaVu-Critic (reviews recall, can block).
- Critic checks: ≥2 receipts, no stale precedent, precedent fixes held, confidence ≥0.55.
- Transport: Band Agent API (POST /events, /messages with X-API-Key).
- Without credentials: identical transcript renders in UI as "local preview".
- With keys: posted for real, badge shows "delivered to Band".

## 7. UI (light theme, 3D, interactive)

- 4 tabs: Live incident, Memory, Learning, Incidents
- Hero verdict card (off vs on comparison with confidence ring and time saved)
- Memory cards: one-line lesson (root cause → fix) + expandable details
- "What the bank has learned" summary (failure classes + counts)
- Signal fingerprint table (signal-by-signal comparison)
- Contradiction guard card (amber)
- Memory timeline strip
- Learning curve chart (SVG, hover tooltips)
- Memory bus (retain/recall trace)
- Band room (two-agent transcript + verdict)
- Keyboard shortcuts: 1-4 tabs, D demo, S story, M recall, R resolve, B bus
- Glassmorphism, 3D hover tilt, animated gradient background, floating particles, pulse animations

## 8. What's done

- [x] Backend: agent.py, memory.py, seed.py, db.py, web.py, config.py, band.py
- [x] 34-incident corpus with failure classes and discriminators
- [x] Hindsight integration (local server, 34 docs retained)
- [x] BM25 fallback
- [x] 4-tab UI with light theme, 3D effects, glassmorphism
- [x] Memory cards enriched (title, symptom, signals, root cause, fix, discriminator, outcome, time, engineer)
- [x] Band bridge (recall + critic + dispatch + transcript)
- [x] README, ARCHITECTURE, DEMO_SCRIPT, ARTICLE, SOCIAL, BAND, SUBMISSION docs
- [x] article.md at repo root (1,500 words)
- [x] requirements.txt, .env.example, LICENSE, Dockerfile, render.yaml, vercel.json
- [x] scripts: smoke.py, verify.py (37 checks, all pass), push_memories.py, run.ps1
- [x] Vercel deployment (https://dejavu-tau.vercel.app, password-free, 24/7)
- [x] Git committed (5 commits)

## 9. What's remaining (human tasks)

- [ ] Record demo video (script in docs/DEMO_SCRIPT.md)
- [ ] Publish article to Medium/Dev.to
- [ ] Post 4 LinkedIn posts (docs/SOCIAL.md)
- [ ] Submit to r/llmdevs / r/sideproject / r/aiagents / r/aimemory
- [ ] (Optional) Create Hindsight Cloud account for HINDSIGHT badge on Vercel
- [ ] (Optional) Install Band Desktop for the build-time coordination demo

## 10. How to run locally

```powershell
# 1. Start Hindsight (Python 3.11 venv)
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
$env:HINDSIGHT_API_LLM_PROVIDER="ollama"
$env:HINDSIGHT_API_LLM_MODEL="qwen3:4b-instruct"
$env:HINDSIGHT_API_LLM_BASE_URL="http://127.0.0.1:11434"
.\.venv-hindsight\Scripts\hindsight-api.exe --host 127.0.0.1 --port 8888

# 2. Start app (Python 3.14)
$env:PYTHONIOENCODING="utf-8"
python -m dejavu.seed --fresh
python -m scripts.push_memories
python -m dejavu.web --port 8011
# Open http://127.0.0.1:8011
```

## 11. Key files to read for context

1. `README.md` — product overview, quickstart, Hindsight usage
2. `docs/ARCHITECTURE.md` — data flow, ranking math, API surface
3. `dejavu/agent.py` — core logic (analyze, rank, resolve, replay)
4. `dejavu/memory.py` — Hindsight adapter + BM25 fallback
5. `dejavu/band.py` — Band bridge
6. `static/app.js` — UI logic
7. `static/style.css` — styling (light theme, 3D, glassmorphism)
8. `docs/DEMO_SCRIPT.md` — video script
9. `docs/SUBMISSION.md` — submission checklist + pitch

## 12. Live URLs

- Vercel (24/7, password-free): https://dejavu-tau.vercel.app
- Local tunnel (HINDSIGHT badge): https://sweet-ideas-jam.loca.lt (password: 152.57.197.146)

## 13. Verification

```bash
python -m scripts.verify   # 37/37 pass
python -m scripts.smoke    # end-to-end flow
```
