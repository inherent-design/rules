# Yarn version decisions and application

**A saved release decision, an announced version, a saved manifest, and a completed command are distinct states.** In the measured Yarn 4.19.0 profile, a failed apply can consume its saved decision before the manifest version is written. The selected recursive option also traverses dependencies while its help describes dependents.

## Sources and fixture scope

The native executable is the pinned official Yarn 4.19.0 distribution, invoked by Node 26.13.1 on macOS. The official `@yarnpkg/cli-dist` registry's latest tag still selected 4.19.0 at inspection and its archive integrity matches the retained executable's acquisition pin. This is a versioned observation, not a global tool update or a source-to-bundle reproducible-build claim.

Five selected plugin-version source files and separate Workspace/Project context are pinned to `62edcb0e2f62c93b7b2ec2ef6a79edeaf2e06b3c`. Their blob identities independently match the retained tag tree. The current command documentation describes [deferred decisions](https://yarnpkg.com/cli/version), [application](https://yarnpkg.com/cli/version/apply), and [checks](https://yarnpkg.com/cli/version/check); the pinned source and retained native results establish this band's precise profile.

The disposable project has three versioned workspaces: `beta` depends on `alpha`, and `gamma` depends on `beta`. The root has no version. Only workspace packages are materialized. Configuration, cache, home, state, Git identity, and hook paths belong to the fixture; network and scripts are disabled. A failure control deliberately names a missing local archive within the disposable root. No registry publication, external package download, personal repository, account, game, global installation, or GUI is involved.

There are 28 retained commands: 24 qualified version/decision operations, one fixture-only workspace installation, and three earlier check calls excluded because an incomplete lockfile stopped them before decision checking. Every recorded process group exited and was absent at capture completion. The original failed setup remains retained rather than being relabeled as valid negative-check coverage.

## Values, owners, and policies

| Value | Owner and meaning |
| --- | --- |
| Manifest version | The workspace's saved package identity |
| Dependency range | A dependent's separate constraint/reference to that workspace |
| Deferred record | Declarative release strategy or explicit version, keyed by workspace identity |
| Decline | An explicit decision that the workspace does not need a bump; it is not an undecided entry |
| Resolved target | A version computed from current manifests and applicable records |
| JSON announcement | The target selected in memory; it does not prove a completed write |
| Git change set | Input to decision checking, separate from installed workspace state or a published release |

A relative `patch` or `minor` record is a policy to resolve later, not necessarily an immutable reviewed plan against an exact manifest revision. The source resolves multiple records by their greatest suggested version. This is a legitimate product distinction from an operation plan that promises revision-bound application. The finite native profile exercises separate workspace records, not every merge, prerelease, or version-ordering case.

Recording leaves manifests unchanged. Applying a selected workspace consumes its applicable record, changes its version, and can rewrite dependent ranges while leaving the dependents' own versions unchanged. A later all-workspace application consumes the remaining bump and updates its dependent range. Repeating a successful apply with no records makes no additional bump in the measured fixture.

An explicit downgrade needs `--force` when recorded **and again** when applied. The stored version is not a durable permission grant from the earlier invocation. The unforced second request refuses while retaining the record; the forced apply changes the version and dependent range.

## Recursive scope differs from help

The pinned command help source describes `--recursive` as including workspaces that depend on the current workspace. Source calls `getRecursiveWorkspaceDependencies`, and native dry runs return:

| Current workspace | Native ordered bump targets |
| --- | --- |
| alpha | alpha |
| beta | beta, alpha |
| gamma | gamma, beta, alpha |

These are dependency traversals. They do not establish a general cyclic graph or every dependency-scope policy. Keep target membership, traversal order, and dependent range rewriting separate: an unchanged dependent version can still have its range updated by applying another workspace's bump.

The compatible correction is to clarify help to match current traversal. Changing traversal direction can alter actual write scope and needs an explicit product/API decision. If both directions become supported, name them separately and test their closures, rather than silently reversing the existing flag.

## Apply failure consumes an unapplied decision

The joined control follows ordinary CLI boundaries:

1. Record an alpha patch while its manifest is `1.2.3`. The record exists; the manifest stays `1.2.3`.
2. Preview apply. JSON announces target `1.2.4`, and saved files remain unchanged.
3. Apply with the deliberately missing local archive still declared. JSON announces `1.2.4`, then the command fails with `ENOENT`. The actual manifest stays `1.2.3`, but the deferred record is gone.
4. Remove **only** the intentionally missing development dependency and retry. The command succeeds without bumping alpha because there is no remaining decision to apply.

The [owner-edit record](../evidence/yarn-version-20261125T193206031858Z/owner-edits.json) binds the repair to both command images. It does not recreate the version decision. The native log, file hashes, record contents, and retry are independently retained in that cohort.

The source explains this bounded behavior: it mutates in-memory release targets and reports them, calls `updateVersionFiles` or `clearVersionFiles`, and only then runs `installWithNewReport`. Resolution/fetch precedes `Project.persist`. This is a reproduced loss of the selected deferred intent on a controlled pre-persistence failure. It is not a claim that every failure loses records or that no manifest can be written before other failures.

## Checking decisions is a different operation

In the initialized Git fixture, only alpha's tracked source changes:

- Without a decision, `version check` fails and identifies the modified workspace.
- Recording alpha's patch makes beta's missing dependent decision visible.
- Explicitly declining beta makes the check succeed. Gamma does not need a decision merely because it depends on a declined beta.

The check validates these release-decision obligations. It does not apply versions, stage files, test runtime compatibility, compile packages, or publish anything. Git HEAD and index stay unchanged; recording legitimately changes working-tree status by creating a decision file.

The initial marker-only project was insufficient for this check's lock admission. Three old calls returned exit 1 for that setup error, not the intended missing-decision reason. The [scope qualification](../evidence/yarn-version-20261125T193018678360Z/scope-qualification.json) excludes them. A fresh initialized project adds diagnostic-reason assertions and supplies the actual check observations. This illustrates why a negative test must check the failed boundary and useful cause, not only a nonzero status.

## Models and verification

[Versions.lean](Versions.lean), [VersionsCase.lean](VersionsCase.lean), and [Versions.bend](Versions.bend) contain 26 Lean and 16 Bend laws. The native comparison covers three ordered scope frames, nine record frames, 27 per-workspace apply frames, three checks, and 18 dependent-range frames. Both models match 282 scalar projections. The stable numeric version, three-node acyclic graph, literal YAML, and caret/tilde range profile are explicit premises, not complete implementations of those languages.

The [conformance receipt](../evidence/yarn-version-20261125T193018678360Z/conformance.json) records retained basis identities, source/tool availability, rejected interpretations, and decoder refusals. Run the retained-data observer with the pinned tools and the model's olean available:

```sh
LEAN_PATH="$PWD/.build/yarn-version-formal" python3 applications/yarn-version/conformance.py
```

Set `LEAN` and `BEND` if they are outside `PATH`. Replay reads the captures and executes only the research models. It does not invoke Yarn, Git setup, installation, or native fixture collection. Private cache loss is reported as availability, not silently counted as fresh qualification.

## Proposed correction and recovery contract

**Report recording, planning, and persistence separately.** Normal deferred writes in the fixture succeed silently; a short record result could identify the workspace, saved decision path, and apply command. The forced deferred warning should describe a recorded lower target rather than imply that the manifest already changed. A target announcement should say what is planned. A completed/save result needs independent confirmation of the relevant manifest and range writes. On failure, keep the per-target outcome and whether records were consumed visible. Machine callers need the same distinctions; renaming a success-sounding headline alone does not repair consumed intent.

**Retain a resolved apply target until its saved state is confirmed.** Preserve the relative decision's provenance, current basis, exact resolved target, affected range edits, and ownership while application can still fail. If persistence is unobserved or ambiguous, retain recovery information. After confirming the scoped target image, acknowledgement may consume the corresponding decision without incrementing again. A changed basis or conflicting observed state needs review; retry must not blindly reevaluate `patch` against a version already saved by a partial attempt.

The candidate laws model this acknowledgement boundary only. They do not implement a journal, transactional multi-file save, install rollback, crash recovery, or a durable receipt store. Any implementation must define its serialized record/receipt version, exact saved scope, concurrent-writer authority, and how old relative records are admitted. A compatibility plan must preserve existing command flags and machine output or explicitly version their changes. Do not silently reinterpret old release files as exact reviewed plans.

A smaller keep-current alternative is to report consumed records and guide deliberate record recreation after inspecting saved versions. That preserves current storage behavior but leaves recoverability dependent on external history. Merely moving cleanup to command success is insufficient: a later link/build failure may occur after some manifest writes, and reapplying a retained relative bump can increment twice.

Falsifiable implementation checks include this missing-input failure and repair/retry, partial or unknown manifest writes, a failure after metadata persistence, unrelated concurrent edits, multiple selected workspaces and ranges, downgrade authority, no-op/equal targets, record merge, and recovery interruption. Compare both current and candidate policies without weakening version or source admission.

For empack, retain the existing distinction between a request, revision-bound plan, saved state, and downstream preparation. This Yarn example informs that design; it does not authorize changing empack's engine or adopting Yarn's release records. General Git staging, prereleases, full dependency graphs, I/O/crash faults, registry publication, and other hosts remain pending. The parent inventory operations gain component evidence only.
