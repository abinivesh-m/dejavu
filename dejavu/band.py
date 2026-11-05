"""Band bridge — put the answer where the on-call team already is.

Déjà Vu participates in a Band room as two agents:

* **DejaVu-Recall** posts the hypothesis, the receipts and the first action.
* **DejaVu-Critic** reviews it against the receipts and can **block** it.

That handoff is the point. Without the room, the critic never runs and a
single weak receipt ships straight to a human at 3 a.m. With the room, the
verdict is a decision two agents made in public, and the on-call engineer
approves or rejects it in the same thread.

Transport: Band Agent API (REST).

    POST {base}/api/v1/agent/chats/{chat}/events     tool calls, thoughts, verdicts
    POST {base}/api/v1/agent/chats/{chat}/messages   directed handoff (needs a mention)

Auth is the agent API key in ``X-API-Key``. Nothing here is required for the
app to work: with no credentials the same transcript is written to SQLite and
rendered in the UI as a *local preview*, clearly labelled.
"""
from __future__ import annotations

import json
import os
import time

import httpx

from . import db

BASE = os.getenv("BAND_API_URL", "https://app.band.ai").rstrip("/")
KEY = os.getenv("BAND_API_KEY") or ""
CHAT = os.getenv("BAND_CHAT_ID") or ""
CRITIC_KEY = os.getenv("BAND_CRITIC_API_KEY") or ""
HUMAN_ID = os.getenv("BAND_HUMAN_ID") or ""
AGENT_NAME = os.getenv("BAND_AGENT_NAME", "DejaVu-Recall")
CRITIC_NAME = os.getenv("BAND_CRITIC_NAME", "DejaVu-Critic")
TIMEOUT = float(os.getenv("BAND_TIMEOUT", "12"))


def configured() -> bool:
    return bool(KEY and CHAT)


def room() -> dict:
    return {
        "configured": configured(),
        "chat_id": CHAT or None,
        "agent": AGENT_NAME,
        "critic": CRITIC_NAME,
        "base": BASE,
    }


# ---------------------------------------------------------------- transport
def _post(path: str, payload: dict, api_key: str) -> tuple[bool, str, float]:
    t0 = time.perf_counter()
    try:
        r = httpx.post(
            f"{BASE}/api/v1/agent/chats/{CHAT}{path}",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code < 300:
            return True, f"{r.status_code}", ms
        return False, f"{r.status_code} {r.text[:220]}", ms
    except Exception as exc:  # network, DNS, timeout
        return False, str(exc)[:220], (time.perf_counter() - t0) * 1000


def post_event(body: str, kind: str = "thought", api_key: str | None = None) -> dict:
    """Events need no mention and are visible to every human in the room."""
    ok, detail, ms = _post(
        "/events",
        {"event": {"content": body, "kind": kind}},
        api_key or KEY or CRITIC_KEY,
    )
    return {"ok": ok, "detail": detail, "latency_ms": round(ms, 1), "kind": kind}


def post_message(body: str, mentions: list[str] | None = None, api_key: str | None = None) -> dict:
    """A directed message. Band requires at least one mention."""
    ok, detail, ms = _post(
        "/messages",
        {"message": {"content": body, "mentions": [{"id": m} for m in (mentions or [])]}},
        api_key or KEY,
    )
    return {"ok": ok, "detail": detail, "latency_ms": round(ms, 1), "kind": "message"}


# ------------------------------------------------------------------- critic
def critic(analysis: dict) -> dict:
    """Deterministic review. A block changes what the room does next.

    This is not a second LLM guessing. It checks the evidence the recall
    agent cited, which is exactly what a reviewer would do.
    """
    h = analysis.get("hypothesis") or {}
    evidence = analysis.get("evidence") or []
    support = int(h.get("support") or 0)
    conf = float(h.get("confidence") or 0)
    stale = [e for e in evidence if e.get("stale")]
    outcomes = [e.get("outcome") for e in evidence]
    failed = [e for e in evidence if e.get("outcome") not in ("resolved", None)]

    checks = [
        {
            "id": "receipts",
            "label": "at least two independent receipts",
            "pass": support >= 2,
            "value": f"{support} receipt{'s' if support != 1 else ''}",
        },
        {
            "id": "freshness",
            "label": "no stale precedent in the top receipts",
            "pass": not stale,
            "value": f"{len(stale)} stale" if stale else "all current",
        },
        {
            "id": "outcome",
            "label": "precedent fixes actually held",
            "pass": not failed,
            "value": f"{len(failed)} recurred" if failed else "all resolved",
        },
        {
            "id": "confidence",
            "label": "confidence above the action threshold",
            "pass": conf >= 0.65,
            "value": f"{round(conf * 100)}%",
        },
    ]

    hard_fail = support < 1 or (evidence and len(stale) == len(evidence)) or conf < 0.55
    soft_fail = any(not c["pass"] for c in checks)

    if hard_fail:
        verdict = "block"
        reason = "The recall is not backed by enough current precedent to act on."
    elif soft_fail:
        verdict = "review"
        reason = "Usable, but a human should confirm before applying the fix."
    else:
        verdict = "allow"
        reason = "Every claim is backed by two or more current, successful receipts."

    return {
        "verdict": verdict,
        "reason": reason,
        "checks": checks,
        "support": support,
        "confidence": round(conf, 2),
        "stale": len(stale),
        "recurred": len(failed),
        "outcomes": outcomes,
    }


# ----------------------------------------------------------------- dispatch
def _recall_body(analysis: dict) -> str:
    h = analysis.get("hypothesis") or {}
    ev = analysis.get("evidence") or []
    lines = [
        f"**{analysis.get('alert', {}).get('title', 'Alert')}** — {analysis.get('alert', {}).get('service', '')}",
        "",
        f"Hypothesis: **{h.get('title', 'unknown')}** ({round(float(h.get('confidence') or 0) * 100)}%)",
        f"First action: {analysis.get('first_action') or h.get('fix', '')}",
        "",
        "Receipts:",
    ]
    for e in ev[:4]:
        lines.append(
            f"• `{e.get('incident_id')}` {e.get('root_cause')} — "
            f"{e.get('outcome')} in {int(e.get('fix_minutes') or 0)} min by {e.get('engineer')}"
        )
    if analysis.get("contradiction"):
        cd = analysis["contradiction"]
        lines += ["", f"Ruled out `{cd.get('incident_id')}` — {cd.get('why_not')}"]
    return "\n".join(lines)


def _critic_body(review: dict) -> str:
    mark = {"allow": "ALLOW", "review": "REVIEW", "block": "BLOCKED"}[review["verdict"]]
    lines = [f"**{mark}** — {review['reason']}", ""]
    for c in review["checks"]:
        lines.append(f"{'✓' if c['pass'] else '✕'} {c['label']} ({c['value']})")
    return "\n".join(lines)


def dispatch(analysis: dict, alert_id: str) -> dict:
    """Write the room transcript, and post it to Band when configured.

    Always persisted so the UI can show the handoff. Never raises.
    """
    db.band_clear(alert_id)
    live = configured()
    log: list[dict] = []

    recall = _recall_body(analysis)
    review = critic(analysis)
    critic_text = _critic_body(review)

    def add(author: str, role: str, body: str, kind: str, key: str | None, mentions: list | None = None):
        res = {"ok": False, "detail": "local preview (no Band credentials)", "latency_ms": 0.0}
        if live:
            if kind == "message" and mentions:
                res = post_message(body, mentions=mentions, api_key=key)
            else:
                res = post_event(body, kind=kind if kind != "message" else "thought", api_key=key)
        db.band_add(alert_id, author, role, body, kind, mentions or [], res["ok"], res["detail"])
        log.append({"author": author, "role": role, "kind": kind, "delivered": res["ok"],
                    "detail": res["detail"], "latency_ms": res["latency_ms"]})
        return res

    add(AGENT_NAME, "recall", recall, "thought", KEY)

    # The critic answers the recall agent — this is the dependent handoff.
    add(CRITIC_NAME, "critic", critic_text, "tool_result", CRITIC_KEY or KEY)

    if review["verdict"] == "block":
        add(AGENT_NAME, "recall",
            "Blocked. Not escalating this fix. Re-collecting signals before the next attempt.",
            "thought", KEY)
    elif HUMAN_ID:
        add(AGENT_NAME, "recall",
            f"@{HUMAN_ID} {review['verdict'].upper()}. Approve the fix in this room and I will retain the lesson.",
            "message", KEY, mentions=[HUMAN_ID])

    return {
        "configured": live,
        "delivered": all(x["ok"] for x in log) if live else False,
        "transport": "band" if live else "local-preview",
        "review": review,
        "messages": db.band_for(alert_id),
        "log": log,
    }


def transcript(alert_id: str) -> dict:
    return {
        "room": room(),
        "messages": db.band_for(alert_id),
        "transport": "band" if configured() else "local-preview",
    }
