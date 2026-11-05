"""Band bridge check — verify credentials before a demo.

    python -m scripts.band_check           # list rooms the recall agent can see
    python -m scripts.band_check --post    # also post one test event to the room

Reads BAND_API_URL, BAND_API_KEY, BAND_CHAT_ID from the environment. Never
prints the key. Exits non-zero when the bridge cannot reach the room.
"""
from __future__ import annotations

import argparse
import sys
import time

import httpx

from dejavu import band


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true", help="post one test event")
    args = ap.parse_args()

    print(f"base:       {band.BASE}")
    print(f"room:       {band.CHAT or '(BAND_CHAT_ID not set)'}")
    print(f"recall key: {'set' if band.KEY else 'missing'}")
    print(f"critic key: {'set' if band.CRITIC_KEY else 'fallback to recall key'}")

    if not band.KEY:
        print("\nBAND_API_KEY is missing — the app will run in local preview.")
        return 2

    try:
        r = httpx.get(
            f"{band.BASE}/api/v1/agent/chats",
            headers={"X-API-Key": band.KEY},
            timeout=15,
        )
    except Exception as exc:
        print(f"\nunreachable: {exc}")
        return 2

    if r.status_code != 200:
        print(f"\nlist rooms failed: {r.status_code} {r.text[:300]}")
        return 2

    chats = r.json().get("chats") or r.json().get("data") or []
    print(f"\nrooms visible to {band.AGENT_NAME}: {len(chats)}")
    for c in chats[:10]:
        print(f"  {c.get('id')}  {c.get('title') or '(untitled)'}")

    if not band.CHAT:
        print("\nCopy the room id above into BAND_CHAT_ID.")
        return 2

    if not any(c.get("id") == band.CHAT for c in chats):
        print("\nThe recall agent is not a participant in BAND_CHAT_ID — add it to the room.")
        return 2

    if args.post:
        res = band.post_event(f"Bridge check from Déjà Vu — {time.strftime('%H:%M:%S')}")
        print(f"\npost event: ok={res['ok']} detail={res['detail']} {res['latency_ms']} ms")
        if not res["ok"]:
            return 1
        critic = band.post_event("Bridge check from the critic role.", api_key=band.CRITIC_KEY or band.KEY)
        print(f"post critic: ok={critic['ok']} detail={critic['detail']} {critic['latency_ms']} ms")
        if not critic["ok"]:
            return 1

    print("\nbridge ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
