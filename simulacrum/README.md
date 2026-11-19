# Simulacrum

The replay receptor discovers session files, decodes JSONL, routes typed entries to staging tables, flushes to production and optionally records a cursor. Parsing policy can skip malformed entries in resilient mode. A durable cursor records a session mtime and descriptive metadata. Selection compares mtime strictly against the cursor timestamp. Two distinct files sharing the same timestamp are a counterexample to treating timestamp equality as identity or exactly-once delivery.

[Model.lean](Model.lean) checks first-run selection, strict ordering and cursor retention when flush fails. The model abstracts staging transactions and crash windows between flush and cursor update. Downstream analytics need provenance and an explicit duplicate policy. A receptor observation does not prove its subject's claim or supply authority for an action. [Source pins](../sources.json)
