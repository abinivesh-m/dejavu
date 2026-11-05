"""End-to-end smoke test: alert -> off/on -> resolve -> repeat -> replay."""
from __future__ import annotations

import json

from dejavu import agent, db, memory


def show(title: str) -> None:
    print("\n" + "=" * 66)
    print(title)
    print("=" * 66)


def main() -> None:
    print("memory backend:", memory.backend(), "| groq:", agent.groq_available())
    a = agent.create_alert("demo")
    print("alert:", a["id"], a["service"], a["severity"])

    show("MEMORY OFF")
    off = agent.analyze(a["id"], "off")
    print("confidence:", off["hypothesis"]["confidence"])
    print("narrative:", off["narrative"][:180])
    print("evidence:", len(off["evidence"]))

    show("MEMORY ON")
    on = agent.analyze(a["id"], "on")
    h = on["hypothesis"]
    print("backend:", on["backend"], "| recall_ms:", on["memory_latency_ms"], "| llm:", on["llm"])
    print("confidence:", h["confidence"], "| support:", h["support"], "| success:", h["success_rate"])
    print("hypothesis:", h["title"])
    print("fix:", h["fix"])
    print("narrative:", on["narrative"])
    print("first_action:", on["first_action"])
    print("evidence:")
    for e in on["evidence"]:
        print(f"  - {e['incident_id']} {e['ts'][:10]} sim={e['similarity']} {e['outcome']:9s} {e['root_cause'][:55]}")
    print("contradiction:", json.dumps(on["contradiction"], indent=2)[:400] if on["contradiction"] else None)
    print("avoid:", on["avoid"])

    show("RESOLVE -> RETAIN")
    r = agent.resolve(a["id"], h["title"], h["fix"], "Abinivesh M", h["fix_minutes"], "resolved",
                      h.get("cause_class", ""))
    print(json.dumps(r, indent=2))

    show("REPEAT ALERT (same signature, after learning)")
    b = agent.create_alert("repeat")
    on2 = agent.analyze(b["id"], "on")
    print("top:", on2["hypothesis"]["title"], "| confidence:", on2["hypothesis"]["confidence"])
    print("narrative:", on2["narrative"][:220])
    print("evidence ids:", [e["incident_id"] for e in on2["evidence"]])

    show("LEARNING REPLAY")
    rep = agent.replay()
    print("graded:", rep["graded"], "top1:", rep["top1"], "top3:", rep["top3"],
          "early:", rep["early"], "late:", rep["late"])
    for p in rep["points"]:
        print(f"  {p['n']:2d} {p['ts']} {p['service']:13s} {'OK ' if p['correct'] else 'MISS'} {p['predicted'][:48]}")

    print("\nmemories:", db.counts())


if __name__ == "__main__":
    main()
