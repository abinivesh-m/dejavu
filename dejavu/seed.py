"""Synthetic but realistic incident corpus for Deja Vu.

26 incidents across 4 services and 90 days, plus one deliberately stale
memory from last year so the agent has something to be appropriately
suspicious about. Every row is labelled ``source='seed'`` in SQLite and the
README says the corpus is synthetic.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

from . import db

ENGINEERS = ["Priya Raman", "Arjun Mehta", "Sofia Alvarez", "Dev Patel", "Nisha Rao", "Tom Becker"]

# Failure classes recur across services even when the specific cause differs.
# Grading and grouping happen at class level; the UI still shows the exact cause.
CAUSE_CLASS = {
    "Missing composite index on orders(created_at,status)": "Missing index after a schema or query change",
    "Missing index on settlement_date": "Missing index after a schema or query change",
    "Connection pool size reduced by config rollout": "Pool sizing changed by config",
    "Connection leak in retry wrapper": "Resource leak or blocking call on the hot path",
    "Synchronous audit call on hot path": "Resource leak or blocking call on the hot path",
    "Retry storm without backoff": "Retry storm without backoff",
    "Upstream PSP outage": "Upstream dependency outage",
    "Idempotency key collision on retry": "Idempotency key collision or change",
    "Idempotency cache key changed in deploy": "Idempotency key collision or change",
    "Expired intermediate TLS certificate": "Expired certificate or signing key",
    "Expired JWT signing key": "Expired certificate or signing key",
    "Stale DNS record after failover": "Stale DNS record or TTL after failover",
    "DNS TTL too high for service discovery": "Stale DNS record or TTL after failover",
    "Redis maxmemory-policy evicting sessions": "Redis eviction or failover misconfiguration",
    "Redis sentinel quorum misconfigured": "Redis eviction or failover misconfiguration",
    "Kafka consumer rebalance loop": "Batch or consumer sizing mismatch",
    "Ledger batch size too large": "Batch or consumer sizing mismatch",
    "Undersized JVM heap after payload growth": "Unbounded memory growth",
    "Unbounded in-memory aggregation": "Unbounded memory growth",
    "JWT clock skew across node pool": "Clock or token validation mismatch",
    "Rate limiter keyed on NAT IP": "Rate limiter keyed on the wrong identity",
    "JWKS fetched per request (no cache)": "Cache missing or invalidated too early",
    "Analytics query on primary database": "Reporting query on the primary database",
    "Out-of-order row updates causing deadlock": "Out-of-order writes causing deadlock",
    "Config service pushed a low pool ceiling": "Pool sizing changed by config",
    "PSP 502 burst with no circuit breaker": "Upstream dependency outage",
    "NTP drift on edge nodes": "Clock or token validation mismatch",
    "Carrier NAT reuses one IP for thousands of users": "Rate limiter keyed on the wrong identity",
    "JWKS cache invalidated every minute": "Cache missing or invalidated too early",
    "Month-end report saturates the primary": "Reporting query on the primary database",
    "Batch reconciliation updates rows out of order": "Out-of-order writes causing deadlock",
}


def inc(iid, ts, service, title, sev, symptom, signals, root, fix, mins, outcome, engineer, tags, discriminator):
    return dict(
        id=iid, ts=ts, service=service, title=title, severity=sev, symptom=symptom,
        signals=signals, root_cause=root, cause_class=CAUSE_CLASS.get(root, root),
        fix=fix, fix_minutes=mins, outcome=outcome,
        engineer=engineer, tags=tags, discriminator=discriminator,
    )


INCIDENTS = [
    inc("INC-0912", "2025-12-18T09:40:00+05:30", "checkout-api", "TLS handshake failures at the edge", "SEV-2",
        "Checkout 5xx at 8% for 11 minutes; TLS handshake errors in the edge log.",
        {"p99_ms": 900, "err_pct": 8, "cert_age_days": 368, "tls_errors": 1},
        "Expired intermediate TLS certificate",
        "Rotated the intermediate certificate chain on the ingress", 7, "resolved", "Priya Raman",
        ["tls", "cert", "edge"],
        "Handshake errors, not application errors; no latency ramp before the failure."),

    inc("INC-1001", "2026-08-08T10:14:00+05:30", "checkout-api", "Checkout 5xx after schema migration", "SEV-2",
        "p99 3.9s, 11% 5xx, pool wait 3.1s, DB CPU 58%. Deploy 18 min earlier touched orders schema.",
        {"p99_ms": 3900, "err_pct": 11, "pool_wait_ms": 3100, "db_cpu_pct": 58, "deploy_min_ago": 18},
        "Missing composite index on orders(created_at,status)",
        "Applied migration 2026_08_add_orders_index with CREATE INDEX CONCURRENTLY", 6, "resolved", "Priya Raman",
        ["db", "index", "pool", "deploy"],
        "Pool wait high and DB CPU moderate; the deploy touched only the orders schema."),

    inc("INC-1002", "2026-08-19T15:02:00+05:30", "checkout-api", "Checkout latency ramp, connections never released", "SEV-2",
        "p99 4.1s, pool wait 3.2s, active connections pinned at max, DB CPU 44%. Deploy 46 min earlier changed the retry path.",
        {"p99_ms": 4100, "err_pct": 3, "pool_wait_ms": 3200, "db_cpu_pct": 44, "deploy_min_ago": 46},
        "Connection leak in retry wrapper",
        "Rolled back checkout v2.28 and patched the retry wrapper to close connections", 9, "resolved", "Arjun Mehta",
        ["db", "pool", "leak", "deploy"],
        "Connections climb monotonically and never drop after requests finish; DB CPU stays low."),

    inc("INC-1003", "2026-09-02T11:25:00+05:30", "checkout-api", "Cart reads slow after cache pressure", "SEV-3",
        "p99 1.8s on cart reads, cache hit rate 61%, Redis evictions 42k/min, DB CPU 39%.",
        {"p99_ms": 1800, "err_pct": 1, "cache_hit_pct": 61, "redis_evictions": 42000, "db_cpu_pct": 39},
        "Redis maxmemory-policy evicting sessions",
        "Switched maxmemory-policy to volatile-lru and raised the cache from 4GB to 8GB", 12, "resolved", "Sofia Alvarez",
        ["redis", "cache", "eviction"],
        "Eviction counter spikes first; DB latency follows the cache miss rate, not the reverse."),

    inc("INC-1004", "2026-09-14T09:05:00+05:30", "checkout-api", "Payment step fails after certificate rotation", "SEV-1",
        "Checkout payment step 5xx 14%; upstream TLS handshake failures; no latency ramp.",
        {"p99_ms": 1200, "err_pct": 14, "cert_age_days": 365, "tls_errors": 1},
        "Expired intermediate TLS certificate",
        "Rotated the gateway certificate chain and reloaded the ingress", 7, "resolved", "Priya Raman",
        ["tls", "cert", "gateway"],
        "Failures start exactly at the rotation timestamp; application metrics are flat."),

    inc("INC-1005", "2026-09-27T18:44:00+05:30", "checkout-api", "Checkout stalls in long GC pauses", "SEV-2",
        "p99 3.4s, GC pause 8.2s, heap 96% after cart payload grew 3x, DB CPU 31%.",
        {"p99_ms": 3400, "err_pct": 4, "gc_pause_ms": 8200, "heap_pct": 96, "db_cpu_pct": 31},
        "Undersized JVM heap after payload growth",
        "Raised the heap from 2g to 4g and capped cart line items at 200", 5, "resolved", "Dev Patel",
        ["jvm", "gc", "heap"],
        "Sawtooth heap with full GCs; downstream DB and pool metrics stay normal."),

    inc("INC-1006", "2026-10-12T14:22:00+05:30", "checkout-api", "Checkout p99 4.2s, pool exhausted", "SEV-1",
        "p99 4.2s, 12% 5xx, pool wait 3.4s, DB CPU 62%, deploy 14 min earlier added the order status filter.",
        {"p99_ms": 4200, "err_pct": 12, "pool_wait_ms": 3400, "db_cpu_pct": 62, "deploy_min_ago": 14},
        "Missing composite index on orders(created_at,status)",
        "Applied migration 2026_10_add_orders_index (CREATE INDEX CONCURRENTLY) and re-ran the query plan check", 6, "resolved", "Priya Raman",
        ["db", "index", "pool", "deploy"],
        "Pool wait high and DB CPU moderate; the deploy touched only the orders schema; pool size unchanged."),

    inc("INC-1007", "2026-10-21T12:10:00+05:30", "checkout-api", "Retry storm after downstream 503", "SEV-2",
        "Checkout 5xx 16%, request rate 4.1x baseline, pool wait 2.6s, upstream 503s, no deploy in 6h.",
        {"p99_ms": 2900, "err_pct": 16, "req_multiplier": 4.1, "pool_wait_ms": 2600, "deploy_min_ago": 380},
        "Retry storm without backoff",
        "Enabled the circuit breaker and added jittered exponential backoff to the client", 14, "resolved", "Arjun Mehta",
        ["retry", "circuit-breaker", "upstream"],
        "Request rate multiplies while unique users stay flat; upstream 503s precede our 5xx."),

    inc("INC-1008", "2026-10-29T16:35:00+05:30", "checkout-api", "Checkout slow during month-end reports", "SEV-3",
        "p99 3.8s for 20 minutes, DB CPU 95%, one long-running analytics query on the primary.",
        {"p99_ms": 3800, "err_pct": 2, "db_cpu_pct": 95, "long_query_s": 840},
        "Analytics query on primary database",
        "Killed the query, moved reporting to the read replica", 4, "resolved", "Sofia Alvarez",
        ["db", "analytics", "replica"],
        "Single query dominates DB CPU; pool wait stays low and there is no deploy."),

    inc("INC-1009", "2026-11-02T08:12:00+05:30", "checkout-api", "Checkout errors after pool config rollout", "SEV-2",
        "p99 3.8s, 9% 5xx, pool exhausted, pool size 8, DB CPU 41%, config rollout 2 min earlier.",
        {"p99_ms": 3800, "err_pct": 9, "pool_wait_ms": 2900, "db_cpu_pct": 41, "deploy_min_ago": 2, "pool_size": 8},
        "Connection pool size reduced by config rollout",
        "Reverted the pool size from 8 to 20; a restart alone only bought 30 minutes", 3, "recurred", "Tom Becker",
        ["db", "pool", "config"],
        "Pool size itself changed in the rollout; a restart temporarily masks it but the limit stays low."),

    inc("INC-2001", "2026-08-11T13:20:00+05:30", "payments-api", "Duplicate charges on retried payments", "SEV-1",
        "17 duplicate charges; retries reuse an idempotency key that collides across requests.",
        {"duplicates": 17, "err_pct": 0, "p99_ms": 700},
        "Idempotency key collision on retry",
        "Derived the key from request hash plus merchant id; replayed the dedupe job", 18, "resolved", "Nisha Rao",
        ["payments", "idempotency", "duplicates"],
        "Duplicates only on retried requests; the key is identical for different payloads."),

    inc("INC-2002", "2026-08-24T10:55:00+05:30", "payments-api", "Payment events backing up", "SEV-2",
        "Consumer lag 41k, rebalance loop every 90s, p99 2.1s, payments still succeed.",
        {"consumer_lag": 41000, "rebalance_s": 90, "p99_ms": 2100, "err_pct": 1},
        "Kafka consumer rebalance loop",
        "Raised max.poll.interval.ms to 600000 and cut max.poll.records to 200", 22, "resolved", "Dev Patel",
        ["kafka", "consumer", "lag"],
        "Lag grows in steps aligned with rebalances; processing time per batch exceeds the poll interval."),

    inc("INC-2003", "2026-09-05T19:30:00+05:30", "payments-api", "PSP outage amplified by retries", "SEV-1",
        "PSP returns 503 for 26 minutes; our error rate 31%, request rate 6x normal.",
        {"err_pct": 31, "req_multiplier": 6.0, "psp_status": 503, "p99_ms": 8000},
        "Upstream PSP outage",
        "Enabled the circuit breaker, queued failed charges, replayed after recovery", 31, "resolved", "Priya Raman",
        ["psp", "upstream", "circuit-breaker"],
        "Failures are all upstream 503s; our own DB and pool metrics are flat."),

    inc("INC-2004", "2026-09-18T14:08:00+05:30", "payments-api", "Payment writes deadlock under load", "SEV-2",
        "p99 6.1s, lock wait 4.8s, deadlock count 37/min, DB CPU 55%.",
        {"p99_ms": 6100, "lock_wait_ms": 4800, "deadlocks_per_min": 37, "db_cpu_pct": 55},
        "Out-of-order row updates causing deadlock",
        "Ordered updates by payment_id and added a retry with jitter", 11, "resolved", "Arjun Mehta",
        ["db", "deadlock", "lock"],
        "Deadlock graph shows two sessions updating the same rows in opposite order."),

    inc("INC-2005", "2026-10-03T11:42:00+05:30", "payments-api", "Duplicates return after dedupe deploy", "SEV-1",
        "9 duplicate charges after the dedupe service deploy; idempotency cache key changed.",
        {"duplicates": 9, "err_pct": 0, "deploy_min_ago": 21, "p99_ms": 650},
        "Idempotency cache key changed in deploy",
        "Rolled back the dedupe service and replayed the affected window", 16, "resolved", "Nisha Rao",
        ["payments", "idempotency", "deploy"],
        "Duplicates start at the deploy timestamp; the key format differs from the previous version."),

    inc("INC-2006", "2026-10-17T09:18:00+05:30", "payments-api", "PSP timeouts after regional failover", "SEV-2",
        "PSP connect timeout 30s for 12 minutes after a regional failover; DNS resolves to the old IP.",
        {"p99_ms": 30000, "err_pct": 22, "dns_ttl_s": 300, "failover": 1},
        "Stale DNS record after failover",
        "Lowered the TTL to 30s and flushed the resolver cache", 8, "resolved", "Sofia Alvarez",
        ["dns", "failover", "psp"],
        "Connections go to an IP that no longer serves traffic; the new IP is healthy."),

    inc("INC-2007", "2026-10-25T17:50:00+05:30", "payments-api", "Payment threads pinned after audit change", "SEV-2",
        "p99 4.6s, thread pool 98% active, throughput flat, deploy 30 min earlier added a synchronous audit call.",
        {"p99_ms": 4600, "thread_pool_pct": 98, "err_pct": 6, "deploy_min_ago": 30},
        "Synchronous audit call on hot path",
        "Moved the audit write to an async queue and reverted the blocking call", 13, "resolved", "Dev Patel",
        ["threads", "audit", "deploy"],
        "Threads block on a downstream call that is not on the critical path; CPU is low."),

    inc("INC-3001", "2026-08-15T08:05:00+05:30", "auth-api", "Login failures on new node pool", "SEV-2",
        "Login 401s at 30% for 9 minutes; failures only on the new node pool; clocks differ by 90s.",
        {"err_pct": 30, "clock_skew_s": 90, "nodes_affected": 3},
        "JWT clock skew across node pool",
        "Enabled NTP on the pool and set a 60s leeway on JWT validation", 6, "resolved", "Nisha Rao",
        ["auth", "jwt", "clock"],
        "Only one node pool fails; token iat/exp look valid when checked on the healthy pool."),

    inc("INC-3002", "2026-08-30T12:33:00+05:30", "auth-api", "All users rate limited behind office NAT", "SEV-2",
        "429s for every user behind one office NAT; other networks unaffected; limiter keyed on IP.",
        {"err_pct": 100, "scope": "nat", "rps": 220},
        "Rate limiter keyed on NAT IP",
        "Changed the limiter key to user id with an IP fallback for anonymous traffic", 9, "resolved", "Tom Becker",
        ["auth", "rate-limit", "nat"],
        "All failures share one source IP; per-user request counts are normal."),

    inc("INC-3003", "2026-09-09T15:40:00+05:30", "auth-api", "Sessions dropped during Redis failover", "SEV-2",
        "Session validation 5xx 12% during a Redis failover; sentinel promoted the wrong replica.",
        {"err_pct": 12, "redis_failover": 1, "sentinel_quorum": 1},
        "Redis sentinel quorum misconfigured",
        "Fixed the sentinel quorum to 2 and pinned the preferred replica", 15, "resolved", "Arjun Mehta",
        ["redis", "sentinel", "session"],
        "Two sentinels disagree about the primary; the promoted node has stale session data."),

    inc("INC-3004", "2026-09-22T10:12:00+05:30", "auth-api", "Login latency after JWKS change", "SEV-3",
        "Login p99 2.1s, JWKS endpoint called on every request, 3.2k req/s.",
        {"p99_ms": 2100, "err_pct": 0, "jwks_calls_per_req": 1},
        "JWKS fetched per request (no cache)",
        "Cached signing keys for one hour with a background refresh", 4, "resolved", "Sofia Alvarez",
        ["auth", "jwks", "cache"],
        "CPU is low; every login makes an outbound JWKS call."),

    inc("INC-3005", "2026-10-06T09:25:00+05:30", "auth-api", "Auth 5xx after signing key rotation", "SEV-1",
        "Auth 5xx 19% right after the expired signing key was rotated; tokens signed with a kid that is not in JWKS.",
        {"err_pct": 19, "cert_age_days": 365, "key_rotation": 1, "p99_ms": 400},
        "Expired JWT signing key",
        "Published the new kid in JWKS and kept the old key for the overlap window", 7, "resolved", "Priya Raman",
        ["auth", "jwt", "keys", "certificate", "expired"],
        "Failures start at the rotation timestamp; the old kid still validates."),

    inc("INC-3006", "2026-10-19T13:55:00+05:30", "auth-api", "Login failures after service discovery change", "SEV-2",
        "Login failures 8% for 20 minutes; service discovery TTL is 5 minutes and one instance is gone.",
        {"err_pct": 8, "dns_ttl_s": 300, "stale_instance": 1, "p99_ms": 1800},
        "DNS TTL too high for service discovery",
        "Dropped the discovery TTL to 30s and deregistered the dead instance", 10, "resolved", "Dev Patel",
        ["dns", "discovery", "auth"],
        "A fraction of requests hit an instance that no longer exists; the endpoint is healthy."),

    inc("INC-4001", "2026-08-21T23:10:00+05:30", "ledger-worker", "Ledger backlog grows overnight", "SEV-2",
        "Ledger lag 3h, batch of 1000 times out at 45s, CPU 40%.",
        {"lag_min": 180, "batch_size": 1000, "timeout_s": 45, "cpu_pct": 40},
        "Ledger batch size too large",
        "Cut the batch to 250 and raised the timeout to 90s", 12, "resolved", "Nisha Rao",
        ["ledger", "batch", "worker"],
        "Lag grows linearly with batch size; each batch times out at the same wall-clock limit."),

    inc("INC-4002", "2026-09-12T02:30:00+05:30", "ledger-worker", "Duplicate ledger entries after replay", "SEV-1",
        "1.2k duplicate entries after replaying a failed batch; at-least-once delivery without dedupe.",
        {"duplicates": 1200, "lag_min": 15, "replay": 1},
        "At-least-once delivery without dedupe",
        "Deduped on transaction id and made the ledger write idempotent", 20, "resolved", "Arjun Mehta",
        ["ledger", "dedupe", "replay"],
        "Duplicates share a transaction id; they all arrive from the replay window."),

    inc("INC-4003", "2026-10-09T01:15:00+05:30", "ledger-worker", "Settlement lag after new report", "SEV-2",
        "Ledger lag 90 min, settlement query scans 4M rows, CPU 70%.",
        {"lag_min": 90, "db_cpu_pct": 70, "long_query_s": 300},
        "Missing index on settlement_date",
        "Added an index on settlement_date and moved the report off the hot path", 8, "resolved", "Sofia Alvarez",
        ["ledger", "db", "index"],
        "Query plan shows a sequential scan; pool metrics are normal."),

    inc("INC-4004", "2026-10-28T04:50:00+05:30", "ledger-worker", "Ledger worker OOM loop", "SEV-2",
        "Worker OOM every 20 minutes, heap climbs with the in-memory aggregation, lag 45 min.",
        {"oom_per_hour": 3, "heap_pct": 99, "lag_min": 45},
        "Unbounded in-memory aggregation",
        "Switched to streaming aggregation with a cap of 50k rows per window", 9, "resolved", "Tom Becker",
        ["ledger", "memory", "worker"],
        "Heap climbs in a straight line between restarts; input size is stable."),

    inc("INC-1014", "2026-09-08T17:20:00+05:30", "checkout-api", "Checkout slow at month-end close", "SEV-3",
        "p99 3.6s for 25 minutes at month-end; DB CPU 93%; one reporting query on the primary; pool wait normal.",
        {"p99_ms": 3600, "err_pct": 1, "db_cpu_pct": 93, "long_query_s": 720, "pool_wait_ms": 200},
        "Month-end report saturates the primary",
        "Moved the close report to the replica and capped it at 5 minutes", 5, "resolved", "Sofia Alvarez",
        ["db", "reporting", "replica"],
        "DB CPU saturates while pool wait stays low; the query starts at the scheduled close time."),

    inc("INC-1010", "2026-09-30T09:45:00+05:30", "checkout-api", "Checkout pool capped by config service", "SEV-2",
        "p99 3.7s, 8% 5xx, pool wait 2.8s, pool size 6 after the config service pushed defaults, DB CPU 38%.",
        {"p99_ms": 3700, "err_pct": 8, "pool_wait_ms": 2800, "db_cpu_pct": 38, "deploy_min_ago": 7, "pool_size": 6},
        "Config service pushed a low pool ceiling",
        "Raised the pool ceiling to 20 in the config service and pinned it per environment", 4, "resolved", "Tom Becker",
        ["db", "pool", "config"],
        "Pool size itself is low; DB CPU and query latency are normal once a connection is acquired."),

    inc("INC-3011", "2026-09-25T08:20:00+05:30", "auth-api", "Login 401s after edge nodes drifted", "SEV-2",
        "Login 401s at 22%, only on edge nodes, token validation fails with iat in the future, clock skew 70s.",
        {"err_pct": 22, "clock_skew_s": 70, "nodes_affected": 4, "p99_ms": 500},
        "NTP drift on edge nodes",
        "Forced NTP sync on the edge pool and added a 90s validation leeway", 5, "resolved", "Nisha Rao",
        ["auth", "jwt", "clock"],
        "Only edge nodes fail; the token is valid on the core pool, and the iat is in the future."),

    inc("INC-2010", "2026-10-11T18:05:00+05:30", "payments-api", "PSP 502 burst with no breaker", "SEV-1",
        "PSP returns 502 for 18 minutes; our 5xx 24%, request rate 5x, no circuit breaker configured.",
        {"err_pct": 24, "req_multiplier": 5.0, "psp_status": 502, "p99_ms": 7000},
        "PSP 502 burst with no circuit breaker",
        "Enabled the circuit breaker and queued failed charges for replay", 27, "resolved", "Priya Raman",
        ["psp", "upstream", "circuit-breaker"],
        "All failures are upstream 502s; our DB, pool and CPU stay flat."),

    inc("INC-3012", "2026-10-23T11:10:00+05:30", "auth-api", "Mobile users rate limited in bulk", "SEV-2",
        "429s for 6% of mobile users; all share one carrier NAT IP; per-user request counts are normal.",
        {"err_pct": 6, "scope": "nat", "rps": 180},
        "Carrier NAT reuses one IP for thousands of users",
        "Keyed the limiter on user id and added a per-IP ceiling only for anonymous traffic", 8, "resolved", "Tom Becker",
        ["auth", "rate-limit", "nat"],
        "Failures share one carrier IP while user-level rates are normal; desktop traffic is unaffected."),

    inc("INC-3013", "2026-11-01T10:30:00+05:30", "auth-api", "Login slow, JWKS refetched constantly", "SEV-3",
        "Login p99 2.4s, JWKS endpoint hit 3.4k times/s, cache TTL set to 60s, CPU low.",
        {"p99_ms": 2400, "err_pct": 0, "jwks_calls_per_req": 1, "cache_ttl_s": 60},
        "JWKS cache invalidated every minute",
        "Raised the JWKS cache to one hour with a background refresh and a single-flight fetch", 4, "resolved", "Sofia Alvarez",
        ["auth", "jwks", "cache"],
        "Every login makes an outbound JWKS call; CPU is low and there is no error spike."),

    inc("INC-2011", "2026-10-30T03:20:00+05:30", "payments-api", "Deadlocks during batch reconciliation", "SEV-2",
        "p99 5.8s, deadlock count 22/min, lock wait 4.2s, a nightly reconciliation job updates rows in random order.",
        {"p99_ms": 5800, "lock_wait_ms": 4200, "deadlocks_per_min": 22, "db_cpu_pct": 51},
        "Batch reconciliation updates rows out of order",
        "Sorted the reconciliation batch by payment_id and added a bounded retry", 12, "resolved", "Arjun Mehta",
        ["db", "deadlock", "batch"],
        "Deadlocks start with the reconciliation job; the same rows succeed when updated in id order."),
]


def postmortem(i: dict) -> str:
    return (
        f"{i['title']}. {i['symptom']}\n\n"
        f"Root cause: {i['root_cause']}.\n"
        f"Fix: {i['fix']} ({i['fix_minutes']:.0f} min).\n"
        f"Outcome: {i['outcome']}.\n"
        f"How we told it apart: {i['discriminator']}\n"
        f"Responder: {i['engineer']}."
    )


def memory_text(i: dict) -> str:
    sig = ", ".join(f"{k}={v}" for k, v in i["signals"].items())
    return (
        f"INCIDENT {i['id']} | {i['ts'][:10]} | {i['service']} | {i['severity']}\n"
        f"TITLE: {i['title']}\n"
        f"SYMPTOM: {i['symptom']}\n"
        f"SIGNALS: {sig}\n"
        f"ROOT CAUSE: {i['root_cause']}\n"
        f"CAUSE CLASS: {i['cause_class']}\n"
        f"FIX: {i['fix']}\n"
        f"RESOLUTION TIME: {i['fix_minutes']:.0f} minutes\n"
        f"OUTCOME: {i['outcome']}\n"
        f"RESPONDER: {i['engineer']}\n"
        f"DISCRIMINATOR: {i['discriminator']}"
    )


def seed_memories(con) -> None:
    for i in INCIDENTS:
        pm = postmortem(i)
        con.execute(
            "INSERT OR REPLACE INTO incidents (id,ts,service,title,severity,symptom,signals,root_cause,"
            "cause_class,fix,fix_minutes,outcome,engineer,tags,discriminator,postmortem) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (i["id"], i["ts"], i["service"], i["title"], i["severity"], i["symptom"],
             json.dumps(i["signals"]), i["root_cause"], i["cause_class"], i["fix"], i["fix_minutes"],
             i["outcome"], i["engineer"], json.dumps(i["tags"]), i["discriminator"], pm),
        )
        success = 1 if i["outcome"] == "resolved" else 0
        fail = 0 if i["outcome"] == "resolved" else 1
        # history weight: repeated root causes have been seen more than once
        repeats = sum(1 for x in INCIDENTS if x["root_cause"] == i["root_cause"])
        con.execute(
            "INSERT OR REPLACE INTO memories (id,incident_id,bank,text,service,root_cause,cause_class,fix,outcome,"
            "fix_minutes,engineer,created_at,last_confirmed,success_count,fail_count,stale,source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"MEM-{i['id']}", i["id"], "dejavu-oncall", memory_text(i), i["service"],
             i["root_cause"], i["cause_class"], i["fix"], i["outcome"], i["fix_minutes"], i["engineer"],
             i["ts"], i["ts"], success * repeats, fail * (1 if repeats > 1 else 1),
             1 if i["ts"] < "2026-06-01" else 0, "seed"),
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="delete the database first")
    args = ap.parse_args()
    if args.fresh and db.DB_PATH.exists():
        for suffix in ("", "-wal", "-shm"):
            p = db.DB_PATH.with_name(db.DB_PATH.name + suffix)
            if p.exists():
                p.unlink()
    db.ready()
    with db.connect() as con:
        seed_memories(con)
    c = db.counts()
    print(f"seeded {c['incidents']} incidents and {c['memories']} memories into {db.DB_PATH}")
    print("services:", sorted({i['service'] for i in INCIDENTS}))
    print("span:", INCIDENTS[1]['ts'][:10], "->", INCIDENTS[-1]['ts'][:10])


if __name__ == "__main__":
    main()
