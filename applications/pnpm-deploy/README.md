# Workspace deployment, runtime closure, and protected targets

This band studies pnpm 12.21.0 on macOS arm64, with source pinned to `b8d388835f9a40ee1ac53fbc2d4b58c3ebfa5600`. It establishes a bounded target-safety defect as well as successful local deployment behavior. It changes no package-manager implementation, user project, or installed tool.

## Native scope

The [collector](probe.py) creates one private workspace with an application, a local library and its transitive dependency, optional and development packages, and a deterministic external local tarball. Scripts are disabled, installation/deployment use offline mode, and registry configuration points to an unreachable loopback endpoint. Explicit config/cache/state paths replace inherited tool configuration; `HOME` is not reassigned. There is no registry service, account, remote publication, native addon, or lifecycle script in this fixture.

The [receipt](../evidence/pnpm-deploy-20261125T152000035565Z/receipt.json) records twelve deployment commands and ten fresh Node runtime reads. Five deployments succeed, and seven refuse. Source snapshots, target snapshots, command outcomes, and runtime results are separate observations. All recorded process groups were absent at return. [Supplemental metadata](../evidence/pnpm-deploy-20261125T152000035565Z/retained-metadata.json) was retained only after its bytes matched the earlier source/target hashes; it does not rerun or replace the original observations.

## Selection is not runtime reachability

The deploy filter must select one workspace project. Selecting none or several refuses before target creation. This is a project-selection rule, not a requirement to select every transitive dependency through the filter. The selected application supplies the root of the deployed runtime graph. [Pinned source and documentation](../sources/pnpm-deploy-selections.json) identify selection, group filtering, dedicated-lock conversion, file copying, and installation separately.

| Deployment | Observed installed package inventory |
| --- | --- |
| `--prod` | Application, library, transitive leaf, external tarball, and optional package |
| `--prod --no-optional` | Application, library, transitive leaf, and external tarball |
| Default groups | The production inventory plus the development package |

The library loads its leaf in every successful runtime read. The application cannot resolve that leaf as a direct root dependency. Direct module visibility is therefore narrower than installed reachability. This extends the [declaration/removal](../js-peers/REMOVAL.md) and [workspace-command](../js-scripts/WORKSPACES.md) distinctions into an actual deployed tree; it does not reuse a script-selection test as installation evidence.

The selected package's `files` list excludes its author-only file, while its required `package.json` and program remain. The successful outputs are copied with relative symlinks preserved. The source workspace, archives, and cache are then temporarily renamed, and a fresh Node process reads each copied application before those roots are restored. All five copied applications run. Recorded symlinks resolve within their copied inventories, and observed direct module realpaths are within the copied output.

Those deployed manifests still contain source-addressed `file:` specifiers. Their presence does not make the already materialized runtime depend on those paths for execution. It also does not make the copied output a portable author project that can necessarily reinstall or resolve its dependencies without the original sources. Runtime backing, declarative acquisition sources, lock data, and future repair authority remain distinct.

## Refusal and partial effects

The ordinary controls establish these boundaries:

- Workspace-root targets, forced targets outside the workspace, and a workspace-child symlink component are refused with their reason.
- A nonempty target without force retains its marker.
- A new target outside the workspace succeeds without force. The narrower forced-replacement policy is a separate condition.
- An admitted forced child target removes its old marker before copying the selected package and installing dependencies.
- With the external archive hidden and a fresh empty store, the forced deployment fails during dependency installation. Its old marker is gone, and copied application files plus generated metadata remain. The author workspace is unchanged.

The final failure is a partial deployment, not rollback. The source prepares the target and copies files before the install completes. A nonzero status therefore does not imply an untouched target. Source hooks are loaded before that preparation; their failure ordering was inspected but not exercised here. Other copy failures and interrupted writes remain open.

## Confirmed case-alias source loss

The separate [alias collector](case_alias_probe.py) creates a fresh dependency-free workspace and retains every author-file preimage before testing force. The [receipt](../evidence/pnpm-deploy-alias-20261125T152635252659Z/receipt.json) records that `packages/app` and `packages/APP` refer to the same device/inode on this host.

The exact source spelling is correctly refused, leaving the complete snapshot unchanged. The case-only spelling is admitted and exits zero. Its warning announces force deletion, and its final output reports success. Afterward, the original `index.cjs` and author-only `private.txt` are absent; generated deployment metadata occupies that source directory. Their original bytes are independently verified in the retained [preimages](../evidence/pnpm-deploy-alias-20261125T152635252659Z/preimage/packages/app/). No personal checkout was used, and the original larger deployment fixture remains unchanged.

The pinned source supports the mechanism: Unix path-component comparison retains spelling, while the target guard uses those comparisons to protect the selected source and its ancestors. The workspace-child check rejects symlinks but does not reject this case alias. Force then clears the admitted target before the source file-copy operation. Subsequent metadata generation and installation can finish without the missing program producing a nonzero exit. This is a reproduced defect in the selected binary/host profile, not merely a simulated path warning. The source/binary identities remain separate; no reproducible-build proof or claim about newer pnpm releases is made.

## Models and verification

[Lean](Deploy.lean) and [Bend](Deploy.bend) model root dependency groups, bounded runtime closure, direct exposure, lexical target admission, destructive preparation, and command outcomes independently. Fourteen measured deployment outcome records match both models. The ordinary graph has six runtime nodes, root-only optional/development choices, and one transitive runtime edge. It has no peers or transitive optional/development edges. These premises constrain the graph laws.

The [decoder](DeployCase.lean) refuses unsupported schemas, unknown required install availability, invalid graph references, unsupported group tags, and duplicate root targets. Early refusals retain install availability as unknown. The stage tags are study classifications, not pnpm exit codes. The [replay](conformance.py) reads original streams, snapshots, retained manifest text, tool/source identities, runtime values, and symlink targets. It executes only formal adapters, never pnpm or Node.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/pnpm-deploy/conformance.py
```

Compile the formal modules first. Changed raw effect observations and invalid model inputs must be rejected for their stated reasons. The models keep the observed current behavior, including the success-with-source-loss counterexample. A proposed physical-conflict admission guard has separate laws; it has no native patch or qualification claim.

## Design and interface direction

Protect actual filesystem resources before destructive target preparation. An existing target must not alias a protected source, workspace root, current directory, or relevant ancestor merely because its spelling differs. Preserve that distinction through the operation's actual write/delete boundary. Globally lowercasing Unix paths is insufficient: case-sensitive directories may legitimately contain distinct names. Canonical spelling alone also does not establish race-safe mutation authority. The existing host identity/rooted-operation boundaries are the appropriate place for filesystem evidence; no new generic transaction framework is selected.

The smallest useful direction is an additional protected-resource admission check before the existing force cleanup, with unknown identity treated as unresolved rather than distinct. Known selection/path refusals remain early; additional physical evidence is needed only for an otherwise admitted mutation. The check must be qualified against the exact binary, case-sensitive and insensitive filesystems, ancestor aliases, symlinks, missing-target parents, and the actual deletion operation. This band supplies the counterexample and a proposed rule, not that implementation.

After an ordinary installation failure, diagnostics should name the affected target and distinguish retained copied files from a completed runnable deployment. Before force, the existing deletion warning is useful but cannot substitute for target safety. Command success, dependency-install success, payload presence, source preservation, and runtime acceptance are separate facts. The alias control makes an implementation fix necessary before presenting that path as safe; wording alone cannot repair it.

For empack, retain the same domain separation without importing pnpm's defect or policies. A selected author root, its source bytes, projected consumer files, retained backing, and native publication authority are different values. A successful writer or metadata receipt cannot certify a usable export or authorize overwriting a source alias. Existing root/identity and verified-output obligations should survive extraction; this comparator does not establish a bug in empack.

## Remaining qualification

Pack/tarball publication, `fetch`, legacy deploy, injected/ambiguous peers, shared global stores, custom virtual-store paths, hooks, optional install failures, platforms, native modules, lifecycle scripts, source drift, competing writers, crashes, and recovery are unqualified. macOS case behavior does not establish Windows, Linux, other APFS modes, network filesystems, or all normalization aliases. Any pnpm/source or Node upgrade must recheck selection, file inventory, root versus transitive exposure, copied-runtime independence, partial effects, and protected-target controls before advancing this band’s pins.
