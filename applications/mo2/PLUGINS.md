# Plugin setters, ordering, and completion boundaries

MO2's game-plugin list is separate from its installed mod catalog and loose-file priority. Raw setters, notification helpers, derived load indices, master-presence checks, writer requests, and game-specific refresh have different contracts. This band executes selected MO2 v2.5.2 methods. It does not run Windows MO2, a game, LOOT, USVFS, or a real profile writer.

## Evidence profile

The [source selections](../sources/mo2-plugin-selections.json) pin `9c130cbf2fc7225fb2916e46419af50671772aa0`. The [collector](plugin_probe.py) inserts nine unchanged method bodies into an identified [driver](plugin_driver.cpp). The [receipt](../evidence/mo2-plugins-20261125T155025191906Z/receipt.json) binds source ranges, input, generated source, compiler, linked Qt framework, executable, and original streams. All three native command groups returned and were absent afterward. Ignored generated work occupies 288 KiB.

The driver uses actual QtCore strings/lists and standard containers. Catalog construction, enum representation, filename comparison, logging, signal calls, and game-index generation are adapters. Names come from one canonical ASCII vocabulary; other spellings, casing, and Unicode are unqualified. The build used pkg-config QtCore 6.12.0 and records the linked framework digest. That does not qualify MO2's supported Qt/Windows configuration. No widget, event-loop delivery, real subscriber, disk writer, game feature, or plugin parser is constructed.

Twenty-eight cases retain thirty-one step states. Inconsistent forced-policy prestates and duplicate order requests are constructed controls. They do not establish that normal loading produces those states. Original capture fields `writes` and `generated` count adapter calls. Models use `writeRequests` and `indexCalls` to avoid implying persistence or real game-index computation.

## Entry points have different effects

| Entry point | Selected-method effects | Separate obligation |
| --- | --- | --- |
| `setState` | Normalizes one enabled bit; unknown name logs a warning | No order synchronization, write request, or state notification |
| `enableESP` | Uses the same scalar policy and requests a write for a found name, even unchanged; notifies a changed bit | No completed writer or derived-view receipt |
| `setEnabledAll` | Skips forced entries; requests one write and grouped notification only when free bits change | Does not repair constructed inconsistent forced prestates |
| `setLoadOrder` | Reassigns priorities, rebuilds lookup indices, and calls game-index generation | No `loadOrder` synchronization, write request, or state notification in this method |
| `syncLoadOrder` | Assigns dense indices to enabled plugins in priority order; disabled entries get `-1` | No master check or saving |
| `testMasters` | Computes missing names from enabled plugins; clears disabled dependents' missing sets | Presence is not order, LOOT compatibility, or runtime acceptance |

Forced-loaded or forced-enabled scalar policy dominates a disable request. A force-disabled scalar without either positive force stays off. Bulk skipping can retain an inconsistent forced prestate; this difference is not itself a defect. The separate [profile activation](PROFILES.md) band concerns mod/profile records, not these game-plugin records and three force flags.

The API-then-normalize case exposes the stages: activating a plugin leaves its old `loadOrder=-1`; explicit synchronization updates that field, and explicit master checking updates dependency evidence. None alone yields a saved-file receipt. A changed helper records its write call before its state-notification call. That is source call order through adapters, not Qt slot-delivery qualification.

## Ordering and lookup counterexamples

A partial order request puts named plugins first and appends unlisted entries in catalog-vector order. It does not preserve their previous priority order. An empty request restores catalog order. The nearby comment says to use old priorities; the model preserves captured implementation behavior rather than inferring stability from that comment.

A duplicate known name consumes two ranks. In the three-entry control, final priorities are `[1,2,3]`. Index rebuilding logs the out-of-range priority and omits that row from name lookup. The catalog still contains the row, but `state(name)` reports `STATE_MISSING`; the priority vector is `[0,0,1]`. Game-index generation is a counter adapter, so consequences in real game-specific index code remain open.

This is an API-shape counterexample with unresolved caller/precondition reachability, not a reproduced full-application failure. A lookup's missing result is not a physical-file observation or deletion authority. Catalog existence, lookup membership, enabled state, file origin, and game load index are different facts.

An enabled master appearing later in priority order is not missing to `testMasters`. This follows the helper's set-membership contract; it does not certify a valid order. Real refresh performs additional primary-plugin and relationship corrections.

## Surrounding operations matter

The inspected refresh establishes indices for game-plugin readers, calls `readPluginLists` through the public interface, applies primary-plugin and relationship corrections, checks masters, rebuilds indices, reads locked ordering, and refreshes load order. Raw setters are useful within this ingestion operation. Comparing one setter with a complete UI action assigns it an unsupported contract.

The constructor connects the write signal to game-index generation. `OrganizerCore` connects it to an existing delayed writer, and `savePluginList` uses `onNextRefresh` before saving locked ordering and the game's representation. The LOOT UI confirms the action, saves before sorting, then refreshes and saves after successful sorting. These caller/writer paths were read, not executed. A source-level call, delayed writer request, refresh callback, publication, and effective game state remain separate evidence.

Executable registration, process/job waiting, UI close, and inherited VFS behavior remain outside this band. Acquiring or scouting their source does not qualify `mo2.executables`.

## Models and replay

[Lean](Plugins.lean) predicts complete admitted timelines from original inputs. Seventeen laws cover scalar/bulk policy, write requests, missing-name feedback, derived-order separation, master-presence limits, partial-order fallback, and duplicate lookup state. The [decoder](PluginsCase.lean) requires contiguous catalog IDs, an initial priority permutation, set-shaped master metadata, the closed name vocabulary, and supported action tags. It permits the duplicate order action the source actually accepts.

[Bend](Plugins.bend) provides nine laws and per-step kernels for enabled values, notification membership, assigned priorities/index admission, load indices, missing-master sets, and write requests. Its 208 scalar/list comparisons start from measured prestates and authored requests. It does not carry the full timeline, Qt event stream, lookup-map construction, or writer state. Lean covers the complete fixture timeline and recorded index/callback fields.

The [replay](plugin_conformance.py) checks producer/input/stream identities, reconstructs selected source bodies, checks available artifacts/source blobs, and compares all cases and steps. Eleven changed-observation/decoder controls must fail for their stated reason. Replay executes only formal adapters, never the C++ compiler, Qt fixture, MO2, LOOT, or a game.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/mo2/plugin_conformance.py
```

Compile the modules first. Catalog IDs are fixture positions, not persistent identities across refresh. Missing source caches or private artifacts do not constitute fresh source-execution verification in another checkout.

## API and UX direction

Keep raw ingestion setters where callers intentionally assemble a list before normalization. Document their effects. For extension/UI actions, consider an explicit batch operation that validates names/order against the current catalog/profile, reuses existing game-specific fixups and writer/refresh paths, and reports completed stages. This is a proposal, not an implemented API or a new generic transaction manager.

Validate or deliberately canonicalize duplicate order requests before mutation when promising a coherent permutation. Preserve originals on refusal. Decide unlisted-entry policy explicitly: current catalog fallback is a valid compatibility choice; retaining previous relative priority would change behavior and needs separate controls. Do not change it silently during extraction.

Feedback should distinguish enabled-state edits, pending normalization, queued saving, and observed saved results where evidence exists. Missing-master messages should name the absent requirement; successful presence checks must not imply correct order or gameplay. Lookup-index failures should retain catalog/source context rather than look like file removal.

The keep-current alternative remains useful: retain entry points, clarify their contracts, and strengthen higher-level caller tests. Audit existing refresh callbacks, delayed writing, game features, and signals before adding coordination. For empack, preserve edit, interpretation, preparation, verified output, and native finalization as distinct stages. A setter test or decoded metadata result cannot establish a complete applied operation.

## Remaining verification

Plugin parsing, filename equivalence, metadata/index allocation, primary/light/medium rules, locked order, relationship correction, UI admission, Qt delivery, writer failures, LOOT, profile switches, interruption, Windows/VFS behavior, and gameplay remain unqualified. Source or Qt updates must recheck method/caller contracts, compiler/framework identities, name assumptions, normalization, notifications, and writer integration before advancing pins. No production change or full feature-family qualification is selected here.
