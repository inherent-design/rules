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

## Models and retained comparison

[Lean](Routing.lean) checks 20 laws; [Bend](Routing.bend) checks nine. Both retain ordered ordinary rows, exact-name admission before regularity, current-profile save contribution, overwrite rows, and independently enabled plugin rows. A single method result covers both an optional plan and the local-feature warning. No returned plan is represented separately from a successful empty list.

The [pure replay](routing_conformance.py) matches both models to the [19 retained results](../evidence/mo2-routing-20261124T145829818462Z/conformance.json), including every row's origin, destination, directory flag, create-target flag, and order. It also compares refusal and warning outcomes. Eight malformed research profiles are refused. This decoder uses closed fixture name/path identities, not a general profile, filesystem, or game-plugin codec. It recompiles the exact Lean model before importing it; no Qt, native collector, or MO2 process runs during replay.

Active entries are already supplied from the selected profile. A model comparison that changes only a profile label while holding that list fixed does not simulate loading another native profile. Likewise, the save callback's one-row shape and the supplied plugin row are fixture premises. The comparison does not model arbitrary plugin side effects or callback timing.

A separate design alternative requires a regular custom target and uses the requested profile's save policy/path. Its four differences are retained as proposed results: the two nonregular-target cases refuse, and the two differing-profile save cases follow the requested profile. These do not replace current observations or establish normal caller reachability. Regular classification alone is not a filesystem-writability proof. Alternatively, an API could explicitly require requested and current profile identities to agree. Choose the actual override contract before adopting either approach.

## Evidence limits and verification

An absent plan is not evidence of zero surrounding effects. The real profile constructor is an adapter here, and `beforeRun` saves current profile state before mapping assembly. Neither constructor/prelaunch publication, previous VFS state, nor cleanup after refusal is qualified by the pure result. Preserve the operation's actual scope when presenting a failure.

For empack's portable authoring target, bind prepared work to its selected recipe/profile and captured project inputs. An ambient editor selection must not silently supply another profile's behavior after preparation. Reuse existing interpretation and native constructor authority; this finding does not justify a second mapping engine, generic launcher, or frontend-only policy table. An assembled plan, installed view, running process, retired process, and captured output remain different evidence.

Before application adoption, exercise a supported Windows MO2/Qt build with actual profiles, regular/foreign mods, local-save plugins, executable overrides, and file-mapper plugins. Observe physical reads/writes from an injected disposable process, retain originals, and confirm process retirement before capturing output. Qualify inactive or stale targets, profile switches, refusal/cancellation, partial mapping installation, and existing-file behavior. Native initialization, process ownership, mapping installation, output capture, and deliberate mod adoption remain separate obligations. No complete feature family or joined workflow is qualified here.
