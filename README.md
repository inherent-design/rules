# Rules

This local repository compares the laws behind five systems. Start with the [common model](common/README.md), then follow a boundary into the corresponding project. Models use mathematical naturals for bounded host quantities. Adapters must reject overflow, invalid units and foreign identities before applying those models.

| Project | Reprojection and evidence |
| --- | --- |
| [Moment](moment/README.md) | From immutable records and contextual support to a visible relation, a wake occurrence and a separately admitted execution |
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

The first command typechecks all five models, their examples and the generic theorems, checks the Bend laws through the Lean-based kernel and runs a terminal replay. The second checks the recorded source files, runs the Moment graph and Playground ledger probes against the working checkouts, and verifies re:desktop's original six Bend laws. Build products stay in `.build/`. No service or remote is required. For live terminal observations and reproducible fault cases see [empack](empack/README.md).

[Source pins](sources.json) record Git revisions and blob IDs. Run the checks after changing a projection. When a tracked source changes, inspect the changed boundary and its tests before advancing the pin. Model proofs cover the stated abstractions. The source probes cover individual adapter cases. Neither amounts to translation validation of an entire host application.

Where an inspected upstream file had uncommitted changes, the manifest records its observed working-tree blob separately from its committed blob. Restoring or advancing that source requires a fresh comparison. The local rules repository does not modify the project checkouts.
