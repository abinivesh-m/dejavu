from dejavu import agent, db, memory

print("modules:", memory.__file__)

inc = db.get_incident("INC-1004")
print(inc["title"], inc["signals"])
alert = {"service": inc["service"], "title": inc["title"], "body": inc["symptom"],
         "signals": db.json_load(inc["signals"])}
rows = [dict(r) for r in db.connect().execute("SELECT * FROM memories WHERE created_at < ?", (inc["ts"],)).fetchall()]
print("window:", [(r["incident_id"], r["service"]) for r in rows])
hits, detail = memory._bm25(agent.build_query(alert), rows, 10)
print("\nBM25 hits:")
for h in hits:
    print(f"  {h['incident_id']} {h['root_cause'][:40]:40s} text={h['score']}")
print("\nRANK:")
for g in agent.rank(hits, alert["signals"]):
    print(f"  {g['root_cause'][:45]:45s} sim={g['similarity']} sig={g['signal_similarity']} txt={g['text_similarity']} cov={g['coverage']} score={g['score']}")
