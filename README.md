# Rules

This repository studies reusable host rules and application behavior through executable models, proofs, and attributable observations. Start with the [plain-language review](review.md) for a file update, a world update, and where Bend and Lean run. The [common model](common/README.md) lists the underlying laws. Models use mathematical naturals for bounded host quantities. Adapters must reject overflow, invalid units and foreign identities before applying those models.

For the six host surfaces, see the [host behavior map](host/README.md), [native and Java profile matrix](profiles/README.md), and [qualification evidence](host/evidence.md). The [application lifecycle study](host/lifecycles/README.md) extends those rules through retained assets, concurrent saves, native editors, and browser hosts. The [terminal application study](terminal/README.md) compares npm, pnpm, Yarn, and empack, with [UX findings and proposed empack changes](terminal/report.md).

| Project                            | Reprojection and evidence                                                                                                                        |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Moment](moment/README.md)         | Historical comparison from immutable records and contextual support to a visible relation, a wake occurrence and a separately admitted execution |
| [Playground](playground/README.md) | From owned reservations and spatial observations to coherent tick candidates and derived presentation                                            |
| [empack](empack/README.md)         | From author intent, terminal observations and resource estimates to a verified plan, managed publication and installed ownership                 |
| [Simulacrum](simulacrum/README.md) | Receptor observations, staged delivery and cursor semantics                                                                                      |
| [re:desktop](re-desktop/README.md) | Human pause, per-session grants, epochs and clocks                                                                                               |

The [application study](applications/README.md) owns the feature-by-feature inventory, per-program models, and design proposals. Its evidence status is tracked per operation. The first [restic retention model](applications/restic/README.md) covers a bounded snapshot lifecycle.

The [Minecraft host study](host/minecraft/README.md) maps resource and graphics definitions and their actual consumers across selected editions, releases, loaders, and Modefite/Polytone/Compat variants. Its initial comparison nodes and expanded versioned research remain in progress; the breadth inventory does not establish capability or completed proofs.

## Check the models

The [development guide](docs/development.md) covers pinned tool setup and checks from a fresh clone. Start with:

```sh
python3 scripts/setup-tools.py
# Add the installed Bend and Lean bin directories to PATH.
python3 scripts/check-rules.py
```

The rules check typechecks tracked Lean modules and rechecks Bend laws. CI runs it once, then compares emitted rules on macOS, Linux, and Windows with bounded host fixtures. Application evidence collection and optional sibling-checkout comparisons follow their own documented procedures.

See [contributing](CONTRIBUTING.md), [repository conventions](docs/repository.md), and [security](SECURITY.md) for participation and maintenance.

[Source pins](sources.json) record Git revisions and blob IDs. Run the checks after changing a projection. When a tracked source changes, inspect the changed boundary and its tests before advancing the pin. Model proofs cover the stated abstractions. The source probes cover individual adapter cases. Neither amounts to translation validation of an entire host application.

Where an inspected upstream file had uncommitted changes, the manifest records its observed working-tree blob separately from its committed blob. Restoring or advancing that source requires a fresh comparison. The local rules repository does not modify the project checkouts.

## Verification boundaries

| Project    | Executable comparison                                                                                                                                                                                       | Adapter boundary                                                                                                                                                                                  |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Moment     | The graph probe calls the actual mutation and topology functions. The Lean reaction example follows an event through proposal and commit, including revocation between those stages.                        | The model takes authenticated action, lease and receipt observations as inputs. SQLite durability and real provider effects need integration tests.                                               |
| Playground | The compiled probe calls the native resource ledger. The Lean tick example connects a reservation and halo reads to world publication and a later device generation check.                                  | A new world can commit while its GPU result is still unavailable. Partition and replay proofs apply to the specified kernels. GPU and physics completion require host observations.               |
| empack     | The differential test compares all 245 normalized single-file cases with Rust. The Lean release example follows an authenticated channel selection through capacity, content verification and installation. | Trust verification, portable metadata, rooted filesystem operations and actual process control belong to the host. A refused install can still advance the authenticated channel high-water mark. |
| Simulacrum | Lean examples exercise first discovery, flush outcome and equal timestamps.                                                                                                                                 | Source inspection supplies the cursor rule. Database crash recovery and analytics delivery have no native parity test here.                                                                       |
| re:desktop | The source check runs 13 Bend laws. The desktop comparison checks renewal and Pause after against the emitted core as used by the host coordinator.                                                         | Disconnect, timer delivery and foreground focus are external observations.                                                                                                                        |

Run the additional native comparisons from this directory with the sibling checkouts present:

```sh
scripts/compare-empack
scripts/compare-desktop
(cd ../moment && node --test test/scheduler.test.mjs)
(cd ../empack && cargo test --locked --offline -p empack-lib --lib engine::resources::tests)
(cd ../empack && cargo test --locked --offline -p empack-lib --lib terminal::capabilities::tests -- --test-threads=1)
```

The reference run on macOS arm64 passed 11 scheduler tests, six governor tests and 20 terminal capability tests. Cargo needs the source checkout's dependencies in its local cache for these offline commands. The manifest uses a null committed blob for a file present only in the inspected working tree. Reproducing that part of the comparison requires the separately recorded working-tree content.
