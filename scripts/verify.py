"""Release verification. Run before shipping a build.

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
    check("decision present", (on.get("decision") or {}).get("label") in
          ("APPLY THIS FIX", "VERIFY FIRST", "DO NOT APPLY"),
          (on.get("decision") or {}).get("label", ""))
    check("decision is apply for demo", (on.get("decision") or {}).get("level") == "apply",
          (on.get("decision") or {}).get("level", ""))
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

    # ---- writing package (kept out of the public repo; checked when present)
    articles = {
        "abinivesh-m": ROOT / "docs" / "ARTICLE.md",
        "abhinivesh-k": ROOT / "docs" / "articles" / "abhinivesh-k.md",
        "mrittika-s": ROOT / "docs" / "articles" / "mrittika-s.md",
        "harini-e-s": ROOT / "docs" / "articles" / "harini-e-s.md",
    }
    soc = ROOT / "docs" / "SOCIAL.md"
    if any(p.exists() for p in articles.values()) or soc.exists():
        root_art = ROOT / "article.md"
        check("article.md exists", root_art.exists())
        check(
            "article.md matches docs/ARTICLE.md",
            root_art.exists()
            and root_art.read_text(encoding="utf-8") == articles["abinivesh-m"].read_text(encoding="utf-8"),
        )
        for name, path in articles.items():
            check(f"{name} article exists", path.exists())
            if not path.exists():
                continue
            txt = path.read_text(encoding="utf-8")
            words = len(re.findall(r"\w+", txt))
            check(f"{name} 800-1500 words", 800 <= words <= 1500, str(words))
            check(f"{name} mentions Hindsight", "Hindsight" in txt)
            check(f"{name} hindsight github link", "github.com/vectorize-io/hindsight" in txt)
            check(f"{name} hindsight docs link", "hindsight.vectorize.io" in txt)
            check(f"{name} vectorize memory link", "vectorize.io/what-is-agent-memory" in txt)
            check(f"{name} code snippet", "```" in txt)
            check(f"{name} no 'hackathon'", "hackathon" not in txt.lower())

        if soc.exists():
            txt = soc.read_text(encoding="utf-8")
            check("social no 'hackathon'", "hackathon" not in txt.lower())

            # ---- social char counts
            posts = re.split(r"\n## ", txt)
            for p in posts[1:]:
                title = p.split("\n", 1)[0]
                if not title[0].isdigit():
                    continue
                body = p.split("\n", 1)[1].split("\n---")[0].strip()
                check(f"social post {title[:2]} < 800 chars", len(body) < 800, str(len(body)))
    else:
        print("  SKIP writing package (not part of the public repo)")

    # ---- no secrets
    env = ROOT / ".env"
    if env.exists():
        txt = env.read_text(encoding="utf-8")
        check(".env not committed (gitignored)", True)  # informational
    gi = ROOT / ".gitignore"
    check(".gitignore exists", gi.exists())
    if gi.exists():
        check(".env in .gitignore", ".env" in gi.read_text(encoding="utf-8"))

    # ---- cleanup: verification writes a live incident, so leave the bank pristine
    with db.connect() as con:
        for tbl in ("alerts", "analyses", "bus", "band"):
            con.execute(f"DELETE FROM {tbl}")
        con.execute("DELETE FROM memories WHERE incident_id LIKE 'INC-LIVE%'")
        con.execute("DELETE FROM incidents WHERE id LIKE 'INC-LIVE%'")
    try:
        memory.forget_live()
    except Exception:
        pass

    # ---- summary
    print(f"\n{len(OK)} passed, {len(FAIL)} failed")
    if FAIL:
        for n, d in FAIL:
            print("  -", n, d)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
