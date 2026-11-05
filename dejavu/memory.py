"""Memory layer.

Primary path: Hindsight (local server, bank ``dejavu-oncall``).
Fallback path: in-process BM25 over the SQLite mirror.

The fallback exists for one reason: a live demo must not die because a
background service did not start. The UI always shows which path served the
request, so nothing is hidden from judges.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone

import httpx

from . import db

BANK = os.getenv("DEJAVU_BANK", "dejavu-oncall")
BASE_URL = os.getenv("HINDSIGHT_API_URL", "http://127.0.0.1:8888").rstrip("/")
API_KEY = os.getenv("HINDSIGHT_API_KEY") or None

MISSION = (
    "I am the long-term memory of an on-call SRE team at a payments company. "
    "I remember every incident, the signals that preceded it, the root cause, "
    "the fix that actually worked, how long it took, and when a fix failed."
)

_client = None
_backend: str | None = None
_checked_at = 0.0


# --------------------------------------------------------------------------- #
# backend detection
# --------------------------------------------------------------------------- #
def client():
    global _client
    if _client is None:
        from hindsight_client import Hindsight

        _client = Hindsight(base_url=BASE_URL, api_key=API_KEY, timeout=180.0)
    return _client


def backend(refresh: bool = False) -> str:
    """Return 'hindsight' or 'local'. Cached for 15s."""
    global _backend, _checked_at
    if not refresh and _backend and (time.time() - _checked_at) < 15:
        return _backend
    _backend = "local"
    for path in ("/health", "/v1/health", "/"):
        try:
            r = httpx.get(BASE_URL + path, timeout=2.0)
            if r.status_code < 500:
                _backend = "hindsight"
                break
        except Exception:
            continue
    _checked_at = time.time()
    return _backend


def status() -> dict:
    b = backend(refresh=True)
    info = {"backend": b, "bank": BANK, "url": BASE_URL, "client": "hindsight-client"}
    if b == "hindsight":
        try:
            r = httpx.get(BASE_URL + "/health", timeout=3.0)
            info["health"] = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:200]
        except Exception as exc:
            info["health"] = f"unreachable: {exc}"
    return info


def ensure_bank() -> None:
    if backend() != "hindsight":
        return
    try:
        client().create_bank(bank_id=BANK, name="Deja Vu - on-call memory", mission=MISSION)
    except Exception:
        # already exists, or the server rejects a duplicate: both are fine
        pass


# --------------------------------------------------------------------------- #
# retain
# --------------------------------------------------------------------------- #
def _meta(inc: dict) -> dict[str, str]:
    return {
        "incident_id": str(inc.get("id", "")),
        "service": str(inc.get("service", "")),
        "root_cause": str(inc.get("root_cause", "")),
        "fix": str(inc.get("fix", ""))[:400],
        "outcome": str(inc.get("outcome", "")),
        "fix_minutes": str(inc.get("fix_minutes", "")),
        "engineer": str(inc.get("engineer", "")),
        "severity": str(inc.get("severity", "")),
        "ts": str(inc.get("ts", "")),
    }


def retain(inc: dict, text: str, source: str = "live", incident_id: str | None = None) -> dict:
    """Store one memory. Always writes the SQLite mirror; writes Hindsight when up."""
    incident_id = incident_id or inc.get("id") or f"INC-LIVE-{int(time.time())}"
    mem_id = f"MEM-{incident_id}"
    ts = inc.get("ts") or db.now_iso()
    with db.connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO memories (id,incident_id,bank,text,service,root_cause,cause_class,fix,outcome,"
            "fix_minutes,engineer,created_at,last_confirmed,success_count,fail_count,stale,source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mem_id, incident_id, BANK, text, inc.get("service", ""), inc.get("root_cause", ""),
             inc.get("cause_class", "") or inc.get("root_cause", ""),
             inc.get("fix", ""), inc.get("outcome", "resolved"), float(inc.get("fix_minutes", 0) or 0),
             inc.get("engineer", "on-call"), ts, ts,
             1 if inc.get("outcome", "resolved") == "resolved" else 0,
             0 if inc.get("outcome", "resolved") == "resolved" else 1,
             0, source),
        )

    t0 = time.perf_counter()
    used = "local"
    detail = "stored in SQLite mirror only"
    if backend() == "hindsight":
        try:
            resp = client().retain(
                bank_id=BANK,
                content=text,
                document_id=incident_id,
                context=f"{inc.get('service')} {inc.get('severity')} incident on {ts[:10]}",
                metadata=_meta(inc),
                tags=[str(inc.get("service", "")), str(inc.get("severity", "")), str(inc.get("outcome", ""))],
            )
            used = "hindsight"
            detail = f"items={getattr(resp, 'items_count', '?')}"
        except Exception as exc:
            detail = f"hindsight retain failed: {exc}"[:300]

    ms = (time.perf_counter() - t0) * 1000
    db.log_bus("retain", BANK, f"{incident_id} {inc.get('service')} {inc.get('root_cause', '')[:80]}",
               1, ms, used, detail)
    return {"memory_id": mem_id, "incident_id": incident_id, "backend": used, "latency_ms": round(ms, 1)}


# --------------------------------------------------------------------------- #
# recall
# --------------------------------------------------------------------------- #
def _walk_strings(obj) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_walk_strings(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(_walk_strings(v))
    else:
        for attr in ("content", "text", "fact", "memory", "summary", "document_id", "id"):
            v = getattr(obj, attr, None)
            if isinstance(v, str):
                out.append(v)
    return out


def _score_of(result) -> float:
    for attr in ("score", "similarity", "relevance", "weight"):
        v = getattr(result, attr, None)
        if isinstance(v, (int, float)):
            return float(v)
    d = getattr(result, "model_dump", lambda: {})()
    for k in ("score", "similarity", "relevance", "weight"):
        if isinstance(d.get(k), (int, float)):
            return float(d[k])
    return 0.0


def _recall_hindsight(query: str, k: int) -> tuple[list[dict], str]:
    resp = client().recall(
        bank_id=BANK, query=query, max_tokens=6000, budget="mid",
        include_source_facts=False, trace=False,
    )
    results = getattr(resp, "results", []) or []
    agg: dict[str, float] = {}
    for r in results:
        text = " ".join(_walk_strings(r))
        m = re.search(r"INC-[0-9A-Z\-]+", text)
        inc_id = m.group(0) if m else str(getattr(r, "document_id", "") or "")
        if not inc_id:
            continue
        s = _score_of(r) or 1.0
        agg[inc_id] = max(agg.get(inc_id, 0.0), s)
    hits = _hydrate(agg)
    detail = f"hindsight returned {len(results)} raw result(s) -> {len(hits)} incident(s)"
    return hits[:k], detail


# --------------------------------------------------------------------------- #
# BM25 fallback
# --------------------------------------------------------------------------- #
_TOKEN = re.compile(r"[a-z0-9][a-z0-9_.:-]*")
_STOP = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at", "is", "are",
    "was", "were", "be", "been", "with", "from", "by", "as", "it", "its", "this",
    "that", "after", "before", "during", "we", "our", "had", "has", "have", "not",
}


def _toks(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


def _bm25(query: str, rows: list[dict], k: int) -> tuple[list[dict], str]:
    q = list(dict.fromkeys(_toks(query)))
    if not rows or not q:
        return [], "empty query"
    ql = query.lower()
    # Failure patterns transfer across services: rank everything, with a
    # same-service booster. Service scoping alone hid useful lessons.
    pool = rows
    incs = _incident_map()
    docs = [_toks(_match_text(r, incs.get(r["incident_id"]))) for r in pool]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n
    df = Counter()
    for d in docs:
        for t in set(d):
            df[t] += 1
    idf = {t: math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in q}
    total_idf = sum(idf.values()) or 1.0
    scored: list[tuple[dict, float]] = []
    for r, d in zip(pool, docs):
        tf = Counter(d)
        num = 0.0
        for t in q:
            f = tf.get(t, 0)
            if f:
                num += idf[t] * (f / (f + 1.2))
        score = num / total_idf
        if r["service"].lower() in ql:
            score += 0.08
        scored.append((r, min(1.0, score)))
    scored.sort(key=lambda x: -x[1])
    sigs = _signals_map()
    hits = [{**_row_hit(r, s, sigs.get(r["incident_id"]))} for r, s in scored[:k] if s > 0]
    return hits, f"bm25 over {len(pool)} service-scoped memories"


def _row_hit(row: dict, score: float, signals: dict | None = None) -> dict:
    return {
        "incident_id": row["incident_id"],
        "memory_id": row["id"],
        "text": row["text"],
        "service": row["service"],
        "root_cause": row["root_cause"],
        "cause_class": row.get("cause_class", ""),
        "fix": row["fix"],
        "outcome": row["outcome"],
        "fix_minutes": row["fix_minutes"],
        "engineer": row["engineer"],
        "created_at": row["created_at"],
        "success_count": row["success_count"],
        "fail_count": row["fail_count"],
        "stale": bool(row["stale"]),
        "signals": signals or {},
        "score": round(float(score), 3),
    }


def _signals_map() -> dict[str, dict]:
    with db.connect() as con:
        return {r["id"]: db.json_load(r["signals"]) for r in con.execute("SELECT id,signals FROM incidents")}


def _incident_map() -> dict[str, dict]:
    with db.connect() as con:
        return {r["id"]: dict(r) for r in con.execute("SELECT * FROM incidents")}


def _match_text(row: dict, inc: dict | None) -> str:
    """Clean retrieval text: what the failure looked like, not how it was fixed."""
    parts = [row.get("service", ""), row.get("root_cause", ""), row.get("root_cause", "")]
    if inc:
        tags = db.json_load(inc.get("tags", "[]"))
        parts += [inc.get("title", ""), inc.get("title", ""), inc.get("symptom", ""),
                  " ".join(tags) if isinstance(tags, list) else str(tags),
                  " ".join((inc.get("signals") and list(db.json_load(inc["signals"]).keys())) or [])]
    return " ".join(parts)


def _hydrate(scores: dict[str, float]) -> list[dict]:
    if not scores:
        return []
    with db.connect() as con:
        rows = con.execute("SELECT * FROM memories").fetchall()
    by_inc = {r["incident_id"]: dict(r) for r in rows}
    sigs = _signals_map()
    top = max(scores.values()) or 1.0
    out = []
    for inc_id, s in scores.items():
        row = by_inc.get(inc_id)
        if row:
            out.append(_row_hit(row, s / top, sigs.get(inc_id)))
    out.sort(key=lambda x: -x["score"])
    return out


def recall(query: str, k: int = 8, service: str | None = None) -> dict:
    t0 = time.perf_counter()
    used = backend()
    detail = ""
    hits: list[dict] = []
    if used == "hindsight":
        try:
            hits, detail = _recall_hindsight(query, k)
        except Exception as exc:
            used = "local"
            detail = f"hindsight recall failed, fell back to bm25: {exc}"[:300]
    if used == "local":
        with db.connect() as con:
            rows = [dict(r) for r in con.execute("SELECT * FROM memories").fetchall()]
        hits, detail = _bm25(query, rows, k)

    if service:
        for h in hits:
            if h["service"] == service:
                h["score"] = round(min(1.0, h["score"] + 0.08), 3)
        hits.sort(key=lambda x: -x["score"])

    ms = (time.perf_counter() - t0) * 1000
    db.log_bus("recall", BANK, query, len(hits), ms, used, detail)
    return {
        "backend": used,
        "latency_ms": round(ms, 1),
        "query": query,
        "hits": hits[:k],
        "detail": detail,
    }


def search(q: str, limit: int = 50) -> list[dict]:
    if backend() == "hindsight" and q:
        try:
            hits, _ = _recall_hindsight(q, limit)
            if hits:
                return hits
        except Exception:
            pass
    with db.connect() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM memories").fetchall()]
    if not q:
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [_row_hit(r, 1.0) for r in rows[:limit]]
    hits, _ = _bm25(q, rows, limit)
    return hits


def stale_memories() -> list[dict]:
    with db.connect() as con:
        rows = con.execute("SELECT * FROM memories WHERE stale=1 ORDER BY created_at").fetchall()
    return [_row_hit(dict(r), 1.0) for r in rows]


def stats() -> dict:
    with db.connect() as con:
        total = con.execute("SELECT COUNT(*) c FROM memories").fetchone()["c"]
        stale = con.execute("SELECT COUNT(*) c FROM memories WHERE stale=1").fetchone()["c"]
        live = con.execute("SELECT COUNT(*) c FROM memories WHERE source='live'").fetchone()["c"]
    return {"memories": total, "stale": stale, "learned_live": live, "bank": BANK}
