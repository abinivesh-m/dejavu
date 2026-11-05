"""The agent: alert -> recall -> ranked hypothesis -> resolve -> retain."""
from __future__ import annotations

import json
import math
import os
import random
import re
import time
import uuid
from datetime import datetime, timezone

import httpx

from . import config  # noqa: F401  (loads .env)
from . import db, memory

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


# --------------------------------------------------------------------------- #
# Groq
# --------------------------------------------------------------------------- #
def groq_available() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def groq_json(system: str, user: str, max_tokens: int = 900) -> dict | None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    try:
        r = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "temperature": 0.2,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=15.0,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
        return json.loads(raw)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# alerts
# --------------------------------------------------------------------------- #
DEMO_SIGNALS = {
    "p99_ms": 4200, "err_pct": 12, "pool_wait_ms": 3400, "db_cpu_pct": 62,
    "deploy_min_ago": 14, "req_multiplier": 1.0, "error": "connection timeout acquiring pool",
}

DEMO_ALERT = {
    "service": "checkout-api",
    "title": "Checkout p99 4.2s, 5xx climbing",
    "severity": "SEV-1",
    "body": (
        "p99 4.2s over the last 5 minutes (baseline 380ms). 5xx at 12%. "
        "Connection pool wait 3.4s. DB CPU 62%. Deploy v2.31 at 14:02 added an "
        "order status filter to the checkout query. Error signature: connection "
        "timeout acquiring pool."
    ),
    "signals": DEMO_SIGNALS,
}

REPEAT_SIGNALS = {**DEMO_SIGNALS, "p99_ms": 3900, "err_pct": 9, "pool_wait_ms": 3100, "db_cpu_pct": 58}
REPEAT_ALERT = {
    "service": "checkout-api",
    "title": "Checkout p99 3.9s again, same pool signature",
    "severity": "SEV-2",
    "body": (
        "p99 3.9s (baseline 380ms). 5xx at 9%. Pool wait 3.1s. DB CPU 58%. "
        "Deploy v2.34 at 09:41 touched the orders query path. Same signature: "
        "connection timeout acquiring pool."
    ),
    "signals": REPEAT_SIGNALS,
}


def create_alert(scenario: str = "demo") -> dict:
    if scenario == "demo":
        base = DEMO_ALERT
    elif scenario == "repeat":
        base = REPEAT_ALERT
    else:
        with db.connect() as con:
            row = con.execute("SELECT * FROM incidents ORDER BY RANDOM() LIMIT 1").fetchone()
        inc = dict(row)
        sig = json.loads(inc["signals"])
        base = {
            "service": inc["service"],
            "title": inc["title"],
            "severity": inc["severity"],
            "body": inc["symptom"],
            "signals": sig,
        }
    aid = f"ALT-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:3]}"
    with db.connect() as con:
        con.execute(
            "INSERT INTO alerts (id,ts,service,title,severity,body,signals,status) VALUES (?,?,?,?,?,?,?,?)",
            (aid, db.now_iso(), base["service"], base["title"], base["severity"], base["body"],
             json.dumps(base["signals"]), "open"),
        )
    return get_alert(aid)


def get_alert(aid: str) -> dict:
    with db.connect() as con:
        row = con.execute("SELECT * FROM alerts WHERE id=?", (aid,)).fetchone()
    if not row:
        raise KeyError(aid)
    a = dict(row)
    a["signals"] = db.json_load(a["signals"])
    return a


def list_alerts(limit: int = 20) -> list[dict]:
    with db.connect() as con:
        rows = con.execute("SELECT * FROM alerts ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        a = dict(r)
        a["signals"] = db.json_load(a["signals"])
        out.append(a)
    return out


# --------------------------------------------------------------------------- #
# query building
# --------------------------------------------------------------------------- #
def build_query(alert: dict) -> str:
    sig = " ".join(f"{k}={v}" for k, v in alert.get("signals", {}).items())
    return f"{alert['service']} {alert['title']} {alert['body']} {sig}"


# --------------------------------------------------------------------------- #
# ranking
# --------------------------------------------------------------------------- #
def _signal_similarity(alert_sig: dict, mem_sig: dict) -> tuple[float, float]:
    """How close two signal fingerprints are, and how much of the alert they cover."""
    if not alert_sig or not mem_sig:
        return 0.0, 0.0
    shared = [k for k in alert_sig if k in mem_sig]
    if not shared:
        return 0.0, 0.0
    total_w = 0.0
    hit_w = 0.0
    for k in shared:
        w = SIGNAL_WEIGHTS.get(k, 0.6)
        total_w += w
        a, b = alert_sig[k], mem_sig[k]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            denom = max(abs(float(a)), abs(float(b)), 1e-9)
            hit_w += w * (1.0 - min(1.0, abs(float(a) - float(b)) / denom))
        else:
            hit_w += w * (1.0 if str(a) == str(b) else 0.0)
    alert_w = sum(SIGNAL_WEIGHTS.get(k, 0.6) for k in alert_sig) or 1.0
    return (hit_w / total_w if total_w else 0.0), (total_w / alert_w)


SIGNAL_WEIGHTS = {
    # discriminating signals carry more weight than generic ones
    "cert_age_days": 2.0, "dns_ttl_s": 2.0, "clock_skew_s": 2.0, "pool_size": 2.0,
    "tls_errors": 1.8, "jwks_calls_per_req": 1.8, "consumer_lag": 1.6, "rebalance_s": 1.4,
    "long_query_s": 1.6, "cache_ttl_s": 1.5, "scope": 1.5, "psp_status": 1.5,
    "duplicates": 1.5, "lock_wait_ms": 1.5, "thread_pool_pct": 1.4, "pool_wait_ms": 1.3,
    "deploy_min_ago": 1.1, "req_multiplier": 1.1, "cache_hit_pct": 1.2, "redis_evictions": 1.2,
    "gc_pause_ms": 1.2, "heap_pct": 1.3, "batch_size": 1.2, "lag_min": 1.1,
    "db_cpu_pct": 0.8, "p99_ms": 0.8, "err_pct": 1.0,
}


def _age_days(ts: str) -> float:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
    except Exception:
        return 0.0


def rank(hits: list[dict], alert_signals: dict | None = None) -> list[dict]:
    """Group recalled incidents by root cause and score them.

    similarity = 50% signal fingerprint + 45% text recall + 5% signal coverage
    final      = similarity, then support / outcome / recency as tie-breakers.
    """
    groups: dict[str, list[dict]] = {}
    for h in hits:
        groups.setdefault(h.get("cause_class") or h["root_cause"], []).append(h)
    ranked = []
    for cls, hs in groups.items():
        best_hit = max(hs, key=lambda h: h["score"])
        sig_sim = 0.0
        cov = 0.0
        if alert_signals:
            pairs = [_signal_similarity(alert_signals, h.get("signals") or {}) for h in hs]
            sig_sim = max(p[0] for p in pairs)
            cov = max(p[1] for p in pairs)
        text_sim = best_hit["score"]
        similarity = 0.50 * sig_sim + 0.45 * text_sim + 0.05 * cov if alert_signals else text_sim
        support = len(hs)
        succ = sum(h["success_count"] for h in hs)
        fail = sum(h["fail_count"] for h in hs)
        rate = succ / (succ + fail) if (succ + fail) else 0.5
        age = min(_age_days(h["created_at"]) for h in hs)
        recency = math.exp(-age / 120)
        stale = any(h["stale"] for h in hs)
        score = 0.82 * similarity + 0.10 * min(1.0, support / 3) + 0.08 * rate
        score += 0.02 * recency
        if stale:
            score -= 0.06
        best = max(hs, key=lambda h: (h["score"], h["created_at"]))
        ranked.append({
            "root_cause": best["root_cause"],
            "cause_class": cls,
            "score": round(min(1.0, score), 3),
            "similarity": round(min(1.0, similarity), 3),
            "signal_similarity": round(sig_sim, 3),
            "text_similarity": round(text_sim, 3),
            "coverage": round(cov, 3),
            "support": support,
            "success_rate": round(rate, 3),
            "age_days": round(age, 1),
            "stale": stale,
            "best": best,
            "hits": sorted(hs, key=lambda h: -h["score"]),
            "fix": best["fix"],
            "fix_minutes": best["fix_minutes"],
            "engineer": best["engineer"],
        })
    ranked.sort(key=lambda g: -g["score"])
    return ranked


def _actions(alert: dict, top: dict, second: dict | None) -> list[dict]:
    inc = db.get_incident(top["best"]["incident_id"]) or {}
    disc = inc.get("discriminator", "")
    out = [
        {"step": f"Confirm the signature: {alert['service']} pool wait is elevated and DB CPU is moderate, not saturated.",
         "why": disc or "This separates resource exhaustion from an overloaded database.",
         "source": top["best"]["incident_id"]},
        {"step": top["fix"],
         "why": f"Same fix worked in {top['best']['incident_id']} and resolved it in {top['fix_minutes']:.0f} minutes.",
         "source": top["best"]["incident_id"]},
        {"step": "Watch pool wait and 5xx for 10 minutes; if pool wait stays above 1s, escalate to the DB on-call.",
         "why": "Recovery is measured on pool wait, not on pod restarts.",
         "source": top["best"]["incident_id"]},
    ]
    if second and second["root_cause"] != top["root_cause"]:
        out.append({
            "step": f"Rule out: {second['root_cause']}",
            "why": f"It also matches the symptoms ({second['similarity']:.2f} similarity) but its fix is different: {second['fix']}",
            "source": second["best"]["incident_id"],
        })
    return out


def _avoid(ranked: list[dict], top: dict) -> list[str]:
    out = []
    for g in ranked:
        if g is top:
            continue
        for h in g["hits"]:
            if h["outcome"] in ("recurred", "made_it_worse"):
                out.append(
                    f"{h['fix']} only masked it in {h['incident_id']} - the incident came back. "
                    f"Treat that as a temporary mitigation, not the fix."
                )
    return out[:2]


def _generic(alert: dict) -> dict:
    """The 'memory off' baseline: a competent but generic playbook."""
    sig = alert.get("signals", {})
    return {
        "hypothesis": {
            "title": f"Generic triage for {alert['service']}",
            "cause_class": "",
            "confidence": 0.31,
            "support": 0,
            "success_rate": 0.0,
            "fix": "Restart the affected pods and watch the error rate",
            "fix_minutes": 0,
            "engineer": "none",
        },
        "title": f"Investigate {alert['service']} latency and errors",
        "confidence": 0.31,
        "narrative": (
            "No prior incidents are available for this service. Start with the standard "
            "triage path: check recent deploys, restart unhealthy pods, and watch the "
            "error rate. This is generic guidance - it is not grounded in what happened "
            "here before."
        ),
        "actions": [
            {"step": "Check the deploy dashboard and roll back the most recent change if it correlates.",
             "why": "Deploys are the most common cause of latency regressions.", "source": "generic"},
            {"step": "Restart the affected pods and watch error rate for 5 minutes.",
             "why": "Clears transient connection and memory pressure.", "source": "generic"},
            {"step": "If errors persist, check database health and connection pool settings.",
             "why": "Saturation shows up as elevated latency.", "source": "generic"},
        ],
        "avoid": [],
        "evidence": [],
        "contradiction": None,
        "receipts": [],
        "signals_used": list(sig.keys()),
    }


# --------------------------------------------------------------------------- #
# analyze
# --------------------------------------------------------------------------- #
def analyze(alert_id: str, mode: str = "on") -> dict:
    t0 = time.perf_counter()
    alert = get_alert(alert_id)
    trace = [{"step": "alert", "label": f"{alert['severity']} received from {alert['service']}", "ms": 0.0}]

    if mode == "off":
        payload = _generic(alert)
        payload.update({
            "alert": alert, "mode": "off", "backend": "none", "memory_latency_ms": 0.0,
            "llm": False, "trace": trace,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        })
        _store(alert_id, payload)
        return payload

    query = build_query(alert)
    t1 = time.perf_counter()
    mem = memory.recall(query, k=10, service=alert["service"])
    mem_ms = (time.perf_counter() - t1) * 1000
    trace.append({"step": "recall", "label": f"recall({memory.BANK}) -> {len(mem['hits'])} memories", "ms": round(mem_ms, 1)})

    ranked = rank(mem["hits"], alert.get("signals"))
    if not ranked:
        payload = _generic(alert)
        payload.update({"alert": alert, "mode": "on", "backend": mem["backend"], "trace": trace,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 1), "llm": False,
                        "memory_latency_ms": round(mem_ms, 1)})
        _store(alert_id, payload)
        return payload

    top = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    contradiction = None
    if second and second["root_cause"] != top["root_cause"] and (top["similarity"] - second["similarity"]) < 0.18:
        alt = db.get_incident(second["best"]["incident_id"]) or {}
        contradiction = {
            "root_cause": second["root_cause"],
            "incident_id": second["best"]["incident_id"],
            "similarity": second["similarity"],
            "why_not": alt.get("discriminator") or "The signals differ in one decisive way.",
            "different_fix": second["fix"],
        }

    confidence = max(0.42, min(0.97, 0.5 + 0.42 * top["similarity"] + 0.08 * top["success_rate"]))
    if top["stale"]:
        confidence -= 0.05

    evidence = []
    alert_sig = alert.get("signals") or {}
    for h in top["hits"][:3] + ([second["best"]] if second and second["root_cause"] != top["root_cause"] else []):
        inc = db.get_incident(h["incident_id"]) or {}
        e_sig, e_cov = _signal_similarity(alert_sig, h.get("signals") or {})
        e_sim = (0.50 * e_sig + 0.45 * h["score"] + 0.05 * e_cov) if alert_sig else h["score"]
        evidence.append({
            "incident_id": h["incident_id"], "ts": h["created_at"], "service": h["service"],
            "root_cause": h["root_cause"], "fix": h["fix"], "fix_minutes": h["fix_minutes"],
            "engineer": h["engineer"], "outcome": h["outcome"], "similarity": round(e_sim, 3),
            "stale": h["stale"], "title": inc.get("title", ""), "severity": inc.get("severity", ""),
            "discriminator": inc.get("discriminator", ""),
        })

    actions = _actions(alert, top, second)
    avoid = _avoid(ranked, top)

    tbl = {
        "root": top["root_cause"], "evidence": evidence, "contradiction": contradiction,
        "support": top["support"], "success_rate": top["success_rate"],
    }
    t2 = time.perf_counter()
    llm = _llm_narrative(alert, tbl)
    llm_ms = (time.perf_counter() - t2) * 1000
    trace.append({"step": "sythesize", "label": "Groq gpt-oss-120b grounded narrative" if llm else "template fallback", "ms": round(llm_ms, 1)})

    narrative = (llm or {}).get("narrative") or (
        f"This matches {top['root_cause'].lower()} ({top['support']} prior incident"
        f"{'s' if top['support'] > 1 else ''}, {top['success_rate']*100:.0f}% resolution rate). "
        f"Most recently {top['best']['incident_id']} fixed it with: {top['fix']} "
        f"({top['fix_minutes']:.0f} min)."
    )

    payload = {
        "alert": alert, "mode": "on", "backend": mem["backend"], "query": query,
        "hypothesis": {
            "title": top["root_cause"], "cause_class": top["cause_class"],
            "confidence": round(confidence, 2),
            "support": top["support"], "success_rate": top["success_rate"],
            "fix": top["fix"], "fix_minutes": top["fix_minutes"], "engineer": top["engineer"],
        },
        "narrative": narrative,
        "first_action": (llm or {}).get("first_action") or top["fix"],
        "why": (llm or {}).get("why") or [],
        "actions": actions, "avoid": avoid, "evidence": evidence,
        "contradiction": contradiction,
        "receipts": [h for h in mem["hits"]],
        "memory_latency_ms": round(mem_ms, 1),
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "llm": bool(llm), "llm_ms": round(llm_ms, 1), "trace": trace,
        "memory_backend": mem["backend"], "memory_detail": mem.get("detail", ""),
    }
    _store(alert_id, payload)
    return payload


def _llm_narrative(alert: dict, table: dict) -> dict | None:
    system = (
        "You are Deja Vu, an on-call incident agent. You are given an alert and the "
        "prior incidents recalled from memory. Write like a senior SRE: concrete, calm, "
        "no filler, never invent facts that are not in the evidence. Return JSON with "
        "keys: narrative (<=80 words, cite incident IDs inline), first_action (one "
        "imperative sentence), why (array of exactly 3 short strings, each tied to an "
        "incident ID or a signal). If the evidence is weak, say so."
    )
    user = json.dumps({"alert": {k: alert[k] for k in ("service", "title", "severity", "body", "signals")},
                       "recalled": table}, default=str)
    out = groq_json(system, user)
    if not out or "narrative" not in out:
        return None
    if not isinstance(out.get("why"), list):
        out["why"] = []
    return out


def _store(alert_id: str, payload: dict) -> None:
    with db.connect() as con:
        con.execute(
            "INSERT INTO analyses (alert_id,mode,top_incident,correct,latency_ms,payload,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (alert_id, payload["mode"], (payload.get("hypothesis") or {}).get("title"),
             None, payload["latency_ms"], json.dumps(payload), db.now_iso()),
        )


# --------------------------------------------------------------------------- #
# resolve -> retain
# --------------------------------------------------------------------------- #
def resolve(alert_id: str, root_cause: str, fix: str, engineer: str = "On-call",
            minutes: float = 6.0, outcome: str = "resolved", cause_class: str = "") -> dict:
    alert = get_alert(alert_id)
    iid = f"INC-LIVE-{datetime.now().strftime('%m%d%H%M')}"
    ts = db.now_iso()
    signals = alert.get("signals", {})
    inc = {
        "id": iid, "ts": ts, "service": alert["service"], "title": alert["title"],
        "severity": alert["severity"], "symptom": alert["body"], "signals": signals,
        "root_cause": root_cause, "cause_class": cause_class or root_cause,
        "fix": fix, "fix_minutes": minutes, "outcome": outcome,
        "engineer": engineer,
        "discriminator": "Confirmed by the responder on this alert; the recalled signal signature matched.",
    }
    text = (
        f"INCIDENT {iid} | {ts[:10]} | {alert['service']} | {alert['severity']}\n"
        f"TITLE: {alert['title']}\n"
        f"SYMPTOM: {alert['body']}\n"
        f"SIGNALS: {', '.join(f'{k}={v}' for k, v in signals.items())}\n"
        f"ROOT CAUSE: {root_cause}\nFIX: {fix}\n"
        f"RESOLUTION TIME: {minutes:.0f} minutes\nOUTCOME: {outcome}\n"
        f"RESPONDER: {engineer}\n"
        f"DISCRIMINATOR: Confirmed live on {ts[:10]} after the agent recalled the matching pattern."
    )
    with db.connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO incidents (id,ts,service,title,severity,symptom,signals,root_cause,"
            "cause_class,fix,fix_minutes,outcome,engineer,tags,discriminator,postmortem) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (iid, ts, inc["service"], inc["title"], inc["severity"], inc["symptom"],
             json.dumps(signals), root_cause, inc["cause_class"], fix, minutes, outcome, engineer,
             json.dumps(["live"]), inc["discriminator"], text),
        )
        con.execute("UPDATE alerts SET status='resolved', matched_incident=?, resolved_by=? WHERE id=?",
                    (iid, engineer, alert_id))
    receipt = memory.retain(inc, text, source="live", incident_id=iid)
    return {"incident_id": iid, "memory": receipt, "alert_id": alert_id, "outcome": outcome}


# --------------------------------------------------------------------------- #
# learning curve (replay over the seeded corpus)
# --------------------------------------------------------------------------- #
def replay() -> dict:
    with db.connect() as con:
        incidents = [dict(r) for r in con.execute("SELECT * FROM incidents WHERE id NOT LIKE 'INC-LIVE-%' ORDER BY ts").fetchall()]
        rows = [dict(r) for r in con.execute("SELECT * FROM memories WHERE source='seed'").fetchall()]
    points = []
    correct = 0
    graded = 0
    for i, inc in enumerate(incidents):
        if i < 3:
            continue
        as_of = inc["ts"]
        window = [r for r in rows if r["created_at"] < as_of and r["incident_id"] != inc["id"]]
        # only grade once the agent has real experience for this service
        if len([r for r in window if r["service"] == inc["service"]]) < 3:
            continue
        alert = {"service": inc["service"], "title": inc["title"], "body": inc["symptom"],
                 "signals": db.json_load(inc["signals"])}
        hits, _ = memory._bm25(build_query(alert), window, 8)
        ranked = rank(hits, db.json_load(inc["signals"]))
        if not ranked:
            continue
        top = ranked[0]
        ok = top["cause_class"] == inc["cause_class"]
        top3 = inc["cause_class"] in [g["cause_class"] for g in ranked[:3]]
        graded += 1
        correct += 1 if ok else 0
        points.append({
            "n": graded, "ts": inc["ts"][:10], "incident_id": inc["id"], "service": inc["service"],
            "predicted": top["root_cause"], "actual": inc["root_cause"],
            "correct": ok, "top3": top3, "confidence": round(0.5 + 0.42 * top["similarity"], 2),
            "accuracy": round(correct / graded, 3),
        })
    right = [p for p in points if p["correct"]]
    wrong = [p for p in points if not p["correct"]]
    return {
        "points": points,
        "graded": graded,
        "top1": round(correct / graded, 3) if graded else 0,
        "top3": round(sum(1 for p in points if p["top3"]) / graded, 3) if graded else 0,
        "method": "BM25 as-of index over the seeded corpus (no LLM, no future memories)",
        "early": round(sum(p["correct"] for p in points[:6]) / max(1, len(points[:6])), 3),
        "late": round(sum(p["correct"] for p in points[-6:]) / max(1, len(points[-6:])), 3),
        "sample_right": right[:3],
        "sample_wrong": wrong[:3],
    }


# --------------------------------------------------------------------------- #
# overview
# --------------------------------------------------------------------------- #
def overview() -> dict:
    with db.connect() as con:
        by_service = [dict(r) for r in con.execute(
            "SELECT service, COUNT(*) incidents, ROUND(AVG(fix_minutes),1) avg_fix FROM incidents GROUP BY service ORDER BY incidents DESC"
        ).fetchall()]
        recent = [dict(r) for r in con.execute(
            "SELECT id,ts,service,title,severity,outcome,fix_minutes FROM incidents ORDER BY ts DESC LIMIT 6"
        ).fetchall()]
    return {
        "counts": db.counts(),
        "by_service": by_service,
        "recent": recent,
        "memory": memory.stats(),
        "backend": memory.backend(),
        "groq": groq_available(),
        "model": GROQ_MODEL,
        "bank": memory.BANK,
        "alerts": list_alerts(8),
    }
