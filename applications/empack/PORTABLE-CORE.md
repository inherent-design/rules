# Shared core on native and browser hosts

Empack's existing pure inventory core runs unchanged on native Rust and browser WASM. The same research wire adapter produces identical results across native execution, Node WASM, and dedicated workers in Chromium and WebKit. This establishes one reusable semantic component. It does **not** establish a shared project engine, project format, browser Prism exporter, or the required import/save/reopen/export flow.

## Executed boundary

The [build receipt](../evidence/empack-portable-core-20261125T095721300368Z/build.json) freezes all 18 core source files at `0b4462e3032b4f09230b15329722eabefb7f574c`. Direct Rust 1.100.0 builds that tree unchanged for macOS arm64 and `wasm32-unknown-unknown`, then links the same [research adapter](portable-core/engine.rs). The native executable is 605,768 bytes; WASM is 121,080 bytes. Neither size predicts a complete portable engine.

The adapter calls `InstallDestination::parse` and `BuildInventory::project`. Inputs carry destination, layer, client/server requirements, representation, known length, digest observation, and permissions. Outputs retain selected metadata, precedence, and choice provenance. The wire is a bounded study protocol, not an empack document schema or public API. Its source-owner indexes grant no filesystem authority. An unacquired input carries an explicit known expected size; unknown sizes are outside this adapter rather than encoded as zero.

The 318-byte owned JAR is an opaque ZIP fixture, not a working mod. The configuration contains Unicode. [Exact input packets](../evidence/empack-portable-core-20261125T095721300368Z/cases.json), [native results](../evidence/empack-portable-core-20261125T095721300368Z/native-cases.json), and [browser results](../evidence/empack-portable-core-20261125T095721300368Z/browser.json) cover 32 cases:

- Bundled client/server views and preserved native layers; side/shared-override/common precedence; disabled-option fallback; shadowed missing input; unresolved choices and required materialization.
- Read-only/executable attributes, empty content, Unicode names, duplicate layers, and invalid side requirements.
- Eight invalid paths and five malformed wire inputs. All four runtimes return the same exact status and output bytes, including refusal diagnostics.

Browser collection uses cached Playwright 1.64.1, Chromium 156.0.8078.4, and WebKit 27.2 with private persistent profiles and a loopback origin. The served page delegates packet processing to a dedicated worker; JavaScript transports bytes and does not choose layers or interpret a consumer format. The [WASM host](portable-core/host.mjs) refuses imports and checks input/output memory bounds. Each instance is serialized; memory views are refreshed after calls that can grow memory, and output is copied before yielding. Both browser profiles refuse an over-limit request.

The module has no imports and was linked with a 16 MiB memory maximum. Node observed 1,179,648 bytes of linear memory; this is not process RSS or an exhaustion test. Same-origin delivery, text-only page output, and a restrictive CSP reduce this fixture's surface; they do not qualify a production browser security boundary. No native path, process, publication, signing, or storage capability crosses the wire.

The [closure receipt](../evidence/empack-portable-core-20261125T095721300368Z/browser-closure.json) records collector exit 0, closed browser contexts/server, absent original process group, and no remaining fixture-workspace process. No graphical desktop session, account, personal project, or live operation store is used. Node results retain exact outputs and shared module identity but lack an original collector-invocation/Node-binary attestation; that provenance remains weaker than the native and browser receipts.

## Selection is not export readiness

Three successful cases intentionally distinguish core semantics from the complete engine:

| Input | Pure-core result | Additional obligation |
| --- | --- | --- |
| `config/Rules.json` and `config/rules.json` | Two distinct destinations | The native output layout applies canonical Unicode caseless collision checks. |
| Canonically equivalent Unicode path spellings | Two distinct destinations | The same collision policy must be shared by the future portable output layer. |
| Caller supplies an all-zero JAR digest observation | The value is preserved | Source capture and retained-byte verification must establish what bytes actually exist. |

These are not new core defects. The [source ledger](../sources/empack-portable-core-selections.json) identifies the separate current engine gates. `layout::CollisionIndex` uses NFD, default case folding, and NFD again, and checks file/ancestor collisions. `ContentLease::copy_verified` and `verify_stream` bind actual bytes and lengths. Client assembly adds `.minecraft/`, templates, `instance.cfg`, and `mmc-pack.json`, validates runtime components and the complete namespace, stages retained files, and writes and verifies an archive before publication. Those full-engine gates were inspected, not executed by this fixture.

A frontend must therefore distinguish “Content selected” from “Ready to export” and name missing bytes, unsupported interpretation, or an output collision without discarding the draft. A content digest is neither an asset lease nor execution permission. Exact-byte agreement among four callers does not establish that their common metadata was true.

## Reused models and fidelity checks

The [retained replay](portable_core_conformance.py) reuses [Projection.lean](Projection.lean), [ProjectionCase.lean](ProjectionCase.lean), and [Projection.bend](Projection.bend) unchanged. Their ten Lean and four Bend laws remain the owning domain models; this band adds runtime evidence rather than another planner.

The [conformance receipt](../evidence/empack-portable-core-20261125T095721300368Z/conformance.json) compares 19 semantic cases with Lean, including selected membership, precedence, and choice provenance. Paths and content observations become equality labels; each case has at most two destinations and one optional key. This does not qualify arbitrary choice maps. The one materialization error compares status only because the real wire returns no intermediate inventory. Bend compares 21 flat destination choices and 19 representation gates after global admission; preserved-layer/global validation remains outside that model. Thirteen path/wire refusals are actual runtime evidence, outside both projection models.

The independent observer decodes native bytes, checks output attributes/lengths/digests against the named inputs, compares all runtime packets, and rechecks tool, source, artifact, stream, and closure identities. Four malformed model inputs refuse. Nine changed observation fields and six changed model outcomes are rejected. These controls exercise the research comparison, not JVM/browser fault handling or production security.

Two adapter compile failures are retained under the [first](../evidence/empack-portable-core-20261125T095419598124Z/unrun.json) and [second](../evidence/empack-portable-core-20261125T095506142124Z/unrun.json) run identities. Neither executed native API cases. A [pure replay correction](../evidence/empack-portable-core-20261125T095721300368Z/replay-review.json) fixes omitted empty lists in a refused-case expectation; it changes no measured runtime result. Compiler and module identities are recorded, but subordinate linker and whole-toolchain reproducibility are not qualified.

```sh
# Use the pinned Lean/Bend toolchain and compile Projection.lean first.
LEAN=<pinned-lean> BEND=<pinned-bend> \
  python3 applications/empack/portable_core_conformance.py
```

Replay reads retained observations and runs the pure models only. Collection commands in `portable_core_build.py`, `portable_core_cases.py`, and `portable_core_browser.mjs` are owner-run procedures, outside ordinary CI. The official WASM standard-library component added about 99.4 MiB of allocated local storage; private build output occupied 16,284 KiB before browser profiles. No full product/Cargo dependency build occurred. Final retained-work allocation is recorded separately in the handoff.

## Extraction sequence and keep-current alternative

The [previous storage band](PORTABLE-STORAGE.md) already exercises browser input, retained backing, incomplete save/reopen, and study backups. Joining its output to this core still requires the following source-owned boundaries; connecting them with a second JavaScript interpreter would evade the candidate's requirement.

1. **Shared interpretation.** Extract author/bindings decoding, semantic validation, raw-versus-semantic identity, source/placement composition, template selection, and output collision policy behind host-neutral interfaces. Preserve incomplete raw drafts separately from successfully interpreted intent. Unknown sizes and unavailable source evidence must remain explicit.
2. **Retained input capabilities.** Adapt native leases and browser immutable backing to verified, bounded input streams. Bind reads and background work to captured images. Preserve current, saved, history, pending, and export roots. A transport packet with a digest cannot replace that custody.
3. **Shared consumer assembly and verification.** Separate Prism profile/default generation, template interpretation, full namespace planning, archive codec, and member verification from native staging/publication. Retain exact current consumer checks, permissions, limits, and cancellation. Browser delivery must observe actual finalized download bytes; worker completion alone is insufficient.
4. **The required join.** Import the local JAR/config, edit metadata/placement, retain an invalid draft, validate and preview a captured image, save/reopen, and export through the shared code on native and browser hosts. Compare complete archive inventories, configuration/profile validity, and delivery receipts, with missing/corrupt backing, stale work, and worker-loss controls. Storage and core component evidence do not qualify this joined scenario.

Keeping native-only export is a valid staged alternative if a complete consumer extraction is not yet justified. A browser may save an explicitly limited project backup and say that distribution export is unavailable. That product decision would narrow the candidate and requires owner review; it cannot be silently substituted for the current required scenario. No production extraction, format migration, or support expansion is selected by this study.

The subsequent [document-codec comparison](PORTABLE-DOCUMENTS.md) establishes actual native/browser portability of the unchanged current author/bindings codec and selected edits through an isolated facade. It does not complete the rest of interpretation, consumer assembly, project storage, or the required join above.
