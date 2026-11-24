# Application domain models and UX

This is the active successor to the [terminal study](../terminal/README.md). It covers empack, npm, pnpm, Yarn Berry, Mod Organizer 2, Prism Launcher, Cargo, restic, and VS Code desktop/vscode.dev. The scope is each application's domain and meaningful features, not a list of ways other programs resemble empack.

The first [inventory](inventory.json) maps 208 feature families and 971 semantic operations across all nine applications. Those counts describe decomposition, not verification. Operation names are research identifiers, not assertions that a program exposes a command with that spelling. Every operation begins pending. Reading help or a contract establishes an inventory basis, not implementation conformance. The inventory is the single maintained feature/assessment source; its one-off initialization generator has been retired.

## Evidence and ownership

The application owner writes only `applications/**`. The host owner writes shared lifecycle primitives, host/profile adapters, root navigation, and shared checks. `terminal/**` remains a preserved baseline. No production empack or comparator source changes are authorized by this analysis.

Each feature must eventually link its domain values/relations, transition model, explicit invariants, Bend decision or trace, Lean laws, native/source comparison, counterexample, UX finding, compatibility obligations, and verification plan. Cross-feature scenarios must also exercise the shared state. A feature cannot become covered because a nearby feature passed or because one operation is modeled.

[Source and tool pins](sources/local-pins.json) distinguish current empack checkout contracts from the released 0.8.8 binary. Official source refs and release metadata are retained beside them. Native root help lives under `evidence/inventory-20261123/`, using private config/state directories. Prism's attempted offscreen help failed because this macOS build provides only Qt's Cocoa platform plugin. That is an unavailable fixture profile, not evidence of a broken installation. Restic is acquired only under ignored `tools/`; it matches the official asset digest and checksum file. Restic backup and maintenance were exercised only on isolated fixture repositories; personal repositories were untouched.

MO2 2.5.2 requires Windows 10 1809+ or Windows 11. Its native Windows behavior is not qualified on this Mac. VS Code desktop 1.147 and the browser service have separately identified evidence obligations; a shared UI does not establish equal filesystem, extension, or process capabilities. Vortex and Yarn Classic have not been selected.

The first [restic band](restic/README.md) has source/native/model evidence for a selected local snapshot-forget/prune/restore flow. The first [Cargo band](cargo/README.md) compares workspace metadata, selected build features, build-script input declarations, and cleanup. Both leave their other operations and most application models pending. [Inventory checks](check_inventory.py) verify structure and bookkeeping constraints, not product correctness.

## Working order

1. Reconcile the broad inventory against help, schemas, source modules, owning contracts, plugins, and actual supported interfaces. Keep every feature's evidence status explicit.
2. Populate bounded application-specific state models across the inventory before deepening a small set. Establish the domain meaning before proposing shared host primitives.
3. Test models against native/source behavior, negative controls, and joined lifecycles. Preserve contradictions and unavailable platform cells.
4. Derive proposals for multiple applications and a coherent empack current/0.9 internal model/interface design. Include keep-current alternatives, serialized/API compatibility, ownership, key custody, and falsifiable acceptance plans.
5. Review the complete proposals with the host owner. Production implementation needs a separately selected decision.

The canonical active checkpoint is in the Moment incident for the application-models intent. It is the only current task checkpoint. Repository artifacts carry evidence and coverage, not a second running task ledger.
