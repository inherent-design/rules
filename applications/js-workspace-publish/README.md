# Workspace publication and accepted prefixes

A workspace release is a sequence of package operations. Its final exit status does not identify every version already accepted. This band joins selected workspace publication, packing, local registry acceptance, installation, and runtime readback for npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 with Node 26.13.1 on macOS arm64.

It extends the [single-package publication study](../js-peers/PUBLICATION.md), [workspace execution study](../js-scripts/WORKSPACES.md), and [package-contents study](../js-package-contents/README.md). Their different command policies remain separate. Nothing here changes a tool, the production empack engine, or the deferred implementation intent.

## Selected graph and commands

Every project has three generated workspaces in this declaration/path order: a private leaf, a public consumer, and its public producer. The consumer requires the producer's generated code. npm uses an ordinary exact dependency version; pnpm and Yarn use `workspace:*`. These are different supported author inputs, not a claim that npm understands the workspace protocol.

| Profile | Selected command | Observed public upload order |
| --- | --- | --- |
| npm | `npm publish --workspaces --json` | Consumer, then producer. |
| pnpm | `pnpm --recursive publish --no-git-checks --json --report-summary` | Producer, then consumer. |
| Yarn | `yarn workspaces foreach -A -t --no-private npm publish --json` | Producer, then consumer. |

Private registry and authentication-marker arguments are retained in the exact command records. Yarn's ordering and private exclusion are explicit flags. pnpm's Git checks are disabled in these disposable non-Git projects. The collector invokes pinned entrypoints directly, uses private child HOME/configuration/cache directories, disables configured retries, and serves only generated artifacts from its own loopback registry. It changes no host environment or user configuration. There is no public registry, real credential, account, or personal project.

The root `packageManager` field is omitted in the corrected pnpm profile because its presence made this pinned binary resolve a `pnpm` configuration dependency from the fixture registry before publication. That isolated setup failure is retained and excluded from workspace-publication comparison. This does not qualify automatic package-manager acquisition. Yarn has its own initialization call before each publication case; that initialization removes redundant public `private: false` fields. Manifest-preservation checks compare the exact state immediately before publication with the state after it.

## Native observations

Nine publication cases cover normal success, a producer hook failing after upload, and a private leaf's early hook configured to fail. The late hook is npm/pnpm `postpublish` and Yarn `postpack`; these are different lifecycle boundaries.

| Case | npm | pnpm | Yarn, with the selected flags |
| --- | --- | --- | --- |
| Success | Exit 0; consumer and producer accepted. | Exit 0; producer and consumer accepted. | Exit 0; producer and consumer accepted. |
| Producer's late hook fails | Exit 7; both packages remain accepted. | Exit 1; producer remains accepted; consumer never starts. | Exit 1; producer remains accepted; consumer never starts. |
| Private leaf's early hook would fail | Its `prepublishOnly` runs and exits 7 before either public package is uploaded. | Private leaf is excluded before its hooks; both public packages publish successfully. | `--no-private` excludes the leaf before its hooks; both public packages publish successfully. |

The ordinary npm success and late-failure cases also run preparation hooks for the private leaf without uploading it. The selected source catches `EPRIVATE` after preparation; a hook failure has a different error and stops the loop. A private flag is an upload restriction, not a script sandbox. Hooks may intentionally change a manifest, so moving that check earlier needs a deliberate compatibility decision rather than assuming it is a harmless optimization.

The pnpm recursive `pnpm-publish-summary.json` names the accepted producer even when its postpublication hook fails. Its partial summary matches the fixture's accepted records. This differs from the [single-directory caller](../js-peers/PUBLICATION.md), which discards an existing internal published-summary error field. Reuse the recursive retention pattern when reviewing that caller; there is no need for another result framework.

For each success, the received consumer manifest names its producer at exact version `1.0.0`. pnpm and Yarn project `workspace:*` into that packed version without modifying the author manifest during publication. npm preserves its already concrete range. The replay verifies archive SHA256, SHA-1, SHA-512 SRI, exact members, manifest data, and source `index.js` bytes. General manifest transformation, peer ranges, aliases, publishConfig rewrites, and arbitrary packlists are not modeled here.

Each successful pair then goes through a separate generated npm consumer installation and a fresh Node process. All three return `producer:1.0.0`. The consumer locks identify the accepted archives and integrity values, and installed entry bytes match the received archive members. These are three published pairs consumed by **one installer implementation**, not three independently qualified installers or a real registry persistence test.

## Evidence and executable comparison

The retained captures are:

- [Initial npm capture](../evidence/js-workspace-publish-20261125T232855329056Z/commands.json): success, consumer installation/execution, and late-hook failure. Its collector incorrectly expected exit 1 instead of npm's existing exit-7 convention and stopped afterward. The actual late-failure outcome remains part of the comparison; none of those commands was repeated.
- [Remaining-npm and setup capture](../evidence/js-workspace-publish-20261125T232922743988Z/commands.json): private-hook failure plus the excluded pnpm configuration-dependency refusal.
- [pnpm/Yarn completion](../evidence/js-workspace-publish-20261125T232953513250Z/receipt.json): the remaining six publication cases, two consumer pairs, and three Yarn initialization calls.

There are 19 recorded invocations: 18 selected calls and one excluded setup refusal. The selected calls comprise nine publication outcomes, three Yarn initializations, three npm consumer installs, and three Node executions. All recorded process groups are absent; each owned registry thread is joined and its listening socket closed. Frozen producers and original failures are retained. Replay does not rerun any native operation.

[Nine source selections](../sources/js-workspace-publish-selections.json) pin the relevant command, workspace selection, packing, and scheduler boundaries. npm's publication command matches the installed source bytes. The pnpm and Yarn source pins plus entrypoint identities do not establish reproducible source-to-binary builds. In particular, failed-consumer non-start is directly observed; its interpretation as dependency scheduling is supported by the selected source and flags.

[WorkspacePublication.lean](WorkspacePublication.lean) and [WorkspacePublication.bend](WorkspacePublication.bend) reuse the existing single-package publication models. The new model adds the fixed graph's private filter, order, stop boundary, accepted prefix, packed-range observation, and recursive summary. Eleven Lean laws and nine Bend laws keep these distinctions explicit. The decoder admits only the named three profiles and three failure boundaries. Both models agree with 72 scalar observations across nine cases; eight changed-field controls and three decoder refusals protect that comparison. They do not implement HTTP, hooks, semver resolution, or a general scheduler.

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/js-workspace-publish/conformance.py
```

The [comparison](../evidence/js-workspace-publish-20261125T232953513250Z/conformance.json), [basis](../evidence/js-workspace-publish-20261125T232953513250Z/basis.json), and [controls](../evidence/js-workspace-publish-20261125T232953513250Z/controls.json) retain the exact scope. `--public-only` excludes installed-tool, latest private-tree, and cached source readbacks, while preserving the retained archive, stream, lock, runtime-output, and dual-model comparisons. Scripts, tarballs, and publication documents contain generated fixture material only.

## UX and design decisions

Keep package acceptance, hook failure, and packages not started as separate report fields. A batch error should name the failed package and phase, list known accepted identities, and make the unfinished selection visible. Source-qualified dependency blocking should not be presented as an observed runtime incompatibility. A client also must not promote the fixture owner's acceptance record into client knowledge after a lost response; that remains the separate single-package uncertainty case.

Preserve each command's actual policy. npm's declaration order is not a dependency-release transaction. Yarn's explicit topological/private flags are part of this request. pnpm's recursive summary already provides useful partial-publication facts. A better final headline can combine those existing facts without changing script semantics, inventing rollback, or promising batch atomicity.

For empack's proposed publication design, immutable artifacts and revisions should be identified independently of display names, operator approval, channel movement, and later hooks. Reuse known per-artifact outcomes and require reconciliation before retrying an uncertain publication. This band supplies comparative design evidence; it selects no production API, publication service, or wire-format change.

Before adopting changes, retain existing exit and event contracts, private-hook semantics, version-conflict behavior, and selected-order policies. Add focused caller tests for partial summaries and final reporting. Actual multi-package retry/reconciliation, response loss during a workspace batch, package mutation by hooks, concurrent publishers, staged release approval, real registry permissions, and cross-platform behavior remain unqualified. The larger npm/pnpm/Yarn joined scenarios and all parent operation statuses remain unchanged; the full nine-application intent stays active.
