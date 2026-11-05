"""Push the incident corpus into Hindsight.

The SQLite mirror is written by ``dejavu.seed``. This script retains the same
documents in the Hindsight bank so recall is served by the real memory server.

    python -m scripts.push_memories          # all incidents
    python -m scripts.push_memories --limit 2  # smoke test
    python -m scripts.push_memories --verify   # recall check only
"""
from __future__ import annotations

import argparse
import sys
import time

from dejavu import db, memory, seed


def run(limit: int | None = None) -> None:
    if memory.backend(refresh=True) != "hindsight":
        print("Hindsight is not reachable at", memory.BASE_URL)
        sys.exit(1)

    memory.ensure_bank()
    print(f"bank: {memory.BANK} @ {memory.BASE_URL}")

    incidents = seed.INCIDENTS if not limit else seed.INCIDENTS[:limit]
    ok = 0
    t0 = time.perf_counter()
    for n, inc in enumerate(incidents, 1):
        res = memory.retain(inc, seed.memory_text(inc), source="seed", incident_id=inc["id"])
        flag = "ok " if res["backend"] == "hindsight" else "LOCAL"
        ok += res["backend"] == "hindsight"
        print(f"[{n:02d}/{len(incidents)}] {flag} {inc['id']:<10} {res['latency_ms']:7.0f}ms")

    dt = time.perf_counter() - t0
    print(f"\nretained {ok}/{len(incidents)} in hindsight in {dt:.1f}s")


def verify(queries: list[str] | None = None) -> None:
    queries = queries or [
        "checkout-api p99 latency 3.9s database cpu high pool wait",
        "auth-api 401s after DNS change TTL low",
        "ledger-worker lock wait deadlocks during batch reconciliation",
    ]
    for q in queries:
        res = memory.recall(q, k=5)
        print(f"\nquery: {q}")
        print(f"  backend={res['backend']} {res['latency_ms']}ms hits={len(res['hits'])}")
        for h in res["hits"][:5]:
            print(f"  - {h['incident_id']:<10} {h['score']:.3f}  {h['root_cause'][:64]}")
    print("\nbank contents:", memory.stats())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()
    if args.verify:
        verify()
        return
    if args.skip_existing:
        try:
            mems = memory.client().list_memories(bank_id=memory.BANK)
            n = len(getattr(mems, "memories", None) or mems or [])
        except Exception:
            n = 0
        if n >= len(seed.INCIDENTS):
            print(f"bank already has {n} memories; nothing to do")
            verify()
            return
    run(args.limit)
    verify()


if __name__ == "__main__":
    main()
