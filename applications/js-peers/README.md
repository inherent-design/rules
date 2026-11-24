# JavaScript packages: content and peer contexts

This band compares npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 on macOS arm64 with Node 26.13.1. It covers a generated local-tarball workspace, the `node_modules` layout, and one frozen-install refusal. The tools' resolver and policy differences are preserved. This is not a general package-manager equivalence claim.

A separate [removal and re-adoption band](REMOVAL.md) follows direct declarations, retained transitive dependencies, and root lookup through normal edits. Its distinct fixture preserves the peer-context observations here.

## Fixture and evidence

Two workspaces consume the same plugin archive. The plugin declares `fixture-api: "*"` as a peer. The left workspace supplies API 1; the right supplies API 2. All archives contain only generated manifests and JavaScript. Scripts are disabled, stores/configuration are private, and installation uses offline flags or disabled network. These explicit settings do not describe the tools' defaults.

The [retained collector and receipt](../evidence/js-peers-20261124T010359780886Z/receipt.json) identify the exact tools, archives, platform, and source. [Trace records](../evidence/js-peers-20261124T010359780886Z/trace.json) retain commands, stream hashes, exit status, and scoped before/after state. Node independently loads each installed plugin and reports the API it actually uses. The manifest and entrypoint bytes are identical across the six measured consumer bindings.

| Tool/profile | Left direct API | Left plugin API | Right direct API | Right plugin API |
| --- | --- | --- | --- | --- |
| npm, default hoisted layout | 1 | 1 | 2 | **1** |
| pnpm, isolated layout | 1 | 1 | 2 | **2** |
| Yarn, explicitly selected node-modules linker | 1 | 1 | 2 | **2** |

npm's `ls --all --json` exits successfully and reports the installed graph without a top-level problem. Its shared hoisted plugin resolves API 1, which satisfies `*`. This observation is not classified as an npm defect or a broken peer requirement. It does show why a consumer's direct dependency and a plugin's effective dependency cannot be assumed identical from names and permitted ranges alone.

After installation, the fixture changes the left workspace's API reference from archive 1 to archive 2. All three frozen commands exit 1: npm `ci`, pnpm `install --frozen-lockfile`, and Yarn `install --immutable`. The lock bytes, edited manifest, and independently queried runtime bindings remain unchanged across these refusals. This does not establish that caches, logs, or every file in `node_modules` were untouched.

The selected [npm ci source](https://github.com/npm/cli/blob/d12b9434dd010b5fb7044c3cc149cdda317813f8/lib/commands/ci.js) validates the saved and proposed graphs before removing `node_modules`. Yarn's inspected project pass compares the generated lock with its initial snapshot after resolution and refuses the change. pnpm's inspected error definition matches the recorded outdated-lockfile cause and recovery guidance; its complete materialization ordering remains unqualified.

## Domain and source comparison

The model distinguishes the requested dependency specification, selected package contents, effective peer-provider binding, installed instance, and saved lock evidence. The same content can participate in more than one runtime context. A successful resolution or a permitted range does not supply the identity of every effective provider.

### npm

The pinned [Arborist edge source](https://github.com/npm/cli/blob/d12b9434dd010b5fb7044c3cc149cdda317813f8/workspaces/arborist/lib/edge.js) separates dependency kinds, target resolution, and validity. Its [node lookup](https://github.com/npm/cli/blob/d12b9434dd010b5fb7044c3cc149cdda317813f8/workspaces/arborist/lib/node.js) checks installed children and then parent scopes. Both inspected files match the installed npm distribution exactly. This explains the measured binding after hoisting; the full placement/hoisting algorithm remains unreviewed.

For this fixture, the plugin has one shared installed location. Both consumers can reach it, while the plugin itself uses its own surrounding API 1 provider. Preserve the distinction between a valid permitted dependency and a promise that two callers share the same concrete provider.

### pnpm

The pinned [PeerSet source](https://github.com/pnpm/pnpm/blob/b8d388835f9a40ee1ac53fbc2d4b58c3ebfa5600/pnpm/crates/resolving-deps-resolver/src/resolved_tree/peer_set.rs) distinguishes declared peers from the peers actually taken in a context. The selected upstream tarball test checks provider versions from their manifests; it was inspected, not executed here. The [official peer-resolution explanation](https://pnpm.io/how-peers-are-resolved) describes context-specific instances when peer providers differ.

In the native fixture, the plugin is reached through two peer-qualified paths in the private virtual store. Their contents match, and their effective API providers differ. The observation does not establish every possible store-linking mode, hardlink identity, or deduplication policy.

### Yarn Berry

The pinned [struct utilities](https://github.com/yarnpkg/berry/blob/62edcb0e2f62c93b7b2ec2ef6a79edeaf2e06b3c/packages/yarnpkg-core/sources/structUtils.ts) construct virtual package/descriptor references, and the selected [project pass](https://github.com/yarnpkg/berry/blob/62edcb0e2f62c93b7b2ec2ef6a79edeaf2e06b3c/packages/yarnpkg-core/sources/Project.ts) virtualizes peer-bearing packages before resolving their parent-provided peer context. The source tag and bundled executable are pinned independently; a reproducible source-to-bundle build was not performed.

The selected node-modules linker materializes two effective plugin contexts, one at the project root and one below the right workspace. This is separate from Yarn's default PnP linker, which was not exercised. The [Yarn lexicon](https://yarnpkg.com/advanced/lexicon) distinguishes descriptors, linkers, and dependency relationships; these concepts should not be collapsed into a physical folder path.

## Models and rejected assumptions

[Lean](Contexts.lean) defines instance identity, three explicitly bounded fixture profiles, and frozen admission. Eight laws cover context-sensitive identity, content preservation, each profile's selected binding, and preservation of the current draft and installed evidence during admission. [Bend](Contexts.bend) executes the same projection with three checked laws.

The [retained replay](conformance.py) checks stream identities, six native bindings against both models, and the frozen refusal observations. It rejects treating one uniform provider-selection rule as all three tools' behavior, and treating matching package contents as sufficient runtime identity. It also reconstructs the original left manifest from the one known edit and verifies its exact pre-install hash; that reconstruction is not presented as an independently captured original file.

These profiles describe the measured outcome. They do not implement or prove npm hoisting, pnpm's resolver, Yarn virtualization, or full semver satisfaction. The frozen model is an admission/refusal projection: admission does not mean installation has completed. Cache and log effects remain outside its measured state.

Compile `Contexts.lean` to `.build/applications/js-peers/Contexts.olean` with the pinned Lean, then replay without running any package manager:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/js-peers/conformance.py applications/evidence/js-peers-20261124T010359780886Z
```

`python3 applications/js_peers_probe.py` creates a fresh private native run. It belongs outside ordinary CI and currently uses this Mac's pinned tools. It does not change a user project or installed global package manager.

## Design and UX candidates

Preserve the tools' own graph and policy distinctions. For inspection interfaces, present the requested peer range, actual provider, requiring instance, and whether that instance is shared. A generic “compatible” label is weaker than this information. Review npm's existing `ls`/`explain`, pnpm's peer inspection, and Yarn's peer explanations before adding another command. An optional structured context view may be enough; do not add a warning merely because two valid contexts differ.

Frozen-install diagnostics in this fixture are useful: npm and pnpm identify the mismatched selection and a command to refresh the lock; Yarn shows the prohibited lock change. Preserve that connection between the authored edit, saved selection, and next action. A refused install must not be summarized as though the user's edited manifest was rolled back, nor should an unchanged lock imply that no cache or log write occurred.

For empack's eventual internal proposal, keep source/content identity distinct from context-specific selected files and executable artifacts. Do not import JavaScript peer semantics into the mod dependency model; compare the identity distinctions against empack's actual target, loader, recipe, and dependency rules first. The existing host contracts can carry exact basis, content, and scoped effects; no new shared primitive is required by this fixture.

The keep-current option is credible for all three tools. Any inspection improvement should be additive, retain established package IDs and lock meaning, and be tested against real hoisting, peer, and linker choices. Remaining work includes missing/optional/incompatible peers, transitive peers, overrides, alias and workspace protocols, immutable-success cases, scripts and trust gates, PnP, cache corruption, concurrent installs, other platforms, and full resolver/source comparison. No production package-manager or empack implementation has changed.
