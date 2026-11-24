# Effective manifests, selected roots, and checked dependencies

This band executes Cargo 1.92.0 at source revision `344c4567c634a25837e3c3476aac08af84cf9203` on macOS arm64. Four generated offline workspaces distinguish root versus virtual manifests and absent versus explicit default members. Thirty-six commands cover eight metadata contexts, 24 check requests, and four private target cleanups. No registry or existing project participates. The fixtures have no build scripts, and their programs are not launched.

## Domain and current rules

Workspace membership, the effective manifest, default request roots, explicit selected roots, and dependency check closure are separate values. A root directory alone does not identify a command's scope. The current directory selects the manifest unless an explicit `--manifest-path` supplies it. A selected member's dependencies can participate even when they were not selected as roots.

The [workspace implementation](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/cargo/core/workspace.rs) applies explicit `default-members` when the effective manifest is the workspace root. Otherwise, a member invocation defaults to that member. At the root, an absent default list selects the root package for a non-virtual manifest or all members for a virtual manifest. The [check reference](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/doc/src/commands/cargo-check.md) describes the same manifest-based selection rule.

The package-selection code keeps default, all, explicit, and opt-out requests distinct. CLI `--exclude` requires `--workspace` and filters selected workspace roots. It is not the manifest's `[workspace].exclude` membership rule and does not ban a selected package from depending on an excluded root. General package specs, globs, automatic path-member discovery, and manifest membership exclusions remain outside this fixture.

The metadata implementation exports `workspace_default_members` from that effective workspace object. It is not guaranteed to be invariant for every invocation that discovers the same root. With `--no-deps`, metadata exports members without resolving the dependency graph. These scope facts matter to IDEs, automation, and callers caching metadata.

## Native observations

Each project has A depending on library B. Non-virtual profiles also have an independent root binary. The actual [configuration](../evidence/cargo-workspaces-20261124T080614049672Z/configuration.json) and [trace](../evidence/cargo-workspaces-20261124T080614049672Z/trace.json) retain source text, request argv, current directory, source/lock/target observations, compiler JSON, statuses, and tool identities.

| Root profile | Root-context metadata defaults | Ordinary root check reports |
| --- | --- | --- |
| Root package, no explicit defaults | Root | Root |
| Virtual root, no explicit defaults | A and B | A and B |
| Virtual root, defaults A | A | A and B |
| Root package, defaults A | A | A and B |

In every profile, an ordinary check or metadata invocation from B defaults to B. In particular, the root-A profile's metadata reports A from the root and B from B, while workspace membership and source files stay the same. Supplying `--manifest-path <root>/Cargo.toml` from B restores the root-context default selection.

`check --workspace --exclude fixture-b` still reports B, because A needs it. The root-default profile reports B with `fresh=false` in this control, so the observation is not limited to a previously cached report. An explicit `check -p fixture-a` also reports both A and B. Package IDs are mapped through actual metadata as opaque foreign keys; the adapter does not infer names or paths by parsing their spelling.

Every `--exclude fixture-b` request without `--workspace` returns 101 with an actionable diagnostic and no compiler artifacts. The observed source, lock, and target-presence state remains unchanged for those refusals. No broader assertion that every Cargo error has no effects follows from this control.

Cold `metadata --no-deps` creates neither a lockfile nor a target directory in these profiles and reports `resolve=null`. The subsequent check creates private lock/target state. This differs from the earlier full-resolution metadata fixture, which created a lock. Preserve the actual request and graph scope before describing metadata as read-only or resolved.

All reported check artifacts have the expected binary or library target kind and no executable path. `cargo check` supplies compiler metadata/check evidence; it omits final code generation and can miss errors only found there. These records do not establish artifact bytes, linked binaries, runtime behavior, or gameplay. Artifact presentation order and freshness implementation are not qualified.

## Models and verification

[Lean](Workspaces.lean) and [Bend](Workspaces.bend) separate effective context/defaults, selected roots, and the finite A-to-B checked closure. Both match all eight metadata-context comparisons and 24 check-membership projections. Lean also compares those 24 statuses, including four flag refusals. Nine Lean laws and four Bend laws retain member-context precedence, root/virtual defaults, and exclusion versus dependency participation. The package/feature/unit distinctions from the earlier [build band](README.md) remain intact; these models do not implement Cargo's full unit generator.

The [adapter](workspaces_conformance.py) derives root/default facts from captured TOML and request context from actual argv/CWD. Metadata member/default fields and compiler-reported packages are direct observations. Selected roots for check requests are separately attributed source/model interpretations. Two invalid research inputs exercise schema and request-code refusal. Replay launches only Lean and Bend:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/cargo/workspaces_conformance.py applications/evidence/cargo-workspaces-20261124T080614049672Z
```

Compile the models with the repository's pinned formal check first. Selected upstream files must be available at the recorded hashes in the ignored source cache; replay does not fetch them or run Cargo. The [source ledger](../sources/cargo-workspaces-selections.json) distinguishes inspected implementation ranges from the unqualified remainder.

The collector used private Cargo/home/temporary directories and checked CWD ancestors for Cargo configuration. Incremental compilation was disabled, and each profile cleaned its own target before retirement. Only afterward was the remaining roughly 328 KiB source/lock fixture moved into ignored capture storage. Its receipt retains original paths and actual environments. No user build, recovery evidence, or shared target was cleaned. These normal completed commands do not qualify concurrent or interrupted builds.

## Preserve semantics and expose scope

No new Cargo correctness defect is established. Preserve manifest-relative defaults, explicit selected roots, dependency inclusion, and the difference between metadata, checks, builds, and runtime. Do not redefine `--exclude` as a dependency ban or flatten metadata into a context-free project summary.

A focused integration/API improvement would keep a request basis with the metadata: effective manifest, discovered workspace, selection mode, resolved roots, and build/check context. Reuse existing options and opaque IDs. An IDE can show that a package participates as a dependency even when excluded as a root. A cache keyed only by workspace root and unchanged manifest text can reuse the wrong default-selection interpretation after a context change; this is a consumer-design risk, not a reproduced bug in Cargo's cache.

The keep-current alternative is sound when callers already carry the manifest and selection flags explicitly and use metadata only for its documented scope. Improving those callers and help is preferable to another resolver, metadata service, or command. Any added public inspection result should be additive and versioned, preserve existing field meanings, and keep unknown or uncomputed build-unit facts explicit. No manifest/lock migration is selected.

Before adoption, test nested/default-member globs, root-only and empty defaults, members outside the root, manifest exclusions, dependencies outside membership, missing and ambiguous package specs, multiple package selectors, features/resolvers, build/test/doc targets, alternate host/target profiles, changed manifests during inspection, concurrency, interruption, and real IDE caching. Compare requested roots, compiler units, artifact evidence, and scoped effects independently.

For empack, keep explicit operation/profile/target basis with interpretation and prepared work. The same authored project can produce different selected outputs without changing its raw content. Excluding one candidate placement or operation root need not erase a retained asset or a prerequisite used elsewhere. Those are domain-specific relations to define, not an invitation to copy Cargo's flags or introduce ambient CWD authority into portable authoring.
