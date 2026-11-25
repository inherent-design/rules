# Direct content types, interpretation, and placement

Empack separates a declared content type, archive-layout recognition, source representation, and destination. The native cases support keeping those distinctions. They also expose useful differences between CLI addition and explicit authored-source acceptance, and between fixed file bindings and automatic placement.

The installed empack 0.8.8-beta binary is independently identified by SHA-256. The inspected source is `0b4462e3032b4f09230b15329722eabefb7f574c`. Relevant inspected core/addition/identification files have no diff from the release tag, but this does not establish reproducible source-to-binary correspondence. No engine or Cargo build ran.

## Recognition and author choice

| Selected type | Current recognition markers | CLI default destination | CLI default server requirement |
| --- | --- | --- | --- |
| Mod | A recognized mod metadata filename | `mods/<filename>` | Required |
| Resource pack | `pack.mcmeta` and either assets or no data entries | `resourcepacks/<filename>` | Unsupported |
| Shader pack | A file below `shaders/` | `shaderpacks/<filename>` | Unsupported |
| Data pack | `pack.mcmeta` and data entries | Explicit layout required | Required |
| World | Dedicated interpretation: exactly one nonempty `level.dat`, with every member below its selected root | Explicit layout required | Required |

These are the selected CLI defaults and policies, not restrictions on every authored environment or placement override. A mixed assets/data archive supports both resource-pack and data-pack layout checks. Recognition is a set of compatible layouts, not a uniquely inferred author intention.

Without an explicit type, a `.jar` name selects mod. Other direct archives need a choice or `--type`; the noninteractive fixture receives usage status 2. Explicit type overrides the filename hint. The selected archive's source bytes, intended type, logical role, and installation filename remain separate values.

The marker reader does not establish that metadata JSON is valid, that a mod matches the loader, or that the payload works in Minecraft. The synthetic fixture deliberately uses empty metadata objects and text world markers. It produces no playable mod or world. `manifest diff --json` reports the declared runtime's agreement with the lock; that field is not payload compatibility. The existing human summary correctly describes dependency settings matching the lock, so this band identifies no defect in that wording.

## Native boundaries and retained evidence

The [primary capture](../../evidence/empack-content-kinds-20261125T200444932279Z/receipt.json) contains 17 calls: initialization, one excluded fixture-path error, 14 direct add/preview requests, and final local inspection. Two followups add three explicit-author/sync calls and two layout calls. All 22 recorded CLI groups were absent after completion.

The project, operation store, cache, home, and temporary directory belong to one disposable fixture. The source confirms that explicit `--state-dir` selects the operation root instead of the global store. No distribution was built, and no Java, game, provider/channel workflow, personal project, or host installation was used. Preservation statements cover captured author entries; they are not a whole-host I/O trace, a sandbox claim, or a statement that state/cache stayed unchanged.

| Request or transition | Observed result |
| --- | --- |
| Implicit mod JAR, resource ZIP, shader ZIP, and explicitly placed data ZIP | Accepted; source and pack copies retain exact archive bytes. The opaque JAR's intrinsic `CON` resource is not extracted into the filesystem. |
| Resource preview, then both requested types for a mixed assets/data ZIP | Accepted previews preserve captured author entries. |
| Unrecognized mod layout | CLI addition refuses with status 1; author entries stay unchanged. |
| Project archive selected as a mod | Refused before author publication; explicit type does not bypass the import-interpretation guard. |
| Wrapped world archive | Two members become explicit `local-files` sources and per-member destinations. The container is not copied as one world file. |
| Archive containing two world roots | Refused; captured author entries stay unchanged. |
| Resource pack named `.jar` or uppercase `.ZIP` | Accepted as requested; the original filename and bytes are preserved. |

The first fixture passed a relative operand while the process working directory was outside the selected project. `--workdir` selects the project root; direct operands are based on the invocation directory. The call failed before classification and left the author snapshot unchanged. A guarded continuation checked the exact known snapshot, inputs, binary, and original rows, then used absolute operands. Original producer, streams, and incomplete receipt remain retained; new labels prevent overwriting the failed stream. This is a harness-path error, not a content-classification defect. The continuation option is not a general recovery tool.

Two broad process-path checks also captured the invoking shells because their command text contained the private path. Separate closure reviews bind those exact matches, the terminal owning exec observations, and a later empty path-match scan. They do not rewrite the original receipts or authorize cleanup. Child-group absence and path matching are different observations.

## Explicit source acceptance and sync

The [authored-source followup](../../evidence/empack-content-kinds-sync-20261125T200904777793Z/receipt.json) inserts only this declaration into the disposable author file:

```yaml
unknown:
  path: vendor/unknown.jar
  type: mod
```

Inspection shows a stale lock and no recorded selection. `sync` then accepts the declared, structurally valid but unrecognized JAR, copies its bytes, and makes inspection current. The [owner-edit record](../../evidence/empack-content-kinds-sync-20261125T200904777793Z/owner-edits.json) binds that explicit change to both sides of the native workflow.

This is a real acceptance-policy distinction: ordinary CLI addition uses `RequireRecognized`; an explicit authored direct source uses `AcceptUnrecognized`. The latter removes a heuristic marker requirement, not structural archive checks or the ordinary archive's project/world interpretation guard. It establishes neither authentication nor runtime compatibility. A newly computed observation is not an independent publisher assertion, and missing dependency metadata must remain unknown.

The refusal's reference to explicit acceptance is hard to act on through CLI addition alone: the inspected `AddOptions` and direct input adapter expose no acknowledgement switch. The safe authored declaration/sync route is now observed for this narrow fixture. A reporting improvement can explain that route without silently relaxing policy or inventing a new flag. Any additional acknowledgement UX requires a separate decision about authority and caller behavior.

## Fixed binding and automatic placement

The [layout followup](../../evidence/empack-content-kinds-layout-20261125T201053173979Z/receipt.json) changes only the automatic mod layout to `custom-mods`:

- The manually declared unknown source moves from `pack/mods/unknown.jar` to `pack/custom-mods/unknown.jar`.
- The CLI-created module remains at `pack/mods/module.jar`, with its explicit file binding.

The observer derives the pre-change policy from saved inspection, then checks the later physical paths by independent payload hashes. The final inspector still distinguishes `automatic` from an explicit destination list. This is not a defect or permission to rewrite bindings: both policies are useful. It is an interface obligation to explain which policy an operation records and how a later layout edit will affect it.

Inspection's normalized request should remain distinct from saved output locations. Where users need both, the existing lock data can support a separately labeled recorded-destination view; replacing `automatic` with a computed path would erase policy information. No new inspection API or persistence format is implemented here.

## Consumer filename constraints

The native resource copies retain `.zip`, `.jar`, and uppercase `.ZIP` names. The retained Minecraft 1.21.1 and 1.21.5 `PackDetector` source checks a regular selected file for a case-sensitive lowercase `.zip` suffix after its symlink branch. Directory admission instead checks for a regular `pack.mcmeta`.

The [host context](../../sources/empack-content-kinds-host-context.json) records exact client/source identities and this static rule without copying proprietary payloads. These three suffix predicates are **source-only comparisons**, not a Minecraft run, a fresh distribution/import test, or complete pack acceptance. The synthetic metadata would require separate semantic validation anyway. Dedicated Iris/shader-pack detection remains unqualified.

This motivates a candidate check at a known consumer projection, rather than a universal content-type restriction. Custom layouts and consumers can have different rules. Preserve input names and byte identity; let an author choose an existing destination binding when a different exported filename is needed. Do not silently rename existing resource packs: seed-owned options may retain the previous selection string. Any implemented policy needs real consumer cases, previewed path effects, and explicit handling of existing names.

## Models and replay

[ContentKinds.lean](ContentKinds.lean), [ContentKindsCase.lean](ContentKindsCase.lean), and [ContentKinds.bend](ContentKinds.bend) contain 29 Lean and 14 Bend laws. Both models agree on 98 scalar projections: 95 native fact projections and three static suffix predicates. Native projections include observer-assigned refusal classes from actual messages/statuses; they are not exported planner enums or new production error codes.

The comparison covers 15 admission requests, eight saved dependency/type/source/placement views, and two layout effects. Marker, route, configured-layout, and archive properties are independently interpreted inputs. Native kind outputs are compared with the original requested kinds, not supplied back as the expected kind. The wrong-cwd failure is excluded from this model. Needed unknown world observations are refused; unavailable fields bypassed by an earlier gate are not treated as observed absence.

With the pinned tools and the model's compiled olean available:

```sh
LEAN_PATH="$PWD/.build/empack-content-kinds-formal" python3 applications/empack/content-kinds/conformance.py
```

Set `LEAN` and `BEND` if they are outside `PATH`. The observer reads original archives, streams, snapshots, producer identities, and both owner-edit chains. Only the latest layout snapshot is compared with the live private tree. It executes research models, not empack, extraction, or native collection. Source/cache absence is recorded as availability; it is not silently promoted to fresh qualification.

The [conformance receipt](../../evidence/empack-content-kinds-20261125T200444932279Z/conformance.json) and basis record expose controls and actual scope. Reuse the existing [archive](../ARCHIVES.md), [world protection](../WORLDS.md), and [portable core](../PORTABLE-CORE.md) studies at their own boundaries. They do not substitute for these direct-file tests, and these tests do not qualify their full consumers.

## Design direction and remaining work

Keep declared type, source assertions/observations, layout evidence, interpretation, file roles, placement policy, and consumer readiness separate. A world import changes representation into retained members; a portable workspace must retain those derived sources and their relationships, not just a container label. Current byte-backed inspection and transaction authority must survive extraction.

A future shared decision helper can reuse the small marker/kind policy inside the existing core while native/browser adapters retain byte inspection, immutable content identity, cancellation, budgets, and persistence authority. Bind background results to the exact retained content and relevant project revision. Do not fork the classifier in a frontend or create a crate per predicate. Keeping the current cohesive native reader is reasonable until a real portable caller needs that extraction.

The proposed compatibility gate in the models preserves missing format/loader checks. It is not an implemented validator. More useful reporting can state what was checked and how an author can proceed without claiming game compatibility. Preserve current kind aliases, source/binding semantics, and structured fields unless an explicit API/schema decision changes them; no migration framework is proposed.

Further verification must cover real metadata/game consumers, custom side/choice overrides, sparse or unusual valid archives, external and URL inputs, restricted/provider identity, named/multi-file selections, source changes during inspection, full decoder budgets, distribution projections, interruption/concurrency, and other hosts. The complete application study remains active. These component slices leave their parent operations pending.
