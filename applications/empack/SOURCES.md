# Source identity, placement, and consumer projection

Empack's portable-authoring extraction should preserve its current layer and choice rules. A captured source, its bytes, a placement, an output recipe, and a verified artifact are different values. This band compares the actual pure core at `0b4462e3032b4f09230b15329722eabefb7f574c` and develops the corresponding source/placement boundary for the separate 0.9 candidate. It changes no production code or project schema.

## Actual core evidence

The [receipt](../evidence/empack-projection-20261124T063515339963Z/receipt.json), [commands](../evidence/empack-projection-20261124T063515339963Z/commands.json), [driver](../evidence/empack-projection-20261124T063515339963Z/driver.rs), and [observations](../evidence/empack-projection-20261124T063515339963Z/observed.stdout) identify 32 named cases. The [collector](projection_probe.py) copied all 18 core source files from the pinned Git revision, checked their bytes against the checkout, compiled that unchanged dependency-free library, and linked the small [driver](projection_oracle.rs). All commands completed, and source hashes matched afterward. This is a standalone Mac arm64 core build, not execution of the installed 0.8.8 CLI or the complete engine.

The driver constructs fictional content labels, one choice key/description, two valid destination labels, and selected snapshot recipes. Embedded test entries all use writable/executable attributes. Subscribed recipes, other attribute combinations, and consumer-specific integration are not exercised. It asserts that the input values remain unchanged. Those values exercise real planner APIs but establish no acquired bytes, authentic source, content lease, filesystem state, or publication permission. Private generated work occupies about 10.7 MiB.

An [earlier attempt](../evidence/empack-projection-20261124T063406279007Z/disposition.json) compiled the core but failed to compile the fixture driver because it moved a borrowed option. Its original source and diagnostics remain separate. The corrected borrowing code has a new run identity; the failed attempt contributes no API cases. Its ignored generated work is about 9.6 MiB.

## Values and phases that already exist

| Value | Meaning | What it does not establish |
| --- | --- | --- |
| `ContentOwner` | Semantic source/dependency/runtime reason for an output | Its native path, byte authenticity, or deletion authority |
| Acquisition source | Where required bytes can be obtained, with original assertions | A placement or permission to overwrite that source |
| Content identity | Observed byte identity or an explicitly retained observation | Independent source authentication or one unique placement |
| `Placement` | Destination, layer, and participation | Host writer authority |
| `BuildProfile` / `Recipe` | Complete consumer, delivery, environment, update policy, and container selection | That the output is generated, verified, hosted, or published |
| `BuildSelection` | Surviving obligations before representation completion | That all needed bytes have been acquired |
| `BuildInventory` | Expected entries whose representation fields satisfy the core's completion checks | Verification of actual archive/file bytes or an engine execution grant |

The [source ledger](../sources/empack-projection-selections.json) pins inspected declarations and implementation. Global validation precedes projection: duplicate layer/destination claims, invalid side participation, inconsistent choice metadata, and unknown supplied choices fail before selection. Avoiding an unnecessary prompt for a shadowed optional is distinct from accepting invalid semantic input.

For a flat client view, precedence is client, shared override, then common. The server view uses server, shared override, then common. `CommonOverride` is a separate layer from the common base; a portable tree must not collapse them because both sound shared. A chosen higher layer replaces the whole file and records applicable displaced owners. It does not merge settings or delete the author's lower source.

The observed cases establish these bounded behaviors:

- With all four layers, client and server select their own entries. Reversing input order leaves the selected client result and precedence unchanged.
- With no applicable side entry, a shared override replaces common.
- An explicitly disabled optional side entry exposes common. An enabled one replaces it. Default-based decisions retain that provenance.
- A shadowed unresolved lower optional is not asked. Conflicting declared choice metadata still fails global validation.
- A flat preserved optional overlay cannot erase its lower fallback. It requires a selected policy. A lone optional can remain selectable in a reference Prism view.
- Mrpack and native-release recipes retain applicable layers and choices. Client-only native projection omits the server side. Native bundled output can retain conditional entries whose bytes must be included for later choices.
- A selected unacquired representation fails completion. A shadowed or opposite-side obligation can disappear from that selected view. Download references require their expected evidence/origin fields; full delivery also needs embedded content.
- Two placements remain two entries even when they use the same fictional byte label.

“Selected” therefore means surviving obligations, which can include preserved conditional inputs. It does not always mean one currently enabled recipient configuration. Acquisition and actual verification must follow the selected recipe's requirements.

## Models and comparison

[Lean](Projection.lean) defines layers, environments, typed requirements, representation states, policies, choice receipts, selection, precedence, and completion. Its ten laws preserve lower-choice masking, optional fallback, source/destination/representation identity during flattening, and incomplete/invalid representation distinctions. One fixed choice key and fixed description are explicit premises. The download cases vary accepted observations and origins with no independent digest assertions; digest-bearing references need separate qualification.

[Bend](Projection.bend) models one destination's ordered flat-layer choice and representation gates, with four laws. Its adapter supplies already-admitted candidates; it does not independently implement global validation, recipe decoding, or preserved-layer inventories. These narrower scopes remain explicit.

The [replay](projection_conformance.py) matches all 32 captured outcomes, selected-entry membership, precedence, and choice provenance against Lean. Bend matches 22 flat-destination decisions and 36 completion gates. Replay also checks producer/driver/stream hashes and the actual Git source identities. It refuses unsupported research schemas, recipes, policies, layers, requirements, representations, and destination labels. These are research decoder limits, not claims that the application lacks other supported values.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/projection_conformance.py applications/evidence/empack-projection-20261124T063515339963Z
```

Compile the formal modules first with the pinned toolchain. Replay starts no compiler, empack process, network request, or consumer. Membership is normalized for comparison; presentation order, arbitrary paths, provider identities, templates, bindings codecs, real bytes, and host behavior remain unqualified.

## Portable source and interface proposal

The [authoring model](AUTHORING.md) already separates project images, edit epochs, saved revisions, retained assets, and prepared inputs. The source layer should fit that model rather than introduce a second interpretation of pack contents.

1. **Retain assets before publishing mappings.** A virtual source tree maps portable project paths to immutable asset references. Keep byte identity, length, original assertions, attributes, provenance, and available/permission-needed/missing state distinct. Native paths, browser handles, and backing-object ownership stay host-specific. A computed digest does not upgrade a source assertion.
2. **Interpret source mappings and authored placement separately.** One asset may serve multiple sources or placements. Moving a placement does not authorize deletion of a source; current native rules also protect a path still used by another surviving local/archive source. Retain current, saved, history, plan, and pending roots under the existing retention protocol.
3. **Compose authoring and bindings before planning.** The current codec merges the separate bindings document into intent and rejects unknown keys, conflicting placement, and inapplicable source members. Targeted splitting preserves which document authored inline integration. The project image must retain raw documents, including absent versus present-empty bindings; a default semantic re-encode is not automatically a lossless project save. This codec was inspected, not executed by the core driver.
4. **Preserve explicit source roles and traversal policy.** Incidental source discovery uses captured exclusions. Explicit locked source/member obligations do not disappear merely because an exclusion matches their path. Discovery completeness, byte availability, and operation-specific observation demand remain separate; the [observation-demand proposal](OBSERVATIONS.md) owns that distinction. Do not import Git/global ignore policy into pack traversal.
5. **Reuse the shared projection on captured semantic inputs.** A native directory adapter and a browser virtual tree may produce equivalent `InventoryInput` values only after their own capture/validation. The same profile, layer/requirement semantics, assertions, attributes, and choices should then produce equivalent expected inventories. This is an adapter obligation, not proof that either adapter or a project codec already exists.
6. **Keep templates an explicit interpretation.** Current template addressing selects layer, destination, and rendering mode before collision checks. It differs from ordinary source placement; `.template` changes the destination spelling, and modes can explicitly copy or render. A generic virtual tree must preserve these rules, bounded reads, output limits, and shared language-specific quoting helpers. Template execution was not exercised here.
7. **Advance through separate verification boundaries.** Capture an immutable image and retain plan inputs; validate intent and capabilities; select obligations; acquire/verify the required representations; generate and verify the consumer output; finalize delivery. Core completion, a host callback, or a selected UI checkbox cannot construct a verified output, native change, or runtime grant.

This preserves native semantics while allowing incomplete raw drafts to remain saveable. Export still needs valid authoring semantics and the selected operation's capabilities. It does not silently discard malformed input to manufacture a valid subset. No general migration framework or arbitrary executable generator interface is selected.

## UX and compatibility decisions

In an editor or detailed plan view, show the selected source, destination, layer, displaced fallback, and choice/default reason together. A disabled optional should explain the restored fallback; an ordinary cross-layer replacement should not become an unused-file error. Default CLI output can remain concise, with this evidence available in details. Keep human and structured reports derived from the same selection facts.

A source-confirmed wording candidate exists: `ReferenceChoicesMustBePreserved` displays “Mrpack output preserves optional choices,” although its guard also covers native empack recipes. A consumer-neutral message should explain that the output retains installation choices. The rejected native CLI path was not executed, so this is a scoped core diagnostic finding, not a reproduced end-user workflow defect.

The keep-current option remains credible for the core: its current selection/completion split and precedence receipts already expose useful boundaries. Prefer extracting these services and supplying attributable source adapters over replacing the planner or adding a generic trusted-host interface. Preserve existing profile meanings, selectors, raw/semantic revisions, original assertions, and native recovery authority. A new project container remains an explicit versioned format, not a silent rewrite of old native state.

Required follow-up includes general choice maps/descriptions, provider file roles and filename changes, bindings round-trips, actual source capture/exclusions, template rendering and collisions, path aliases/directories, recipe/archive verification, missing assets, stale plans, lease retention, and the real local-JAR/config import → edit → save/reopen → consumer export flow. Native/browser semantic equivalence, WASM compilation, storage durability, and consumer acceptance remain open.
