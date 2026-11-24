# Component requirements, protected selections, and launch profiles

This band examines Prism 11.1.1 at `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. Compiled source comparisons, scoped formal models, and retained replay cover requirement composition, protected selections, cached metadata, and a removal-loop boundary. Nothing here establishes a complete Prism dependency resolver or game launch. [Launch-task sequencing](LAUNCH.md) and [mrpack update planning](README.md) remain separate bands.

## State and ownership

A component UID identifies an installed or requested component, not a version rank. Cached version metadata supplies requirements and a volatility flag. The persisted selection separately records dependency-only, important, and disabled flags; local custom-file presence supplies another independent state. These properties answer different questions:

- Exact requirements constrain a particular UID/version string.
- Suggested versions guide a missing component without becoming an exact requirement.
- Dependency-only status permits certain automatic version adjustments; an explicitly selected component is protected against those adjustments.
- A custom component's non-null file makes its differing version protected even when dependency-only.
- Volatility permits a no-longer-required dependency-only component to become an automatic removal candidate.
- Important and dependency-only components cannot be disabled through the selected activation predicates.
- Disabled, removable roots remain part of requirement gathering; effective launch-profile application separately skips disabled components.

The [source selections](../sources/prism-components-selections.json) identify each inspected byte range and its limits. Cached getters and field presence in the fixture do not prove that real metadata was downloaded, parsed, validated, or durably saved.

Requested `m_version` and loaded/cached `m_cachedVersion` are separate values too; the selected `getVersion` method returns the cached value. The codec fixture supplies equal values and does not qualify their asynchronous reconciliation. A cached getter cannot by itself prove that the requested metadata has loaded.

## Compiled decision comparisons

The [primary capture](../evidence/prism-components-20261124T111134328480Z/receipt.json) retains 19 cases through unmodified requirement composition, gathering, obsolete-candidate selection, and trivial-change functions. It also executes selected component accessors and activation predicates. `Meta::Require`, the actual `Version` implementation, Qt `QString`/containers, and the list/index aliases are retained unchanged in ignored compilation inputs. The fixture supplies the component declaration, cached fields, and pointer/loading adapters. A custom file is represented by a non-null marker; no real component file is created or validated.

The compiler uses C++20, `-O0`, `QT_NO_DEBUG`, and Qt 6.12.0. Both the package metadata and executing binary report that Qt version, within the pinned Prism source's supported Qt-6 baseline. The comparison is headless and does not open a launcher profile or personal state.

| Input distinction                                             | Observed decision                                                                                                           |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Missing exact requirement                                     | Proposes adding the required UID at the first dependee's index.                                                             |
| Existing exact match                                          | Requirement is met.                                                                                                         |
| Differing non-custom dependency-only version                  | Proposes changing it to the exact requirement.                                                                              |
| Differing explicit version                                    | Refuses the change plan.                                                                                                    |
| Differing custom dependency-only version                      | Refuses the change plan.                                                                                                    |
| Same exact version required twice                             | Combines the requirement and preserves the earliest dependee index.                                                         |
| Unconstrained and exact requirements                          | Retains the exact requirement.                                                                                              |
| Different nonempty exact requirements                         | Requirement gathering fails; subsequent change planning is not run.                                                         |
| Numeric suggestions `1.2` and `1.10`                          | Uses the actual version comparator and keeps `1.10`.                                                                        |
| Exact requirement plus another suggestion                     | Retains both as distinct fields; a suggestion does not erase the exact version.                                             |
| Unreferenced volatile dependency-only component               | Proposes removal.                                                                                                           |
| Unreferenced nonvolatile dependency or explicit volatile root | Does not propose removal.                                                                                                   |
| Required volatile dependency                                  | Keeps it.                                                                                                                   |
| Disabled root with requirements                               | Those requirements are still collected.                                                                                     |
| Disabled flag on dependency-only or important component       | The selected source predicate still reports it enabled. This is not proof that the UI can create that raw flag combination. |

These are one-pass proposals. The probe does not run the caller's removal fixed point, metadata reload, version assignment, download, or publication. A proposed addition is not an installed component, and a proposed removal is not confirmed file deletion. On a gathering conflict, the partial requirement set is retained for observation; it is not presented as an applicable plan.

## Version spelling and ordering

A [three-case follow-up](../evidence/prism-component-order-20261124T111344706573Z/receipt.json) uses the same attributed binary without recompiling or modifying it. It distinguishes ordering from identity:

- Suggestions `1.2+left` and `1.2+right` have equal comparison rank because this comparator ignores appendices. The newly composed suggestion wins that tie. Reversing component order reverses the retained spelling.
- Exact requirements `1.02` and `1.2` conflict even though the comparator normalizes numeric leading zeros. Exact matching uses the original strings.

A model that uses a commutative set maximum for suggestions, or normalizes exact selections through a version rank, would erase these observed policies. Earliest insertion position and suggestion tie choice also have different ordering roles. This is a policy distinction, not a demonstrated defect. The comparison does not qualify every FlexVer string or the downstream availability of either suggested spelling.

## Removal and cached-state boundaries

`resolveDependencies(checkOnly)` first gathers requirements and attempts obsolete dependency removal in a loop. Its `checkOnly` gate occurs later and refuses still-required additions or version changes. Therefore the parameter cannot be assumed to mean a universally read-only operation.

The [expanded boundary capture](../evidence/prism-component-boundaries-20261124T115810215571Z/receipt.json) executes the unchanged codecs, requirement-array helpers, cache-refresh method, removal methods, and the caller's loop prefix through its `while` condition. The fixture closes the method there; the caller tail is deliberately excluded. Constructors/loading, typed JSON conversions, model-row notifications, save scheduling, and local-JAR filename resolution are adapters. They neither parse arbitrary corrupt native state nor establish durable publication. An [initial capture without local JARs](../evidence/prism-component-boundaries-20261124T112753590091Z/receipt.json) remains intact; its first seven results agree after removing the added observation fields.

For removal, the fixture creates its own patch file. A writable directory permits deletion, removal from the component list, one invalidation, and one scheduled-save callback. A directory changed to mode `0555` produces three real `QFile` “Permission denied” failures. Each failed removal leaves the candidate and file present. The unchanged caller ignores the false removal result and retries the same stable snapshot. A fixture guard throws before a fourth attempt; that guard is not in the product. Important-component refusal follows the same nonprogress path without attempting deletion. The raw flag combination's reachability through the real UI remains unqualified.

Both writable and permission-denied cases run with `checkOnly` true and false. Successful obsolete removal still occurs before the check-only gate; failed removal still does not reach that gate. Original directory modes are restored. Save callbacks are counters, not evidence of a saved profile. This demonstrates nonprogress in the stable, single-candidate source prefix under an actual OS refusal. It does not claim that a complete native Prism GUI hang was reproduced.

The local-JAR control makes the effect boundary more specific. A writable patch directory and read-only JAR directory allow the patch file to be deleted before the JAR removal fails. The component record and JAR remain, and the loop retries without restoring the patch. A writable-JAR control removes both files and the record. These use real `QFile` operations at fixture-supplied owned paths; actual library discovery and filename validation remain unqualified. A false result therefore does not imply that every file was preserved.

| Fixture                  | In-memory component-list entry | Patch file | Local JAR    |
| ------------------------ | ------------------------------ | ---------- | ------------ |
| Patch permission refusal | Retained                       | Present    | Not included |
| JAR permission refusal   | Retained                       | Deleted    | Present      |
| Both deletions succeed   | Removed                        | Deleted    | Deleted      |

The table describes observed fixture effects, not durable profile publication.

The proposed correction handles a false removal result as a terminal failure of this resolution attempt. Retain the component record and report the affected UID/cause plus confirmed partial file effects. It must not turn “stop retrying” into “successfully removed,” promise rollback, invent a runtime timeout, or retry without a changed basis. The existing `PackProfile::Result` success/error convention is a candidate for carrying the cause before inventing another error hierarchy. Boolean callers and signal/slot or function-pointer expectations need review; a compatibility facade is an option. That result type alone does not supply an effects receipt or rollback.

A no-change alternative retains the demonstrated source loop; it does not resolve this failure boundary. Qualification still needs the complete instance/controller, real library discovery, multiple local JARs and mixed effects, metadata transitions, interruption, and delivered UI diagnostics. The native fixture proves partial deletion and repeated failure in a source prefix, not a complete GUI/controller failure or a production fix.

For the codec, a component with `cachedVolatile=true` writes that key, but the decoder reads `volatile` and yields false. Required/conflicting entries and selected identity/name/version survive this valid-input fixture. Calling cache refresh without metadata clears the dependency/conflict cache; it does not establish a valid empty dependency graph. Supplying loaded metadata restores its volatility and dependency facts. Repeating the same metadata emits no new notification, while changing an exact requirement under the same UID does replace that cached requirement and emit a notification.

This establishes a cached-field round-trip mismatch, not a demonstrated game failure or loss of authored component data. The inspected load path refreshes cached data before normal dependency decisions. The smallest candidate aligns the reader and writer's cached key, with an explicit policy for existing `volatile`/`cachedVolatile` files and false-versus-absent values. It need not introduce a new general migration subsystem. Keeping current behavior plus loaded-metadata refresh can avoid the downstream mismatch in the ordinary path, but leaves the codec inconsistency. Missing/partial metadata, legacy or contradictory fields, malformed JSON, root persistence, and actual application recovery remain separate tests.

An initial boundary build omitted the fixture's `getID` declaration. Its [disposition](../evidence/prism-component-boundaries-20261124T112644195656Z/disposition.json) retains the original producer and four compiler errors, with no executed native cases. The successful capture is separate. This was a harness omission, not a Prism defect.

## Models, UX, and compatibility

[Lean](Components.lean) proves 26 laws; [Bend](Components.bend) checks ten. Lean models complete selected requirement gathering and one-pass proposed changes, while Bend compares the exact/suggestion, adjustment, activation, and retention predicates. The cache and retry projections preserve their own state rather than borrowing the success of another phase. Record, patch, and JAR presence remain separate after partial failure. Equal-rank suggestions are ordered; exact identities remain unnormalized; partial lists on failure are observations rather than application authority.

The pure [replay](components_conformance.py) matches 22 component cases, two multi-step cache traces, and seven removal-prefix cases with the Lean model, plus 150 scoped Bend comparisons. Seven invalid research inputs are refused, including unknown suggestion ranks and duplicate identities. This says which fixture inputs the research decoder supports, not which inputs Prism rejects. Suggestion ranks are admitted for the selected strings; neither model implements general FlexVer, metadata loading, UI reachability, or a complete resolver.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/prism/components_conformance.py \
  applications/evidence/prism-components-20261124T111134328480Z \
  applications/evidence/prism-component-order-20261124T111344706573Z \
  applications/evidence/prism-component-boundaries-20261124T115810215571Z
```

Compile `Components.lean` to `.build/formal/applications/prism/Components.olean` first. Ordinary proof checks execute no launcher or native collector. Native procedures are `components_probe.py`, `components_order_followup.py`, and `components_boundary_probe.py`, outside ordinary CI. The order follow-up reuses the primary capture's attributed executable; no compiler result is claimed for that follow-up.

Preserve protection of explicit/custom component choices and the narrower permission to adjust non-custom dependency-only components. A useful conflict message can name the requiring component, required exact version, and protected current selection, then guide the user to change their chosen version or undo the incompatible request. For obsolete cleanup failure, report the failed removal and retained state through the existing task failure path. Another successful gathering pass or a longer spinner is not useful progress.

Preserve disabled-component requirements unless a separately chosen product policy changes them. Disabled does not mean uninstalled or unused: keeping requirements can support later re-enablement. Explanations should distinguish those states without adding a long warning to every successful launch. Similarly, suggestion ranking should not silently rewrite exact component IDs or introduce a generic cross-program version normalizer.

These proposals can reuse component/task/model state. A shared host primitive is unnecessary for the current boolean-removal handling. Public profile/metadata formats and existing users need comparator-specific compatibility choices; empack's selected clean-break project-format policy does not authorize breaking Prism's files. Full profile persistence, native application acceptance, and any upstream patch decision remain open.

## Other inspected boundaries

Launch-profile composition is also only inspected in this band. Components apply in the profile's list order; disabled components are skipped. Only the Minecraft UID can supply the Minecraft version/type/assets through the selected version-file method. Nonempty scalar contributions replace previous strings, JVM arguments append, traits unite, and tweakers are moved later when overridden. Compatible Java major lists append, while the later Java check admits an empty list or membership in that list; its explicit compatibility override warns and succeeds. These policies are not an intersection of arbitrary mod constraints or proof that the JVM/game can run. Library/agent merging, metadata interpretation, Java discovery, process preparation, and UI diagnostics remain separate work.

Generated upstream source and binaries remain ignored; the public captures preserve the producers, inputs or controlled modes, command configuration, source/generated/binary hashes, compiler streams, observed decisions, and explicit adapters. The full original source retains its upstream license. Native Windows/Linux, actual instance edits, accounts, games, and the proposed portable-authoring runtime remain unqualified.
