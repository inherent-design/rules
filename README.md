# Rules

This local repository compares the laws behind five systems. Start with the [common model](common/README.md), then follow a boundary into the corresponding project. Models use mathematical naturals for bounded host quantities. Adapters must reject overflow, invalid units and foreign identities before applying those models.

| Project | Reprojection and evidence |
| --- | --- |
| [Moment](moment/README.md) | Historical comparison from immutable records and contextual support to a visible relation, a wake occurrence and a separately admitted execution |
| [Playground](playground/README.md) | From owned reservations and spatial observations to coherent tick candidates and derived presentation |
| [empack](empack/README.md) | From author intent, terminal observations and resource estimates to a verified plan, managed publication and installed ownership |
| [Simulacrum](simulacrum/README.md) | Receptor observations, staged delivery and cursor semantics |
| [re:desktop](re-desktop/README.md) | Human pause, per-session grants, epochs and clocks |

## Check the models

Use Lean 4.34.0 and Bend 2.0.40 on PATH, including the Lean binary for Bend's independent verdict. With the existing sibling re-desktop installation on macOS arm64:

```sh
export PATH="$PWD/../re-desktop/.tools/lean-4.34.0-darwin_aarch64/bin:$PWD/../re-desktop/.tools/bend/bin:$PATH"
scripts/check
scripts/check-sources
```

The first command typechecks all five models, their examples and the generic theorems, checks the Bend laws through the Lean-based kernel and runs a terminal replay. The second checks the recorded source files, runs the Moment graph and Playground ledger probes against the working checkouts, and verifies re:desktop's seven Bend laws. Build products stay in `.build/`. No service or remote is required. For live terminal observations and reproducible fault cases see [empack](empack/README.md).

[Source pins](sources.json) record Git revisions and blob IDs. Run the checks after changing a projection. When a tracked source changes, inspect the changed boundary and its tests before advancing the pin. Model proofs cover the stated abstractions. The source probes cover individual adapter cases. Neither amounts to translation validation of an entire host application.

Where an inspected upstream file had uncommitted changes, the manifest records its observed working-tree blob separately from its committed blob. Restoring or advancing that source requires a fresh comparison. The local rules repository does not modify the project checkouts.

## Verification boundaries

| Project | Executable comparison | Adapter boundary |
| --- | --- | --- |
| Moment | The graph probe calls the actual mutation and topology functions. The Lean reaction example follows an event through proposal and commit, including revocation between those stages. | The model takes authenticated action, lease and receipt observations as inputs. SQLite durability and real provider effects need integration tests. |
| Playground | The compiled probe calls the native resource ledger. The Lean tick example connects a reservation and halo reads to world publication and a later device generation check. | A new world can commit while its GPU result is still unavailable. Partition and replay proofs apply to the specified kernels. GPU and physics completion require host observations. |
| empack | The differential test compares all 245 normalized single-file cases with Rust. The Lean release example follows an authenticated channel selection through capacity, content verification and installation. | Trust verification, portable metadata, rooted filesystem operations and actual process control belong to the host. A refused install can still advance the authenticated channel high-water mark. |
| Simulacrum | Lean examples exercise first discovery, flush outcome and equal timestamps. | Source inspection supplies the cursor rule. Database crash recovery and analytics delivery have no native parity test here. |
| re:desktop | The source check runs seven Bend laws. The renewal comparison checks Lean against the emitted core and the host coordinator for accepted renewal, a stale epoch and a wrong caller. | Disconnect, timer delivery and foreground focus are external observations. |

Run the additional native comparisons from this directory with the sibling checkouts present:

```sh
scripts/compare-empack
scripts/compare-desktop
(cd ../moment && node --test test/scheduler.test.mjs)
(cd ../empack && cargo test --locked --offline -p empack-lib --lib engine::resources::tests)
(cd ../empack && cargo test --locked --offline -p empack-lib --lib terminal::capabilities::tests -- --test-threads=1)
```

The reference run on macOS arm64 passed 11 scheduler tests, six governor tests and 20 terminal capability tests. Cargo needs the source checkout's dependencies in its local cache for these offline commands. The manifest uses a null committed blob for a file present only in the inspected working tree. Reproducing that part of the comparison requires the separately recorded working-tree content.
