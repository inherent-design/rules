# MO2: mapping plans and profile-bound output targets

This record retains selected-source observations for `OrganizerCore::fileMapping(profileName, customOverwrite)` at MO2 v2.5.2 source `9c130cbf2fc7225fb2916e46419af50671772aa0`. It does not install VFS mappings, launch a tool, or establish where a Windows process writes. The [overwrite sync study](OUTPUTS.md) concerns a later, separate adoption operation.

## Compiled boundary

The [collector](routing_probe.py) compiles the unchanged complete method body using the [driver](routing_driver.cpp). Qt 6.12.0 strings, paths, QVariant storage, and offscreen application are real. Profile loading, enabled mod entries, regular-mod classification, game paths, local-save mappings, and file-mapper plugins are controlled adapters. Directory readiness is held true; the wait adapter refuses execution. No actual refresh/signal protocol is exercised.

The [receipt](../evidence/mo2-routing-20261124T145829818462Z/receipt.json) identifies source selection, producer/driver, compiler, SDK, binary, request set, and 19 raw records. The [dependency readback](../evidence/mo2-routing-20261124T145829818462Z/environment.json) identifies current direct frameworks and load commands after execution. Runtime Qt version and offscreen platform match the selected package. This does not qualify MO2's supported Windows dependencies or prove a reproducible application build.

The [source ledger](../sources/mo2-routing-selections.json) separates this executed method from inspected profile, executable-dialog, process-runner, and connector code. The fixture does not execute the real profile parser or mod catalog. Two API-boundary inputs deliberately differ from ordinary UI assumptions: a nonregular custom target and differing requested/current profiles.

## Observed mapping decisions

The [raw records](../evidence/mo2-routing-20261124T145829818462Z/observe.stdout) retain complete ordered mapping lists, accepted/refused results, constructed profile directory, and collected warnings.

| Input                                             | Observed method result                                                                                          |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| No custom target, one or two data paths           | Regular mod mappings followed by overwrite mappings; each overwrite data mapping carries the create-target flag |
| Active regular custom target A                    | A's data mappings carry the flag; overwrite mappings remain present without it                                  |
| Missing custom target                             | Refused                                                                                                         |
| Differently cased custom name                     | Refused under exact name equality                                                                               |
| Reserved overwrite name supplied as custom target | Refused; the reserved active entry is skipped before target matching                                            |
| Active nonregular custom target B                 | Accepted, but neither B nor overwrite receives a data create-target mapping                                     |
| Empty active set and no custom target             | Overwrite mapping remains available                                                                             |
| Local saves enabled for current profile A         | The supplied save feature contributes an A save mapping                                                         |
| Requested B, current A enabled, B disabled        | B is constructed, but the supplied save mapping still uses A                                                    |
| Requested B enabled, current A disabled           | No local-save mapping is added                                                                                  |
| Current local saves enabled, feature unavailable  | Ordinary mappings remain; a warning is collected                                                                |
| Enabled file-mapper plugin                        | Its supplied row is appended, including its own create-target flag                                              |
| Disabled file-mapper plugin                       | Its row is absent                                                                                               |

The two-data-path variants preserve separate occurrences and order. Local-save and plugin rows are not ordinary mod-data targets. The enabled plugin control supplies another flagged row for the same virtual data path; the final list therefore has no universal “exactly one create target” property. Which mapping wins, or whether this is a valid real game-plugin combination, requires the backend and plugin contracts.

These flags are mapping-plan facts. The connector source forwards the flag to directory linking; this fixture does not establish new-file versus existing-file writes, injection, descendant processes, or effective-file precedence. A mapping list is not a confirmed process view or a captured output set.

## Boundaries to investigate

**An enabled name is not necessarily an eligible write backing.** The method marks the custom name active before checking whether the mod contributes regular mappings. Its normal executable dialog filters several special mod classes. The nonregular case therefore tests the method's admitted input boundary, not a reproduced ordinary UI failure. A future target proof should either establish regular writable eligibility or retain an explicit caller precondition; do not turn this source result into a Windows write-loss claim.

**Requested and ambient profile identity are distinct inputs.** The method constructs the requested profile for active mods but uses the current profile for local-save enablement and path. The inspected process runner permits a profile override and also reads executable customization from the current profile before forwarding the selected name. Complete caller/profile-switch reachability and real save consequences remain unresolved. This is a source-level context dependency, not yet a confirmed full-launch defect.

A candidate design would resolve the mapping context explicitly: selected profile, mod set/classification, game paths, local-save policy, executable overrides, and plugin contributions. Reuse the existing profile and mapping types; do not add a second resolver or generic launch framework. If differing profiles are forbidden by the real caller contract, validate that precondition rather than silently mixing them. If overrides are supported, decide which settings intentionally remain ambient and report that basis.

## Evidence limits and remaining comparison

No Lean/Bend routing comparison is claimed by this record yet. The next comparison must retain ordered rows, exact name admission, regularity, requested/current profile distinctions, and independently supplied plugin/local-save rows. Any stronger target/profile rule remains proposed and must not replace these current observations.

Before application adoption, exercise a supported Windows MO2/Qt build with actual profiles, regular/foreign mods, local-save plugins, executable overrides, and file-mapper plugins. Observe physical reads/writes from an injected disposable process, retain originals, and confirm process retirement before capturing output. Qualify inactive or stale targets, profile switches, refusal/cancellation, partial mapping installation, and existing-file behavior. Native initialization, process ownership, mapping installation, output capture, and deliberate mod adoption remain separate obligations. No complete feature family or joined workflow is qualified here.
