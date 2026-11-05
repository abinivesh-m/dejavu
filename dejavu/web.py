"""FastAPI app for Deja Vu."""
from __future__ import annotations

import argparse
import json
import sqlite3
import threading

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, band, config, db, memory, seed

app = FastAPI(title="Deja Vu", version="1.0")

app.mount("/static", StaticFiles(directory=str(config.STATIC)), name="static")


# --------------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------------- #
@app.on_event("startup")
def _startup() -> None:
    db.ready()
    with db.connect() as con:
        n = con.execute("SELECT COUNT(*) c FROM incidents").fetchone()["c"]
    if n == 0:
        with db.connect() as con:
            seed.seed_memories(con)

    def warm() -> None:
        try:
            memory.ensure_bank()
        except Exception:
            pass

    threading.Thread(target=warm, daemon=True).start()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(config.STATIC / "index.html"), headers={"Cache-Control": "no-store"})


# --------------------------------------------------------------------------- #
# api
# --------------------------------------------------------------------------- #
@app.get("/api/overview")
def overview() -> dict:
    return agent.overview()


@app.get("/api/health")
def health() -> dict:
    return {"memory": memory.status(), "groq": agent.groq_available(), "model": agent.GROQ_MODEL}


@app.get("/api/alerts")
def alerts() -> dict:
    return {"alerts": agent.list_alerts(30)}


class NewAlert(BaseModel):
    scenario: str = "demo"


@app.post("/api/alerts")
def new_alert(body: NewAlert) -> dict:
    return agent.create_alert(body.scenario)


@app.get("/api/alerts/{aid}")
def get_alert(aid: str) -> dict:
    try:
        return agent.get_alert(aid)
    except KeyError:
        raise HTTPException(status_code=404, detail="alert not found")


class Analyze(BaseModel):
    alert_id: str
    mode: str = "on"


@app.post("/api/analyze")
def analyze(body: Analyze) -> dict:
    if body.mode not in ("on", "off"):
        raise HTTPException(status_code=400, detail="mode must be on or off")
    try:
        payload = agent.analyze(body.alert_id, body.mode)
    except KeyError:
        raise HTTPException(status_code=404, detail="alert not found")
    if body.mode == "on":
        try:
            payload["band"] = band.dispatch(payload, body.alert_id)
        except Exception as exc:  # the room must never break the answer
            payload["band"] = {"configured": False, "transport": "error", "detail": str(exc)[:200]}
    return payload


@app.get("/api/band/{aid}")
def band_room(aid: str) -> dict:
    return band.transcript(aid)


@app.get("/api/band")
def band_info() -> dict:
    return band.room()


class Resolve(BaseModel):
    alert_id: str
    root_cause: str
    fix: str
    engineer: str = "Abinivesh M"
    minutes: float = 6.0
    outcome: str = "resolved"
    cause_class: str = ""


@app.post("/api/resolve")
def resolve(body: Resolve) -> dict:
    try:
        return agent.resolve(body.alert_id, body.root_cause, body.fix, body.engineer,
                             body.minutes, body.outcome, body.cause_class)
    except KeyError:
        raise HTTPException(status_code=404, detail="alert not found")


@app.get("/api/learning")
def learning() -> dict:
    return agent.replay()


@app.get("/api/memory")
def search_memory(q: str = "") -> dict:
    return {"query": q, "memories": memory.search(q, 60), "stats": memory.stats()}


@app.get("/api/memory/stale")
def stale() -> dict:
    return {"memories": memory.stale_memories()}


@app.get("/api/incidents")
def incidents() -> dict:
    rows = db.list_incidents(200)
    for r in rows:
        r["signals"] = db.json_load(r["signals"])
    return {"incidents": rows}


@app.get("/api/incidents/{iid}")
def incident(iid: str) -> dict:
    row = db.get_incident(iid)
    if not row:
        raise HTTPException(status_code=404, detail="incident not found")
    row["signals"] = db.json_load(row["signals"])
    return row


@app.get("/api/bus")
def bus() -> dict:
    return {"ops": db.recent_bus(30), "backend": memory.backend()}


class Reset(BaseModel):
    fresh: bool = False


@app.post("/api/reset")
def reset(body: Reset = Reset()) -> dict:
    with db.connect() as con:
        con.execute("DELETE FROM alerts")
        con.execute("DELETE FROM analyses")
        con.execute("DELETE FROM bus")
        con.execute("DELETE FROM band")
        if body.fresh:
            con.execute("DELETE FROM memories")
            con.execute("DELETE FROM incidents")
    if body.fresh:
        try:
            memory.forget_live()
        except Exception:
            pass
    if body.fresh:
        with db.connect() as con:
            seed.seed_memories(con)
    return {"ok": True, "counts": db.counts()}


@app.exception_handler(404)
def not_found(_request, exc):
    return JSONResponse({"error": "not found", "detail": str(exc.detail)}, status_code=404)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8011)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--reload", action="store_true")
    args = ap.parse_args()
    uvicorn.run("dejavu.web:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
