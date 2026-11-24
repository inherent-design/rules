# Lock-only updates, frozen installs, and installed evidence

A current lock and a successful command do not necessarily establish current installed files. This band compares npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 on the pinned macOS arm64/Node 26.13.1 profile. It adds normal frozen-install and resolution-only cases to the earlier [peer-context](README.md) and [declaration-edit](REMOVAL.md) work. It also reproduces a bounded npm correctness defect across resolution-only and ordinary installation.

## Domain and selected operations

The project declares one generated local archive, first version 1 and then version 2. These exact selections have different package metadata and executable module values. The fixture distinguishes five facts:

- The manifest's requested archive.
- The root lock's selected archive/version.
- The installed package's actual files and package metadata.
- A fresh Node process's loaded module value.
- For npm, the hidden index's recorded installed version in `node_modules/.package-lock.json`.

The last value is a claim used by an optimization. It is not independently observed payload identity. No global clock or universal “current” flag can replace these relations.

| Purpose                                                 | npm                           | pnpm                                           | Yarn Berry                       |
| ------------------------------------------------------- | ----------------------------- | ---------------------------------------------- | -------------------------------- |
| Update selections and materialize                       | `install`                     | `install --no-frozen-lockfile`                 | `install`                        |
| Install while refusing a changed lock                   | `ci`                          | `install --frozen-lockfile`                    | `install --immutable`            |
| Update selections without materializing the new package | `install --package-lock-only` | `install --lockfile-only --no-frozen-lockfile` | `install --mode=update-lockfile` |

These are purpose comparisons, not interchangeable implementations. npm `ci` clears the selected project's existing modules after its lock validation; the other two tested commands are not specified as npm-style clean installs. The profile has a nonempty direct dependency, disables lifecycle scripts, and uses private configuration/cache/home with offline or disabled network. No user project is opened.

## Native flow and effects

The [primary trace](../evidence/js-lock-modes-20261124T104619177625Z/trace.json) and [receipt](../evidence/js-lock-modes-20261124T104619177625Z/receipt.json) retain 36 invocations: six installation commands and six independent fresh-process runtime reads per tool. Saved manifests and locks identify selections separately from captured module-tree hashes.

| Step                                                                                 | Native observation in all three tools                                                                          |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Frozen install without a lock                                                        | Refused with status 1; no package is loadable.                                                                 |
| Normal initial installation                                                          | Lock selects version 1; Node loads version 1.                                                                  |
| Author changes the request to version 2, then requests a frozen install              | Refused with status 1. The measured manifest, lock, and module tree are unchanged; Node still loads version 1. |
| Resolution-only update                                                               | Succeeds; lock now selects version 2; Node still loads version 1.                                              |
| Frozen installation with that current lock                                           | Succeeds without changing lock bytes; Node now loads version 2.                                                |
| Owner deletes only the disposable modules tree, then requests another frozen install | Succeeds without changing lock bytes and recreates a loadable version 2.                                       |

The resolution-only module-tree measurements differ. pnpm and Yarn leave the captured tree unchanged. npm changes only its hidden `.package-lock.json`; the package's metadata and entry point stay unchanged. Therefore even “lock-only did not change `node_modules`” is too broad for the observed npm implementation. No inference about complete cache/log effects, inode stability, global nonmutation, or crash safety follows from these images.

The exact missing-lock and stale-lock policies also require premises. The selected pnpm source explicitly allows a missing lock with no declared runtime dependencies; this fixture deliberately contains a dependency. Yarn's immutable lock checks do not mean its entire installation is read-only, and `--immutable-cache` is a separate policy that was not exercised here. Hook execution and platform/setting differences remain outside this script-disabled profile.

## Reproduced npm stale-install defect

The changed hidden index warranted a separate check. A [fresh-project follow-up](../evidence/js-lock-npm-refresh-20261124T104751912940Z/receipt.json) retains eight invocations, actual JSON images, and fresh Node reads. The sequence is:

```text
install exact local version 1
edit manifest to request exact local version 2
install --package-lock-only
install
ci
```

After the resolution-only command, both root and hidden locks record version 2 while the installed `package.json` and runtime are version 1. The ordinary `install` returns 0 and reports “up to date,” but still leaves and loads version 1. The subsequent `ci` installs version 2. This is an observed correctness defect in this exact native profile, rather than merely unfamiliar output: an accepted ordinary installation has not satisfied its exact requested selection.

A separately attributed [discriminating control](../evidence/js-lock-npm-refresh-20261124T104927472206Z/receipt.json) retains ten invocations. It first reproduces the same stale result, then the fixture owner removes only its private hidden index. The next ordinary install loads version 2. The edit receipt verifies that no other project file was changed by that intervention. Original no-intervention observations remain intact. These controls support the hidden-index mechanism; they do not qualify arbitrary cache corruption recovery or establish behavior in another npm release.

The [selected upstream source](../sources/js-lock-modes-selections.json) matches the installed `ci`, Arborist `reify`, and `load-actual` bytes. Reification skips package writes for `packageLockOnly`, then later saves the ideal tree as hidden actual metadata without the same guard. Actual-tree loading can admit that hidden metadata and return a virtual tree before reading the filesystem tree. Presence/mtime validation, options, and the rest of Arborist remain relevant; the model does not treat every arbitrary hidden file as admitted.

The proposed npm correction is to keep resolution-only publication separate from observed-install metadata. Options include preserving valid prior actual metadata, or explicitly invalidating it when the actual image has not been established. A subsequent installer must compare the actual version-1 payload with desired version 2. Updating the hidden index to desired version 2 is not such a comparison. No upstream issue, patch, release claim, or production edit was made by this study.

Keeping the current behavior is not an adequate correctness resolution for the reproduced sequence. A documented clean `npm ci` is a tested operational workaround here, but it deletes/recreates the project's modules and can execute hooks without this fixture's flags. The hidden-file intervention was a controlled private experiment, not a general cleanup recommendation. A product fix needs tests for ordinary refresh after lock-only, unchanged requests, workspaces and filtered updates, alternate installation strategies, hidden-index absence/staleness, partial failures, and interruption.

## Source, models, and counterexamples

The six [source selections](../sources/js-lock-modes-selections.json) identify exact revisions, inspected ranges, and bytes. npm's lock validation precedes module deletion in `ci`. pnpm's dispatch distinguishes frozen/fresh/lock-only work and its source warns that a root preinstall hook can precede freshness checks; disabled scripts matter to the measured refusal. Yarn compares generated lock text before fetching and linking, then explicitly skips the link step in update-lockfile mode. Full solvers, linkers, hooks, and source-to-binary reproduction for pnpm/Yarn are not qualified by those excerpts.

[Lean](LockModes.lean) proves 13 laws, and [Bend](LockModes.bend) checks five. The models keep requested, locked, payload, and npm hidden-index states separate. They project the selected fixture's admitted operations, including the current npm counterexample. `invalidateHidden` represents the separately measured control; it is not silently substituted for current behavior. Neither model proves general hidden-index admission, arbitrary resolver equivalence, filesystem mutation safety, or repair.

The pure [replay](lock_modes_conformance.py) compares 27 installation outcomes from 54 native invocations. Eighteen shared-profile cases compare status, selected version, and fresh runtime value. Their npm index input is a source-interpreted label; it is not reported as decoded native data. Nine follow-up cases additionally decode saved root/hidden locks and installed package metadata, and compare the runtime independently. Both executable models agree. Six invalid research inputs are refused, including absent requested dependencies, unknown revisions/profiles/modes, and assigning npm's index to another tool. That refusal describes the research decoder's scope, not a product refusal.

The useful counterexamples are that a current lock can coexist with an old payload, a resolution-only operation can change install metadata, a successful ordinary npm installation can retain an old exact version, and a hidden index can disagree with both installed metadata and runtime. Fixing a misleading string alone would not address the reproduced npm behavior.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/js-peers/lock_modes_conformance.py \
  applications/evidence/js-lock-modes-20261124T104619177625Z \
  applications/evidence/js-lock-npm-refresh-20261124T104751912940Z \
  applications/evidence/js-lock-npm-refresh-20261124T104927472206Z
```

Compile `LockModes.lean` into `.build/formal/applications/js-peers/LockModes.olean` first. `scripts/check-rules.py` checks tracked model sources. Native collection is separate owner-run execution of `applications/js-lock-modes-probe.py` and `applications/js-lock-modes-npm-followup.py [--remove-hidden-control]`; neither belongs in ordinary CI. The follow-up deliberately reads the primary capture's preserved archive bytes and creates a new disposable project.

## Per-application UX and compatibility decisions

**npm:** repair the metadata/materialization invariant before improving “up to date.” A lock-only completion could say “Updated the lockfile; installed packages were not updated.” The defect is about subsequent installation, so a truthful lock-only message does not discharge that correction. Preserve manifest/root-lock formats and established flags; a hidden-index invalidation or observation fix should not introduce a second resolver. Compare root/hidden/actual images and fresh loads, not only expected lock text.

**pnpm:** preserve its explicit stale importer/specifier diagnostic and its direct two-command guidance. The native message names the old/new requested file and recommends lock-only followed by frozen installation. Its “Lockfile passes supply-chain policies” result describes that selected evidence; it is not a statement that installed files changed. An optional completion summary can identify “lock updated; installation unchanged” while leaving the current lock/store formats and policy semantics intact. Keep-current is reasonable when the existing command/flag distinction is understood. Test hooks, workspace importers, excluded groups, dedupe, and local-content changes before extending the model.

**Yarn:** preserve the distinct resolution, fetch, and link phases and the explicit “Skipped due to mode=update-lockfile” message. A final summary could connect those phases to the remaining install action without treating its warning as failure or describing the project as materialized. Keep immutable and immutable-cache separate. Keep-current is also reasonable; the existing stage output already exposes the key fact. PnP, plugins/hooks, changed cache admission, patches, persistent install state, and interruption require their own comparisons.

For empack's proposed interfaces, reuse this distinction rather than adopting a package-manager command wholesale. Author intent, selected lock, retained content, generated artifact, and observed installation are separate owners and receipts. A current lock or an optimistic local index cannot mint installation evidence or native execution authority. This is a design constraint for future models; no new empack defect or production change is inferred from the npm sequence.

The band leaves registry/network behavior, arbitrary semver/peer/workspace graphs, downloads and cache integrity, lifecycle failures, concurrent writers, interruption/recovery, and other platforms pending. Retained private work is about 3 MiB per capture; archives, tool stores, and private logs remain ignored. Published evidence contains generated fixture metadata and streams, not personal package projects.
