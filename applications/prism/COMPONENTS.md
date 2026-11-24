# Component requirements, protected selections, and launch profiles

This band examines Prism 11.1.1 at `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. It currently retains compiled source comparisons and inspected caller boundaries. Its Lean/Bend models and pure replay are not yet complete, and no inventory operation is promoted by this initial source band. Nothing here establishes a complete Prism dependency resolver or game launch.

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

## Source-only boundaries and open questions

`resolveDependencies(checkOnly)` first gathers requirements and attempts obsolete dependency removal in a loop. Its `checkOnly` gate occurs later and refuses still-required additions or version changes. Therefore the parameter cannot be assumed to mean a universally read-only operation. Full caller execution, persistence, and interruption remain untested here.

Two adjacent source questions need discriminating follow-up before a defect claim or design change:

1. The obsolete-removal loop ignores the boolean result of `PackProfile::remove`. That method can refuse important components or fail while removing local files. The loop's progress and failure behavior need a bounded comparison that preserves failed removal as an outcome; the present one-pass probe does not establish an actual launcher hang or reachable UI state.
2. Component serialization writes `cachedVolatile`, while the inspected decoder reads `volatile`. The cached value can also be refreshed from loaded metadata before dependency decisions. A codec round-trip comparison and caller refresh analysis are needed to establish its observable consequence. The current fixture supplies cached fields directly and cannot qualify this codec.

Launch-profile composition is also only inspected in this band. Components apply in the profile's list order; disabled components are skipped. Only the Minecraft UID can supply the Minecraft version/type/assets through the selected version-file method. Nonempty scalar contributions replace previous strings, JVM arguments append, traits unite, and tweakers are moved later when overridden. Compatible Java major lists append, while the later Java check admits an empty list or membership in that list; its explicit compatibility override warns and succeeds. These policies are not an intersection of arbitrary mod constraints or proof that the JVM/game can run. Library/agent merging, metadata interpretation, Java discovery, process preparation, and UI diagnostics remain separate work.

The native procedures are owner-run `components_probe.py` and `components_order_followup.py`, outside ordinary CI. Generated upstream source and binaries remain ignored; the public captures preserve the producer, input, command configuration, source/generated/binary hashes, compiler streams, observed decisions, and explicit adapters. The full original source retains its upstream license. Native Windows/Linux, actual instance edits, accounts, games, and the proposed portable-authoring runtime remain unqualified.
