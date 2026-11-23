# Qualification on November 23, 2026

The emitted Bend classifiers matched Lean on all **64 input combinations** across eight decisions. Seven Bend laws passed their separate kernel verdict. The host comparisons matched **103 native observation rows**, including repeated baseline checks on six exact OS/JDK combinations. The same scenario can produce multiple rows. These are comparisons on fixtures with declared premises, not 103 independent guarantees.

The [observations](observations.json) retain each normalized row once, with an ordered list of zero-based row references and a raw JSON-lines digest for each run. A digest identifies the captured bytes. Re-running a producer can change insignificant serialization order. Recheck decoded facts and outcomes.

| Subject | Actual check | Outcome and limits |
| --- | --- | --- |
| Common model | `scripts/check-host` with Lean 4.34.0 and Bend 2.0.40 | Kernel verdict, warnings-as-errors Lean compilation, full finite classifier comparison, ported Windows fence edge cases, and negative verifier controls passed. The admission proof assumes current evidence and a serialized effect boundary. |
| macOS | The same script ran `python3 host/native.py`, compiled and ran `host/LedgerProbe.cpp` against Playground, and compiled and ran `host/MetalProbe.swift`. | 24 POSIX/application rows, two C++ ledger rows, and five Metal/application rows. Real command buffer and successful byte readback. World generation, device mismatch, and withdrawn demand were controlled inputs, not a physical device removal. |
| GNU/Linux | Ran `python3 host/native.py` inside an Ubuntu guest using the same study source and private stream fixture. Fed its JSON lines to `node host/compare.mjs` on macOS. | 24 rows. Real Linux kernel, glibc, ext4, PTY, loopback, file locks, and SQLite. No native Linux GPU node. The guest had no Darwin or Windows APIs. |
| Java | Ran `host/java/check JDK_HOME FEATURE` once for each named JDK on each host. Passed all six JSON-lines files to the same verifier. | 6, 8, and 10 decision rows for versions 17, 21, and 25 respectively on each OS. Each also ran both stream topologies and recorded the console observation separately. No preview flags. |
| Windows | `zig cc -target x86_64-windows-gnu -Wall -Werror host/WinProbe.c -o .build/WinProbe.exe`, Zig 0.17.1. `file` identified PE32+ x86-64. | Compile and artifact inspection passed. No Windows execution, real console, NTFS failure injection, D3D12 device, or Windows JDK comparison. The BigInt fence decoder’s removal and precision cases passed locally. |
| Consumer baselines | `scripts/check` and `scripts/compare-empack` | Existing rules passed; 245 normalized Rust planner decisions matched Lean. Compared the application code and reviewer’s source references at empack 0b4462e3 and Playground d7a1c99. The upstream SDL graphics test was inspected, not rerun. |

The historical whole-repository source gate, `scripts/check-sources`, still stops on drift at `moment/docs/reference/model.md`. That comparison and its historical pins were left with their existing owner. The targeted host comparisons above ran independently.

The comparison command on the coordinating host was:

```sh
scripts/check-host .build/{mac,linux}-jdk{17,21,25}.jsonl .build/linux-host.jsonl
```

The Linux guest used Lima 2.3.0 with Apple VZ, two CPUs, 3 GiB RAM, a 10 GiB logical guest disk, plain networking, and no host mounts. The Ubuntu 24.04 arm64 input image was the 20261017 release, pinned SHA-256 `50e24e1fb79e89116e939d90aa7738f7af48c442fa1bc2510131e0b39c50348e`. The three guest JDK packages were the distribution’s headless builds. The [profile matrix](../profiles/README.md) records their exact identities. The VM was stopped normally after all Linux probes finished and the host had read their receipts.

## What can be reproduced or challenged

- **Decode and observation.** The stream mask round-trips all eight combinations. Independent child and launcher observations agree in both actual layouts. Unknown or absent trace versions, missing Boolean evidence, and a deliberately wrong outcome are refused.
- **Ordering.** A working thread remained live after cancellation of its Java Future. A later native outcome is possible. The Lean writer-order counterexample shows why checking content and writing in separate operations can lose an intervening edit.
- **Uncertainty and recovery.** The native TCP fixture withheld the acknowledgement in both a committed and an unapplied case. Lean rules out any function that recovers the actual commit solely from that missing receipt. Authentication, distributed transaction durability, and exactly-once delivery are outside the experiment.
- **Ownership.** The Playground counterexample changed the shared publication and reuse predicates. A healthy compatible pool can recycle an entry only after other owners and uses release it. Report successful completion, consumer readiness, and final release independently.
- **What a failure says.** The same exit status produced different project effects in the native control. One observed pnpm run did change project state before exit 1. The check records changes per scope and makes no claim about writes that returned to the same snapshot.

To extend coverage, run the Windows executable and JDK fixtures on the named system first. For stronger durability claims, specify the filesystem, barriers, and admissible crash boundary and capture independent recovery evidence. For GPU or subscription guarantees, retain the exact queue, resource generation, or recipient basis and observe the consuming API. Advance a profile only for the claim that evidence supports.
