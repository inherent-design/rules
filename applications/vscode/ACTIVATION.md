# VS Code: saved enablement and running extensions

Workspace disablement can be saved while already activated code continues to run. Enabling an extension can make its API description available without activating it. A quit request is also distinct from normal exit and observed process absence. The native results support these separate states; they do not establish an instant-revocation defect.

## Native joined lifecycle

The [collection](../evidence/vscode-activation-20261126T042148920855Z/collection-complete.json) uses installed desktop **1.148.0**, commit `661626d0e72f97806550790a98fb87116c9db825`, on macOS arm64. Four separate windows run serially against one private profile and two generated workspace folders. One earlier local VSIX CLI call installs the owned target. A development extension controls the experiment through the real extension API and workbench commands. These are actual application/API operations, not clicked UI controls or separately executed source fragments.

The target has no automatic activation event. It writes its activation, API calls, deactivation, and disposal to an owned event file, and updates a heartbeat. The controller records `getExtension`, `isActive`, `extensionKind`, API results, workspace identity, and host PID. SQLite queries after each normal application exit independently record selected global and workspace enablement keys. Captured process trees and later PID checks supply separate retirement observations.

| Window and request | API/runtime observation | After-exit saved state |
| --- | --- | --- |
| Workspace A: startup, explicit activation | Target is initially visible and inactive. Activation returns its API; a fresh ping and heartbeat witness actual execution. | No target global-disable entry. |
| A: **Disable All Installed Extensions for this Workspace** | Command returns; target remains visible and active. A previously captured API answers another ping with the current host PID. | A has a disabled-target override; installation membership is unchanged. |
| A: quit | At the recorded quit request the API is still active. Target then logs deactivation and disposal; application exits zero. | Disabled override survives exit. Tracked PIDs are absent. |
| Workspace B: startup and activation | The same profile admits the target in B, initially inactive. Explicit activation succeeds. | B has no target override; A's disabled override remains. |
| Workspace A reopened | Target is absent from the extension API, despite still being installed. | The saved A override was applied at startup. |
| A: **Enable All Extensions for this Workspace**, then activate | Enabling exposes an inactive target. A subsequent explicit activation succeeds. | A has an enabled-target override. |
| A reopened again | Target remains visible and inactive; no target activation/event file appears in this phase. | Enabled override remains; installation membership is unchanged. |

There are fourteen live API snapshots and four after-exit observations: **eighteen observations of one joined four-window flow**, not eighteen independent complete workflows. All four application processes were waited for and exited zero. All 29 process IDs in the captured descendant snapshots were absent afterward; a final command-path check found no process referencing the private fixture root. This is bounded evidence for the owned main/target processes and captured descendants, not proof of complete containment of arbitrary detached children.

Desktop access was held during native actions, then released immediately after the last window exited and the subscription was removed. No new GUI run is needed for retained-data verification. Private profiles, databases, logs, originals, and package inputs remain protected.

## Policy, admission, and activity are different values

The [selected source/API contexts](../sources/vscode-activation-selections.json) identify seven commit-addressed files. They are read-only evidence in this band; **zero source methods are separately executed**.

`ExtensionEnablementService` separates workspace-enabled, workspace-disabled, globally-disabled, and default globally-enabled policy. Workspace overrides take precedence over global defaults. Its full effective `EnablementState` also depends on environment, validity, trust, virtual workspaces, kind, dependencies, malicious-extension checks, and other gates. A policy entry alone is not full admission.

The workbench separately computes an `ExtensionRuntimeActionType` and reason. For an enabled-to-disabled extension that is still running, the inspected branch requests a restart or reload to finish disabling it. Auto-restart on focus loss is explicitly off in this fixture. The native results agree with a pending runtime change; the rendered restart button and tooltip were not independently inspected.

The public API documents `Extension.isActive` as “has been activated.” Its activation result/exports and the current `extensions.all` membership are different observations. An old activation flag is not independent proof of continued execution. Here, the captured API's new ping and the target's file receipt supply that additional evidence. Conversely, a description becoming visible after enablement does not attest activation.

The controller supplies another concrete limit: all four startup snapshots record its own `isActive` as false while its asynchronous `activate` function is executing the recorder. False is therefore not proof that no extension code is executing. The target model samples settled calls, not this intermediate activation phase; pending/failed activation remains open. No activation flag here is a sandbox or security-revocation guarantee.

The API's `ExtensionKind` is also not the earlier source picker's `ExtensionHostKind` enum. The owned workspace-kind target reports API kind UI in this local, non-remote window, as the selected API documentation permits. No browser worker or remote host was created.

## Actual scope and incidental effects

The public workbench commands used here operate on **all** eligible extensions for the current workspace. They are not single-target enable/disable APIs. The disable action affected the only installed user target; the development controller is separate from installed profile membership.

The later enable action also wrote a workspace-enabled override for bundled `github.copilot-chat`, which had a global-disabled entry in this fresh profile. The [retained effects](../evidence/vscode-activation-comparison/conformance.json) preserve that broader selection. It is consistent with the command's “All” scope. No claim is made that the bundled extension was activated or that its service behavior was tested. Individual extension action objects are inspected from source but are not native UI coverage supplied by this collection.

All named data, extension, download, shared-data, agent-plugin, and agent-data directories are private. The non-GUI install uses a private HOME. GUI runs use ordinary HOME for keychain compatibility, in-memory secrets, private TMP/XDG paths, disabled telemetry/update settings, and no selected account or Marketplace request. Workspace trust is disabled for this fixture, so the API reports trusted. This is not trust grant/revoke enforcement, a network sandbox, or proof of no incidental OS writes. The four private main stderr files are empty; that does not qualify every bundled extension's health.

Workspace database associations were read after the four runs and linked to the actual folder URIs. Selected SQLite values were read after each corresponding exit. No mid-command database flush or crash durability was measured, and no full historical database image is claimed. The original command/API/target/process records remain unchanged.

## Joined model and evidence checks

[Lean](Activation.lean) and [Bend](Activation.bend) retain per-workspace overrides/default policy separately from live visibility, activation, quit requests, and retirement. Each has twelve laws. Opening or enabling a description does not activate it; workspace A changes preserve B; disable/quit transitions retain the settled activation flag. Those flag laws alone do not prove continuing execution; the fresh target calls and process receipts supply separate native evidence. Only an admitted exit-and-absence receipt permits the research trace's retirement transition.

The [bounded codec](ActivationCase.lean) accepts this normal four-phase profile, not arbitrary VS Code requests. Repeated activation, inactive-target disablement, failed activation, globally disabled initial targets, another host, and crashes remain outside its native profile. Pure state-machine branches beyond measured inputs are authored model behavior, not additional native qualification. Command snapshots follow the recorder's 500 ms settling interval; this is not an instantaneous-transition guarantee or timing SLA. A supplied Boolean is not a process-liveness authority: the [observer](activation_observer.py) validates retained exit, PID, target, API, workspace, and storage records before constructing model inputs.

The [checker](activation_conformance.py) compares all eighteen outcomes with both models. Seventeen DTO refusals cover incomplete traces, wrong identities, unsupported contexts, and missing retirement witnesses. Thirteen changed native observations cover API activity, fresh execution receipts, persisted policy, cross-window storage continuity, workspace selection, admission versus activation, exit, PID absence, and shutdown hooks. One of those controls changes only the bundled-extension effect; it verifies that broader saved changes are retained even though the target model is unchanged. Missing pre-window database observations remain null rather than being relabeled as an observed empty policy.

| Check | Classification and limit |
| --- | --- |
| Owner CLI install | Native archive/profile integration for one generated VSIX. |
| Four desktop windows | One partial end-to-end application/API flow with real persistence and process effects; not clicked UI or complete extension management. |
| Retained Lean/Bend comparison | Pure state/trace model comparison against those observations; no new application execution. |
| DTO and changed-observation controls | Codec/verifier falsification checks; not additional native product workflows. |

Non-checkpoint outcomes deliberately have null stored-policy fields. Retirement outcomes have no callable API observation. These nulls do not mean that policy was absent or that an API getter returned false after its host exited.

Owner checks additionally read current private source/tool/fixture/database identities. Public-only verification excludes those private categories and uses retained evidence. It runs no Code, extension, Node source method, or GUI. The [comparison report](../evidence/vscode-activation-comparison/conformance.json), [inputs](../evidence/vscode-activation-comparison/input.json), and [measured outcomes](../evidence/vscode-activation-comparison/measured.json) retain the exact basis and scope; they do not promote a pending full feature.

## Preservation and design decisions

Preserve workspace-scoped overrides, explicit activation, the existing `isActive` meaning, and restart/reload requirements for running code. Keep the current policy change behavior: forced unloading could discard extension work or bypass orderly cleanup, and this study does not qualify a safe instant unload protocol. “Enable All” should retain its actual broad scope; use an existing single-extension action when that is the intended user operation.

An additive management result is a candidate for automation and operator diagnostics. It could carry affected extension IDs, workspace/profile identity, the saved policy change, the existing runtime action/reason, and separately observed host state. An opaque host incarnation would keep stale observations from being reused after restart; a PID alone is insufficient. Human output could say that a workspace choice was saved and that running code still needs a restart, using the same facts as structured output.

This candidate does not redefine `Extension.isActive`, silently restart hosts, or rewrite existing settings/SQLite formats. Existing Boolean/void callers keep their contracts. A new reporting envelope needs an explicit version and an API/permission decision about which consumers may inspect management state. The host must retain actual restart outcome and uncertainty, preserve unsaved work, and avoid turning a successful policy write into a stop receipt. Keeping the current internal `EnablementState` and `runtimeState` with improved documentation is a reasonable alternative.

Falsify the proposal with pending/failed activation, throwing or blocked deactivation, lost command responses, another policy writer, host crash/PID reuse, real per-extension actions, rendered restart controls, and remote/worker/trust-gated contexts. These remain specific verification obligations, not claimed failures. No production implementation is selected.

For empack, preserve saved author/instance policy, observed installed state, admitted runtime work, stop requests, and actual retirement as separate facts. This native editor comparison supports the existing direction; it does not authorize file publication while a game is running or replace empack's own leases and recovery rules. The same distinction helps Prism describe cancellation and restic distinguish saved selections from completed effects without forcing their domain models to match VS Code.

Full extension enablement, individual UI actions, trust enforcement, automatic activation events, dependency/pack cascades, remote/browser hosts, other platforms, concurrent updates, and interruption recovery remain pending. Run the retained checker with the pinned Lean/Bend tools and `--public`; native collection requires the separately selected owner procedure and desktop lease.
