"""SQLite storage for Deja Vu.

Hindsight is the semantic memory layer; SQLite is the operational record
(incidents, alerts, analysis runs and the memory bus trace).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "dejavu.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    service TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    symptom TEXT NOT NULL,
    signals TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    cause_class TEXT NOT NULL DEFAULT '',
    fix TEXT NOT NULL,
    fix_minutes REAL NOT NULL,
    outcome TEXT NOT NULL,
    engineer TEXT NOT NULL,
    tags TEXT NOT NULL,
    discriminator TEXT NOT NULL,
    postmortem TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_inc_ts ON incidents(ts);
CREATE INDEX IF NOT EXISTS idx_inc_service ON incidents(service);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    bank TEXT NOT NULL,
    text TEXT NOT NULL,
    service TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    cause_class TEXT NOT NULL DEFAULT '',
    fix TEXT NOT NULL,
    outcome TEXT NOT NULL,
    fix_minutes REAL NOT NULL,
    engineer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_confirmed TEXT NOT NULL,
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count INTEGER NOT NULL DEFAULT 0,
    stale INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'seed'
);
CREATE INDEX IF NOT EXISTS idx_mem_service ON memories(service);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    service TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    body TEXT NOT NULL,
    signals TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    matched_incident TEXT,
    resolved_by TEXT
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    top_incident TEXT,
    correct INTEGER,
    latency_ms REAL NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    op TEXT NOT NULL,
    bank TEXT NOT NULL,
    query TEXT NOT NULL,
    n_results INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    backend TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT ''
);

-- Room transcript. Mirrors what the Band agents say to each other, so the
-- handoff is visible in the UI even when no Band credentials are configured.
CREATE TABLE IF NOT EXISTS band (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    alert_id TEXT NOT NULL,
    author TEXT NOT NULL,
    role TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'message',
    body TEXT NOT NULL,
    mentions TEXT NOT NULL DEFAULT '[]',
    delivered INTEGER NOT NULL DEFAULT 0,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_band_alert ON band(alert_id);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def ready() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def get_incident(incident_id: str) -> dict | None:
    with connect() as con:
        return row_to_dict(con.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone())


def list_incidents(limit: int = 200) -> list[dict]:
    with connect() as con:
        rows = con.execute("SELECT * FROM incidents ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def counts() -> dict:
    with connect() as con:
        return {
            "incidents": con.execute("SELECT COUNT(*) c FROM incidents").fetchone()["c"],
            "memories": con.execute("SELECT COUNT(*) c FROM memories").fetchone()["c"],
            "alerts": con.execute("SELECT COUNT(*) c FROM alerts WHERE status='open'").fetchone()["c"],
            "services": con.execute("SELECT COUNT(DISTINCT service) c FROM incidents").fetchone()["c"],
        }


def log_bus(op: str, bank: str, query: str, n_results: int, latency_ms: float, backend: str, detail: str = "") -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO bus (ts, op, bank, query, n_results, latency_ms, backend, detail) VALUES (?,?,?,?,?,?,?,?)",
            (now_iso(), op, bank, query[:400], n_results, round(latency_ms, 1), backend, detail[:2000]),
        )
        # keep the console trace bounded
        con.execute("DELETE FROM bus WHERE id < (SELECT MAX(id) - 300 FROM bus)")


def recent_bus(limit: int = 40) -> list[dict]:
    with connect() as con:
        rows = con.execute("SELECT * FROM bus ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def json_load(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        return {}


def band_add(alert_id: str, author: str, role: str, body: str, kind: str = "message",
             mentions: list | None = None, delivered: bool = False, detail: str = "") -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO band (ts, alert_id, author, role, kind, body, mentions, delivered, detail) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (now_iso(), alert_id, author, role, kind, body, json.dumps(mentions or []),
             1 if delivered else 0, detail[:1000]),
        )
        return int(cur.lastrowid)


def band_for(alert_id: str) -> list[dict]:
    with connect() as con:
        rows = con.execute("SELECT * FROM band WHERE alert_id=? ORDER BY id", (alert_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["mentions"] = json_load(d.get("mentions", "[]")) or []
        out.append(d)
    return out


def band_clear(alert_id: str) -> None:
    with connect() as con:
        con.execute("DELETE FROM band WHERE alert_id=?", (alert_id,))
