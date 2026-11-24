# Direct declarations, retained dependencies, and re-adoption

Removing a direct dependency declaration does not necessarily remove that package from the installed dependency graph. This band follows that distinction through npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0, using the same pinned Node 26.13.1 and Mac as the [peer-context study](README.md). It covers normal single-project editing, not interruption or package-manager atomicity.

## Fixture and observations

Two generated local archives provide `fixture-parent` and `fixture-leaf`. The parent requires the exact local leaf archive and loads it when Node loads the parent. Initially the project declares both. The collector disables lifecycle scripts, uses private homes/configuration/caches, and selects offline or disabled-network operation. It does not open a personal project or alter an installed global tool.

The [native receipt](../evidence/js-removal-20261124T042813469322Z/receipt.json), [trace](../evidence/js-removal-20261124T042813469322Z/trace.json), saved manifests/locks, and raw streams retain 36 invocations: six editing/install commands and six independent Node observations per tool. The exact collector bytes are captured at startup. The retained private work occupies about 2.7 MiB; caches are outside Git.

| Step | Shared observation |
| --- | --- |
| Install both direct declarations | The parent and leaf load successfully. |
| Remove the leaf declaration | The declaration disappears; the parent still loads its required leaf. |
| Remove that transitive-only leaf again | The measured manifest and lock stay unchanged; command status differs by tool. |
| Add the identical leaf archive | The direct declaration returns; the parent still loads successfully. |
| Remove the parent | The direct leaf remains loadable; the parent is no longer root-resolvable. |
| Remove the last leaf declaration | Neither fixture package is root-resolvable. |

This last observation does not establish deletion from every store/cache or physical space reclamation. Runtime lookup, a manifest declaration, a lock selection, a materialized graph, and cached archive bytes are distinct facts.

The repeated transitive-only removal returns 0 and “up to date” in npm. pnpm returns 1 with `ERR_PNPM_CANNOT_REMOVE_MISSING_DEPS`, naming the available direct parent. Yarn returns 1 and says that the pattern does not match packages referenced by this workspace. Those are different supported policies, not three implementations of a universal refusal rule. The fixture establishes unchanged manifest/lock bytes, not absence of cache/log writes.

After the first removal, npm and Yarn still expose the leaf to a root-level `require`, while pnpm does not. All three parents still load it. Root visibility therefore proves neither a direct declaration nor the absence of a retained transitive dependency.

Re-adoption uses the same archive target in all three tools. npm rewrites its absolute `file:` reference to a relative reference; pnpm and Yarn retain the original spelling in this fixture. A first replay incorrectly required serialized reference equality and refused that npm row. The corrected replay checks both spelling and normalized target identity and reports the distinction. The original native records are unchanged. This is not a dependency-version change or a reproduced product defect.

## Source and model boundaries

The [source selections](../sources/js-removal-selections.json) identify exact upstream revisions and inspected bytes. npm's uninstall command passes removal names and workspace selection to Arborist reification; the inspected file exactly matches the installed distribution. pnpm validates names against manifest dependency groups before preparing removal and delegating to installation. Yarn matches declaration scopes in the selected workspace, refuses unmatched patterns, and delegates changed declarations to its installer. The full resolver, linker, hooks, multi-pattern publication, and crash behavior are not proved by these command entry points. pnpm/Yarn source-to-binary reproducibility was not established.

[Lean](Removal.lean) checks nine laws; [Bend](Removal.bend) checks three. The models project a fixed parent-to-leaf edge, two direct-declaration bits, each observed missing-root policy, and the selected node-modules root-lookup profile. They separate accepted editing from the declaration result and desired graph liveness. They are not general reachability, installation, or hoisting implementations. A successful model edit supplies no filesystem write authority or completion receipt.

The [replay](removal_conformance.py) checks raw-stream identities and saved manifest/lock hashes, then compares 15 actual declaration edits and their following runtime observations with both models. It rejects interpreting declaration removal as immediate payload unavailability or root lookup as direct-dependency ownership. Unsupported schema input is refused. No package manager executes during replay:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/js-peers/removal_conformance.py applications/evidence/js-removal-20261124T042813469322Z
```

Compile `Removal.lean` to `.build/applications/js-peers/Removal.olean` first. Native collection is the separate owner-run `python3 applications/js-removal-probe.py`, outside ordinary CI.

## Preservation and improvement candidates

**Preserve direct declarations as editable intent.** A package that remains selected transitively is not an existing direct declaration. Re-adding an identical selected package should be assessed as a declaration edit, with its own graph consequences, rather than automatically classified as a request to replace its bytes. The three native tools demonstrate this normal workflow. This is useful evidence for empack's separately recorded removal/re-adoption proposal; it does not qualify an empack implementation change.

**Explain retained dependencies without weakening their relationships.** A useful optional result is “Removed the direct dependency; it is still required by fixture-parent.” For a transitive-only target, a message can identify its requiring direct dependency and point to the tool's existing graph/explanation command. Keep npm's no-op policy and pnpm/Yarn's refusal policies unless a separately selected compatibility decision changes them. A silent forced deletion or invented direct declaration would be inappropriate.

The internal result should distinguish declaration edits, selected-graph changes, materialized effects, and retained reasons. Retention reasons require a complete relevant graph or an explicit unknown; a caller must not infer “unused” from an absent root lookup. A report-only extension can leave lock formats and saved projects unchanged. Reusing existing package/explanation structures is preferable to adding a second graph or a new command merely for this fixture.

The keep-current option is reasonable: the commands perform the selected edits correctly, and their existing dependency inspection can reveal retention. Its cost is the extra inspection a user needs to understand an apparently unsuccessful removal. Any new human summary and structured result should derive from the same completed facts, preserve established status policy, and avoid claiming cache deletion.

Before adoption, test shared workspace consumers, dev/optional/peer edges, unknown or incomplete metadata, changed archive targets, re-adoption with a different constraint, lifecycle failures, partial publication, lock-only modes, PnP, and concurrent edits. Those remain pending; this band establishes a small normal-flow comparison and a reporting/API candidate.
