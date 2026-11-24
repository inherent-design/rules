# Install hooks, review policy, and explicit scripts

A script setting governs a particular operation, not every process a package manager can start. This band compares dependency install hooks, root install hooks, and an explicitly requested root script under npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0. Execution permission, review state, command status, installed files, and hook-written output remain separate facts.

## Native scope and results

The [receipt](../evidence/js-scripts-20261124T054018650056Z/receipt.json), [case configurations](../evidence/js-scripts-20261124T054018650056Z/cases.json), and [raw trace](../evidence/js-scripts-20261124T054018650056Z/trace.json) identify the exact tools, generated archive, commands, streams, and before/after observations. The [retained marker files](../evidence/js-scripts-20261124T054018650056Z/retained-effects.json) were copied after the run and verified against its final snapshot hashes. The owner-run [collector](probe.py) used private roots on macOS arm64, offline installation, isolated configuration/cache directories, and one harmless generated package. Its hooks append markers inside the private fixture and can deliberately fail after postinstall. No third-party hook or production project ran.

There are 42 commands: 21 installs, 18 independent module queries, and three explicit root-script requests. Yarn's nominal broad-allow case repeats its enabled-default explicit-denial configuration; Yarn has no equivalent broad-bypass flag in this fixture. This is a duplicate control, leaving 20 distinct install profiles. Keep the original records rather than relabeling them as a new policy dimension.

For the generated dependency, these are the measured decisions:

| Effective policy | npm | pnpm | Yarn |
| --- | --- | --- | --- |
| No review entry, ordinary defaults | Run hooks; exit 0 | Skip hooks; exit 1, `ERR_PNPM_IGNORED_BUILDS` | Run hooks; exit 0 |
| Explicit denial | Skip; exit 0 | Skip; exit 0 | Skip; exit 0 |
| Explicit allowance | Run; exit 0 | Run; exit 0 | Run; exit 0 |
| Scripts disabled, explicit allowance | Skip; exit 0 | Skip; exit 0 | Run; exit 0 |
| Broad allowance plus explicit denial | Run; exit 0 | Skip; exit 0 | Duplicate of explicit-denial control |
| Allowed postinstall writes a marker, then exits 7 | Three markers; exit 7 | Three markers; exit 1 | Three markers; exit 1 |

The disabled settings are npm/pnpm `--ignore-scripts` and Yarn `enableScripts: false`. They are deliberately not modeled as one portable switch. With no dependencies and those settings, npm and pnpm skip the root's install hooks, while Yarn runs its root preinstall/install/postinstall hooks. Explicit `run probe` then runs the root script in all three tools. npm suppresses its preprobe/postprobe wrappers, pnpm runs both wrappers under this profile, and Yarn runs only the named script.

A hook denial is not a package-install denial. All successful dependency installs leave the selected module and lock present, including denied hooks. pnpm's unreviewed-build failure also leaves both present. In the injected hook-failure cases, npm leaves neither selected module nor lock, pnpm leaves the selected module without the lock, and Yarn leaves both. All retain the three hook-written markers outside the project directory but inside the private fixture. These are selected observations, not complete rollback, cache, usability, or safety claims.

The work tree was moved into the ignored retained capture after the snapshots. Absolute links in it are not promised to work at that new location. The captured module queries ran before that move.

## Source and policy boundaries

The [source ledger](sources.json) pins inspected selections, upstream URLs, whole-file hashes, and cache locations. Seven npm files match the installed distribution byte for byte. pnpm's source pin and Yarn's source/bundle pins remain attribution, not proofs of reproducible binaries.

npm's policy resolver chooses CLI/environment, root manifest, or configuration in precedence order rather than merging every layer. Its source matcher distinguishes a resolved local archive from a registry package's name; this fixture grants the exact local source. The rebuild gate skips denied lifecycle hooks while retaining binary-link handling, and the dangerous override bypasses denial. `ignore-scripts` still suppresses install hooks. The explicit-run command gates pre/post wrappers separately from its named script. The inspected strict-review preflight precedes reification, while non-strict review reporting occurs after reification; **strict npm mode was not executed here**.

pnpm's `AllowBuildPolicy` resolves approval against the dependency source. Its explicit false entry wins over broad allowance. The fixture uses a source-qualified local archive key in `pnpm-workspace.yaml`, not permission based solely on the archive's self-reported name. The selected build-policy tests explain scheduling and ignored-build defaults; they were inspected, not executed. Explicit-run stage construction uses `enable_pre_post_scripts`, a separate setting from installation's ignore flag.

Yarn's dependency build-request function applies `built: false` before the global default, then permits an explicit `built: true` even with `enableScripts: false`. Compatible hard packages are a premise here. Workspace lifecycle directives are collected separately in the project pass, explaining the root-hook observation. Soft links, incompatible architectures, implicit node-gyp builds, PnP, and other profiles remain unqualified.

## Models, laws, and replay

[Lean](Policy.lean) defines effective application profiles, matched review decisions, operation scopes, controlled marker sequences, and the injected failure. Eleven laws preserve precedence, explicit-run scope, review distinctions, and already-observed markers. [Bend](Policy.bend) checks six permission/precedence laws. Permission is not authorization for arbitrary effects and supplies no process sandbox.

The [replay](conformance.py) compares 24 native scoped outcomes with Lean and 21 install decisions with Bend. It independently checks captured configurations, source hashes, streams, manifest/lock snapshots, module queries, and unchanged replay inputs. Unknown schema, profile, and scope are refused. Filesystem/lock cleanup and exact numeric statuses remain native observations, outside the permission model.

After compiling the models with the pinned toolchain, replay without launching a package manager:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/js-scripts/conformance.py applications/evidence/js-scripts-20261124T054018650056Z
```

`python3 applications/js-scripts/probe.py` collects a fresh native fixture on this Mac. It belongs outside ordinary CI. Replaying retained evidence is not a new native installation.

## Design and UX decisions

Preserve each application's distinct policy. Deny, unreviewed, permitted, executed, and completed successfully should remain separate in internal results and reports. A nonzero command must not imply that no files or hook effects exist. A skipped hook must not be reported as a missing package without checking installation state.

npm's unreviewed warning appears after hooks have already run under the measured non-strict profile. A candidate diagnostic should say that execution happened and review remains outstanding, while distinguishing strict preflight refusal. This is a reporting opportunity, not a claim that the default violates its policy. pnpm can report ignored builds alongside the materialized selection and the command's failed result. Yarn can make the dependency/workspace scope of `enableScripts` and the effect of explicit `built` entries discoverable. Keep-current behavior is reasonable where existing help and diagnostics already communicate these distinctions.

These candidates can be additive reports from existing policy/execution facts. They need no lock-format rewrite, shared universal script policy, new scheduler, or weakened permission gate. Verify them against registry/local identities, policy layers, strict review, explicit approval/rebuild, workspace selection, failures before and during hooks, and existing machine-output callers before adoption.

For empack, this evidence supports keeping a requested operation, admitted capability, captured inputs, runtime outcome, and observed effects distinct. It does not select arbitrary third-party generators for portable authoring or define their trust model. Current recipe-owned integration remains separate from general executable author content. No production implementation changed.

A separate [workspace band](WORKSPACES.md) compares root/member scope, exact versus dependency selection, serial scheduling, missing scripts, and partial effects. It does not expand this hook-policy band into parallel execution or general task-graph qualification.
