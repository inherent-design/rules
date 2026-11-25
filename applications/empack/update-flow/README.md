# Author update to snapshot recipient

One isolated empack 0.8.8-beta project now joins public provider discovery, pin removal, update preview/application, materialization, two Prism snapshot exports, and first native recipient preparation. Twenty CLI invocations form **one successful workflow**, not twenty independent integration scenarios. The finite models compare 82 scalar observations across the same trace. This changes no empack implementation or deferred UX intent.

The [source map](../../sources/empack-update-flow-selections.json) pins four inspected owners at `0b4462e3032b4f09230b15329722eabefb7f574c`. The [source context](../../evidence/empack-update-flow-20261125T213429298820Z/source-context.json) records identical core/lib source trees and Cargo.lock at that revision and the v0.8.8-beta tag. This is not a reproducible source-to-binary build. The installed executable was independently identified by SHA256 `99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f`.

## Fixture and observations

The own project requests Minecraft 1.21.1, Fabric 0.16.0, and preferred Java 21. Its sole explicit dependency is Modrinth project `uXXizFIs` (FerriteCore). Independently sampled public records identify old `wmIZ4wP4` / 7.0.0-fabric and target `sOzRw3CG` / 7.0.3-fabric, including size and SHA512 assertions. These samples are not intercepted native responses. The two records have no required *mod* edges in the sampled provider metadata. The actual target JAR separately declares loader and Minecraft requirements; no provider-mod edges does not mean no runtime requirements.

All commands used separate, explicitly selected test state/cache directories. Input was closed, stdout/stderr were separately captured, and every recorded process group was absent at completion. Source, raw streams, snapshots, sampled bodies, downloaded artifacts, and recovery-capable test state remain retained. No personal pack, host installation, or launcher instance was changed.

| Step | Native observation | Meaning |
| --- | --- | --- |
| `sync --materialize` | Old lock selection and matching 117,333-byte mod appear. | Initial exact selection and local payload agree. |
| `update --all` preview | Held old pin; permitted old, runtime-compatible target; required closure validated. | Held does not mean no compatible candidate. This is a one-root success case. |
| `unpin ferrite` | Author pin removed; old exact selection and local mod retained. | Relaxing the request is not updating the saved or installed selection. |
| Automatic preview | Target proposed; no author pin change; project entry snapshots unchanged. | Candidate selection and publication remain distinct. Cache/state side effects outside the project are not excluded. |
| Exact preview and later `--apply` | Author/lock replacements and old-mod removal match the earlier three-file preview. | Fresh application published those effects. This does not test stale approval or prove reuse of the earlier plan object. |
| After application | Exact target pin and lock saved, old mod gone, target mod not in the author directory. | The target is a retained reference obligation, not yet a local author payload. Global cache availability was not independently measured. |
| Plain `check` | Recorded scope, complete, zero verified files, one reference. | Required recorded checks passed; referenced bytes may legitimately be absent. There is no `--local` flag. |
| `sync --materialize` and checks | Target 123,450-byte mod appears; author/lock bytes, modes, and modification times stay unchanged. Plain check verifies one file; online check adds fresh provider assertions and relationships. | Materialization need not change selection. Neither check starts Minecraft. |
| Bundled Prism snapshot | Correct mod, `instance.cfg`, and `mmc-pack.json`; 108,232-byte ZIP. | Selected mod bytes are embedded. This case built after author materialization; it does not prove all bundled builds require a preexisting author file. |
| Reference Prism snapshot | No mod payload; bootstrap JAR, invocation files, release JSON, and Prism metadata; 2,764,577-byte ZIP. | Delivery can be references while updates are snapshot-only. The tool JAR is not a mod payload. Reference delivery is not necessarily a smaller archive. |
| Native `instance ensure` | Generated release digest selects the snapshot; mod, completed release, and layout record appear. | First recipient file preparation succeeds. The JAR was not executed. |
| Repeated ensure and instance check | No captured entry changes; one verified managed file; own unowned options file preserved. | Bounded idempotence and preservation, not an old-to-new recipient update or launch. |

The generated snapshot has `require_subscription: false`. Its prepare invocation requests the exact release SHA256 and engine 0.8.8-beta. The release format separately declares `minimum_engine: >=0.8.4-beta`. Those describe different constraints: exact delegated tool selection versus release-format admission. Neither is a claim that an arbitrary older engine can execute the generated bootstrap protocol.

The native recipient call used the entire reviewed `prepare.json` argument list, through the independently identified native binary. The producer checked every argument, schema, engine, digest, and side/layout value. It did not blindly execute archive-provided instructions. Extraction admitted only the recorded unique entry set, checked every digest and total size, rejected absolute/traversing/link paths, and created a fresh owned destination. These checks qualify this study procedure, not empack's general archive-import security.

## State and proof scope

[UpdateFlow.lean](UpdateFlow.lean), [UpdateFlowCase.lean](UpdateFlowCase.lean), and [UpdateFlow.bend](UpdateFlow.bend) model an admitted success trace. Identity labels `1` and `2` stand for the independently sampled old and target exact identities; they are not versions or chronology. The input contains the initial fixture profile and operations, never native after-state values. [observations.py](observations.py) independently decodes retained author/lock bytes, physical file hashes, native JSON, and archive inventories. Its YAML decoder deliberately accepts only this fixture's shape.

Each author row first reports `[author pin, saved selection, local payload]`. Operation facets then report held/permitted selection, preview target/reference count, check completeness/verified/reference counts, or export mod/tool/subscription presence. Recipient ensure rows report `[installed selection, unowned setting preserved]`; instance checking reports `[complete, verified files, recorded seed/world entries, unowned setting preserved]`. The observer does not mistake an absent author payload for absent global cache data.

Eighteen Lean and nineteen Bend laws preserve unpin retention, preview nonpublication, exact update versus materialization, permitted references, snapshot representation, and recipient idempotence. The comparison is a finite success projection: admission, network uncertainty, provider correctness, root authority, digests, filesystem publication, and arbitrary graphs are not proved by the model. Recorded snapshot hashes and source boundaries supply separate evidence.

Twelve changed-output controls, six unsupported DTO/sequence controls, and four raw-observer controls exercise lost selections/payloads, false materialization, incorrect check counts, missing bundled payloads, unintended subscription, unowned-file loss, changed command mode, and corrupted assertions. Raw captures remain unchanged. The [proof receipt](../../evidence/empack-update-flow-20261125T213429298820Z/proof-gate.json), [conformance receipt](../../evidence/empack-update-flow-20261125T213429298820Z/conformance.json), and [basis hashes](../../evidence/empack-update-flow-20261125T213429298820Z/basis.json) identify the tested inputs and tools.

Replay uses only proof tools and retained data:

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/empack/update-flow/conformance.py
```

Use the pinned toolchain and compile the two Lean modules into `.build/empack-update-flow-formal` first, as recorded in the proof receipt. Missing private archives, sampled API bodies, native executable, or latest fixture roots are explicitly unavailable in a public-only replay. Recorded streams and member assertions remain available; replay does not reacquire or reconstruct missing native artifacts.

Pass `--public-only` to refuse those owner-local reads even when the original paths happen to exist. An isolated public-only copy matched the same model inputs, observed values, basis hashes, and controls while excluding eleven private artifact/source locations. This does not replace inspection of the retained native ZIPs or the owner's latest fixture state.

## Keep current and simplify deliberately

Keep exact pins, automatic preference, saved selections, local payloads, export delivery, update ownership, and completed recipient release as distinct facts. The native flow supports their separation. The [core selection band](../selection/README.md), [synchronization band](../SYNCHRONIZATION.md), and [JavaScript update band](../../js-updates/README.md) provide related components; their command effects are not interchangeable. Unlike this empack application, a package manager may materialize its installation during the update command itself.

The captured apply output already lists the reference and actual file actions. A useful UX proposal is to carry those facts into its final result: “Saved the new selection; one file still needs materialization,” with an appropriate next command. A single “updated” Boolean would lose information. Prefer a derived operation result over another persistent status file or a second planner. In a portable API, keep changed intent, selected graph, verified/remaining content obligations, and publication receipt together without turning any one of them into authority for the others. Existing planning, verification, and reporting owners should supply those values.

The captured current display label is an opaque old provider ID, while the target has a friendly version. A future report can distinguish an unavailable label from an unavailable selection, without making an extra lookup mandatory merely for cosmetics.

`player_owned_entries: 0` is correct for this fixture's **recorded** release inventory. The inspected owner increments it only for selected seed/world entries and deliberately does not traverse their content. The separate unowned `options.txt` is outside that count and remained byte-, mode-, and modification-time identical. A clearer label or supplemental count description could prevent interpreting zero as “no user files.” Do not add whole-world or directory scans merely to make the count look comprehensive, and do not weaken ownership protection.

Flow-style pack/runtime/build values produced four authoring editing-limitations in inspection. They did not block the unrelated dependency pin edits. This is evidence for the selected operation's edit scope, not permission to ignore unknown dependency evidence during deletion. The deferred removal/re-adoption UX work remains unstarted.

## Remaining

This join does not cover an existing recipient applying an older-to-newer release, subscription/channel authentication, server exports, Prism import, bootstrap execution, Java/Minecraft launch, game compatibility, worlds/seeds, conflicts/overrides, failed acquisition, stale input, interrupted publication/recovery, multi-root closure, provider errors, or other platforms. Required closure validation and artifact hash agreement do not establish those properties. All parent inventory operations and joined-scenario statuses remain unchanged.
