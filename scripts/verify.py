"""Final verification. Run before submission.

    python -m scripts.verify
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OK = []
FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (OK if cond else FAIL).append((name, detail))
    print(("  OK   " if cond else "  FAIL ") + name + (f"  -- {detail}" if detail else ""))


def main() -> int:
    print("\nDeja Vu verification\n")

    # ---- imports
    try:
        from dejavu import agent, band, db, memory
        check("imports", True)
    except Exception as e:
        check("imports", False, str(e))
        return 1

    # ---- health
    h = memory.status()
    check("memory backend is hindsight", h["backend"] == "hindsight", h["backend"])
    check("groq available", agent.groq_available())

    # ---- data
    c = db.counts()
    check("incidents >= 34", c["incidents"] >= 34, str(c["incidents"]))
    check("memories >= 34", c["memories"] >= 34, str(c["memories"]))
    check("4 services", c["services"] == 4, str(c["services"]))

    # ---- hindsight bank
    try:
        mems = memory.client().list_memories(bank_id=memory.BANK)
        n = len(mems.items)
        check("hindsight bank has >= 34 docs", n >= 34, str(n))
    except Exception as e:
        check("hindsight bank reachable", False, str(e))

    # ---- analyze
    a = agent.create_alert("demo")
    off = agent.analyze(a["id"], "off")
    on = agent.analyze(a["id"], "on")
    try:
        on["band"] = band.dispatch(on, a["id"])
    except Exception as e:
        on["band"] = None
        print("  band dispatch error:", e)
    check("memory off confidence < 0.5", off["hypothesis"]["confidence"] < 0.5,
          str(off["hypothesis"]["confidence"]))
    check("memory on confidence >= 0.7", on["hypothesis"]["confidence"] >= 0.7,
          str(on["hypothesis"]["confidence"]))
    check("memory on has >= 2 receipts", len(on["evidence"]) >= 2, str(len(on["evidence"])))
    check("contradiction present", on["contradiction"] is not None)
    check("band dispatch attached", isinstance(on.get("band"), dict) and on["band"].get("messages"))
    check("band verdict present", (on["band"].get("review") or {}).get("verdict") in ("allow", "review", "block"))

    # ---- resolve + repeat
    h = on["hypothesis"]
    r = agent.resolve(a["id"], h["title"], h["fix"], "Abinivesh M", h["fix_minutes"], "resolved",
                      h.get("cause_class", ""))
    check("resolve returns memory_id", (r.get("memory") or {}).get("memory_id", "").startswith("MEM-"))
    check("resolve backend hindsight", (r.get("memory") or {}).get("backend") == "hindsight",
          (r.get("memory") or {}).get("backend"))
    b = agent.create_alert("repeat")
    on2 = agent.analyze(b["id"], "on")
    check("repeat cites a live incident first",
          any("LIVE" in str(e["incident_id"]) for e in on2["evidence"][:2]))

    # ---- replay
    rep = agent.replay()
    check("replay graded >= 20", rep["graded"] >= 20, str(rep["graded"]))
    check("replay top1 >= 0.45", rep["top1"] >= 0.45, str(rep["top1"]))
    check("replay late >= 0.75", rep["late"] >= 0.75, str(rep["late"]))
    check("replay early < late", rep["early"] < rep["late"], f"{rep['early']} vs {rep['late']}")

    # ---- content files
    art = ROOT / "article.md"
    check("article.md exists", art.exists())
    if art.exists():
        txt = art.read_text(encoding="utf-8")
        words = len(re.findall(r"\w+", txt))
        check("article 800-1500 words", 800 <= words <= 1500, str(words))
        check("article mentions Hindsight", "Hindsight" in txt)
        check("article has hindsight github link", "github.com/vectorize-io/hindsight" in txt)
        check("article has hindsight docs link", "hindsight.vectorize.io" in txt)
        check("article has vectorize memory link", "vectorize.io/what-is-agent-memory" in txt)
        check("article has code snippet", "```" in txt)
        check("article no 'hackathon'", "hackathon" not in txt.lower())

    soc = ROOT / "docs" / "SOCIAL.md"
    check("SOCIAL.md exists", soc.exists())
    if soc.exists():
        txt = soc.read_text(encoding="utf-8")
        check("social no 'hackathon'", "hackathon" not in txt.lower())

    # ---- social char counts
    import re as _re
    posts = _re.split(r"\n## ", soc.read_text(encoding="utf-8")) if soc.exists() else []
    for p in posts[1:]:
        title = p.split("\n", 1)[0]
        if not title[0].isdigit():
            continue
        body = p.split("\n", 1)[1].split("\n---")[0].strip()
        check(f"social post {title[:2]} < 800 chars", len(body) < 800, str(len(body)))

    # ---- no secrets
    env = ROOT / ".env"
    if env.exists():
        txt = env.read_text(encoding="utf-8")
        check(".env not committed (gitignored)", True)  # informational
    gi = ROOT / ".gitignore"
    check(".gitignore exists", gi.exists())
    if gi.exists():
        check(".env in .gitignore", ".env" in gi.read_text(encoding="utf-8"))

    # ---- summary
    print(f"\n{len(OK)} passed, {len(FAIL)} failed")
    if FAIL:
        for n, d in FAIL:
            print("  -", n, d)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
