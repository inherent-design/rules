# npm manifest queries and edits

**A manifest value, a query result, and displayed output are separate values. A failed multi-workspace edit can also leave an earlier workspace saved.** This band compares those boundaries on authored local manifests; it does not qualify installation or publication.

## Profiles and observations

| Profile | Evidence | Boundary |
| --- | --- | --- |
| npm 11.20.0, Node 26.13.1, macOS | 31 commands: 24 primary, four scalar reads, and three joined retry commands | Selected getters, semantic edit refusal, no-op, array edits, sequential workspace saves, and explicit repair/retry |
| Isolated npm 12.2.3, same Node/host | 13 commands, including version | Explicit JSON versus default text for selected falsy values, arrays, a missing field, and null traversal |
| Both versions, same authored document | Two commands | Full-document `npm pkg get --json` preserves the complete JSON object |

All 46 recorded process groups exited and were absent at capture completion. Commands used disposable projects, private configuration/cache paths, direct argument vectors, and offline/disabled network settings. No install, hooks, publication, global tool update, or personal project mutation occurred. These settings are fixture controls, not a host sandbox or a complete I/O trace.

The npm 11 source is pinned to `d12b9434dd010b5fb7044c3cc149cdda317813f8`; seven selected files match installed bytes, including `@npmcli/package-json` 7.0.5 helpers. Separate ledgers retain the display implementation and two inspected test files. The npm 12 source is pinned to registry `gitHead` `7aa36da5c867b71fc7ea905f0392fc872f769cc6`. Its official archive was admitted using registry SHA512 integrity, SHA256, bounded regular-file extraction, and three source correspondences. The host npm installation stayed unchanged.

The registry's npm package selected 12.2.3 at inspection. GitHub's repository-level latest-release endpoint instead returned a `libnpmpack` component release. The retained [qualified endpoint observation](../evidence/npm-manifest-20261125T183326087674Z/repository-latest-component.json) is not a CLI version-selection rule.

## Reading a field is versioned behavior

| Request | npm 11.20.0 | npm 12.2.3 |
| --- | --- | --- |
| Selected `false`, `null`, `0`, or `""` | Exit 0, empty stdout | Explicit `--json`: object mapping the requested field to its exact value |
| Selected empty array | Exit 0, empty stdout | Explicit `--json`: mapped `[]` |
| Selected singleton array | Unwrapped element | Explicit `--json`: mapped array, cardinality preserved |
| Missing selected field | `{}` | Explicit `--json`: `{}` |
| Field below a present null | Exit 1, generic `Cannot convert undefined or null to object` | Same observed diagnostic |
| No selector, explicit `--json` | Complete authored document | Complete authored document |

In npm 11, Queryable unwraps empty/singleton arrays before rendering. The command also unwraps a single selected field. The buffered display pipeline uses truthiness checks that can discard a valid falsy scalar. A parent-object query retains the same leaf values because its top-level object is truthy. The model therefore distinguishes **field presence, array cardinality, producer wrapping, payload presence, and JavaScript truthiness**.

npm 12 already changes this producer contract: explicit JSON preserves field mappings and arrays, while default output is text. Its measured default singleton array is `[ 'one' ]`, which is not valid JSON. The selected Queryable source body is unchanged; the call's options and command envelope differ. The display implementation still contains truthiness guards, but these selected JSON requests avoid a falsy root payload by wrapping the result. This is an existing npm 12 behavior, not a proposed new fix.

For automation needing these values across both measured versions, the verified common command is:

```sh
npm pkg get --json
```

Parse that full document as JSON, then select the desired field locally. This only establishes the measured document/profile; it does not promise that every npm command or every future version has the same output contract.

## Editing and validating are different actions

The npm 11 fixtures establish the following boundaries:

- A plain assignment stores text; `--json` stores the parsed JSON type.
- A later scalar-path conflict, invalid JSON argument, invalid script type, or forbidden key refuses the selected single-document edit before saving. Its bytes, mode, and modification time remain unchanged, even when an earlier assignment had changed the in-memory object.
- A semantic no-op preserves those same file facts. The source preserves detected indentation/newlines and skips an unchanged serialization.
- Invalid package name/version strings can still be saved. These editing checks are not comprehensive package-identity validation.
- Deleting an array index shifts later entries. Appending twice adds twice; it is not idempotent.
- `--force` replaces the selected incompatible scalar with an object; it is explicit destructive conversion, not general repair.

The selected save helper uses a direct filesystem write. Successful writes and semantic refusals do **not** demonstrate atomic replacement, crash recovery, disk-full safety, concurrent-writer safety, or whole-filesystem isolation.

### Workspace failure and retry

The workspace setter saves each selected workspace in order. In the first fixture it saves `alpha`, then refuses `omega` because the requested path crosses a scalar. The command fails, but `alpha` remains changed; root and `omega` remain unchanged. The current error does not identify the saved prefix or failing workspace.

A separate joined fixture appends in `alpha`, fails in `omega`, and records an explicit owner repair of **only** `omega` from a scalar to an empty array. Retrying appends to both workspaces, so `alpha` now has the appended entry twice. [The repair record](../evidence/npm-manifest-retry-20261125T185049329242Z/owner-edits.json) binds the intervening edit to both command images. This is observed semantic partial application and retry behavior, not a crash-generated recovery scenario. These write/retry controls were not rerun on npm 12.

## Test fidelity

The pinned upstream Queryable test retains empty values inside a multi-field object. The selected display null test exercises the direct text-cleaning path. Both are useful at their stated unit boundaries; neither establishes the composed single-falsy-leaf buffered JSON path. These source tests were inspected, not executed. The native CLI captures provide the independent composed-path observations in this band.

## Models and replay

[Manifest.lean](Manifest.lean), [ManifestCase.lean](ManifestCase.lean), and [Manifest.bend](Manifest.bend) contain 24 Lean and 16 Bend laws. The versioned getter projection and sequential-save model compare:

- 26 query frames, 31 command-effect frames, and five admitted append transitions;
- 119 native output/effect fields;
- 31 separately identified source-derived attempted-step counts;
- 78 proposed renderer/shape fields, which are not native patched-program observations.

All 228 projected fields agree between the models. The [conformance receipt](../evidence/npm-manifest-20261125T183326087674Z/conformance.json) records controls, availability, and retained basis hashes. The original `initial-comparison.json` describes an earlier model/profile, not the current gate. Its counts must not substitute for the final receipt.

With the pinned Lean/Bend tools and the model's compiled olean available, run:

```sh
LEAN_PATH="$PWD/.build/npm-manifest-formal" python3 applications/npm-manifest/conformance.py
```

Set `LEAN` and `BEND` to the chosen executables if they are outside `PATH`. The observer reads retained streams/images and available source/tool identities. It executes only research models, never npm or an application fixture. If local tool/source caches have been removed, it reports that availability instead of claiming a new native qualification. Collection scripts remain separate and must not run in ordinary CI.

## Candidate improvements and compatibility

1. **Keep machine reads explicit and shape-preserving.** Preserve npm 12's field mappings and typed arrays. For measured cross-version consumers, prefer the full-document read above. Changing older command output is an API/major-version decision; do not silently redefine its serialized contract. Test absence, null, falsy scalars, empty/single/multi arrays, and errors independently.
2. **Name a failed traversal's field and container type.** The null traversal remains an observed error in both versions. An actionable cause can identify the requested path and null parent while retaining structured error conventions. This needs the command's existing error policy, not a new general diagnostic framework.
3. **Report partial workspace edits.** Retain a per-target saved/no-op/failed/not-attempted result and identify the failing workspace. Tell the operator to inspect completed changes before retrying a non-idempotent edit. This can improve reporting without promising a multi-file transaction or automatic rollback. A two-phase or transactional write redesign would need separate authority, storage, and interruption studies.
4. **Keep renderer proposals scoped.** A separate payload-presence test could preserve falsy data in a general buffered renderer, but a renderer-only change cannot reconstruct an array already collapsed upstream. Review all callers, redaction, standard text output, and serialized compatibility before selecting such a change. No display patch or security weakening is approved here.

For empack, this supports preserving declarative values, explicit query/output policies, per-target effects, and retry consequences as separate domain facts. It does not require adopting npm's edit syntax or its partial-save policy. Keep existing empack validation/revision fences until a separately reviewed implementation decision chooses otherwise.

Remaining work includes `init`/`fix`, general manifest schemas and JSON-path parsing, nested singleton arrays, complete redaction behavior, npm 12 workspace writes, save I/O failures, concurrency/interruption, other platforms, and joined install/publish behavior. Parent inventory operations remain pending; only the named component slices gain this evidence.
