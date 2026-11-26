# Cargo: lock admission, source access, and exact revision

`--locked` prevents a changed lock selection. It does not prohibit source acquisition or promise that a failed command leaves its cache untouched. `--offline` restricts acquisition and can still create or change a lockfile. `--frozen` combines those two policies.

This band records Cargo/Rust 1.92.0 on macOS arm64, with Cargo source `344c4567c634a25837e3c3476aac08af84cf9203`. It uses one owned path dependency, one owned `file://` Git repository with two commits at the same package version, and one compatible path patch. There is no registry, remote server, build, check, or application launch. Cargo may query compiler information; these records are not a physical compiler-process census.

## Native results

The [collector](lock_sources_probe.py) creates private project, HOME, CARGO_HOME, temporary, and target paths. It records original streams, tool hashes/versions, project files, raw hashes and file metadata, and cache inventories before and after each request. There are sixteen Cargo requests, seven Git setup commands, and two version queries. These are different scopes, not a count of all descendant processes.

| Boundary | Recorded outcome |
| --- | --- |
| Missing path lock under `--frozen` | Exit 101; lock stays absent. Cache bookkeeping can still appear. |
| Generate the path lock offline | Exit 0; local version 1.0.0 is selected and a lockfile is written. |
| Repeat with `--locked --offline` | Exit 0; exact lock record is unchanged. |
| Add an owned comment and CRLF formatting, then use `--frozen` | Exit 0; exact lock bytes, mode, and mtime remain unchanged. |
| Change the path dependency to compatible version 1.1.0 | `--locked --offline` refuses without rewriting the lock; plain `--offline` updates it. |
| Resolve cold local Git with `--offline` | Exit 101; source access is refused and no lock is created. |
| Resolve that source with `--locked` and acquisition permitted | Cargo copies the owned local Git source into its private cache, then refuses the missing lock. Twenty-four cache files are added; lock stays absent. |
| Retry offline using that admitted cache | Exit 0; commit A is selected and a lockfile is written. |
| Advance the owned Git branch to commit B, retaining package version 1.0.0 | `--frozen` retains A; offline update retains cached A; an update permitted to refresh the local Git source selects B. |
| Override that Git source with the compatible local path patch | Locked mode refuses the source switch. Offline mode updates the selection; the following frozen read accepts it. |

The five refusals and eleven successes match the intended command outcomes. The cache is a separate scope from the project. Successful locked/frozen requests, and all five refusals, preserve the exact lock record in this fixture. A refused lock publication is not rollback of prior cache work. Cache file counts are observed effects, not a prediction of general Git storage layout.

## Logical identity is not an exact content revision

The two Git reads report the **same opaque metadata package ID** at A and B. Their separate `source` fields contain different precise revisions. A path dependency and the path patch both report null `source`, while their opaque IDs and manifest paths distinguish their origins. Name and version alone cannot identify those selections either.

The selected source explains these roles. `Package::serialized` produces `id` through `PackageId::to_spec`, which uses the source URL/kind; `source` is serialized separately with its precise Git information. Ordinary internal `SourceId` comparison ignores the precise/name fields, while `full_eq` has a stronger interned-identity role. These are distinct contracts. The public metadata documentation treats source representations as opaque and describes IDs in the document/package-selector role.

Keep those existing identities and metadata fields. A consumer should retain the resolution/document basis and relevant opaque source evidence instead of treating package ID equality as immutable content equality. A path source also needs its actual file/input basis when bytes matter. Do not parse the strings observed here as a universal or permanently stable external format, rewrite Cargo's package ID schema, or infer a product defect from the equal IDs.

## Selection and publication have separate policy gates

The selected `GlobalContext` exposes separate offline and locked flags. Git acquisition first uses a locked revision already present in the database; offline deferred requests consult the existing reference. An otherwise required acquisition is refused in offline mode, including the cold local-file case. The model's cache-usability and commit-coverage inputs are premises for this controlled history, not a general validator for arbitrary Git caches.

`write_pkg_lockfile` compares the existing and proposed resolve before a required write. Under locked mode, semantic resolve equality can accept a differently formatted existing file without rewriting it. The explicit comment/CRLF case distinguishes this from a canonical-byte requirement. It does not qualify arbitrary lockfile versions, metadata, unknown fields, or corruption recovery.

The update path deliberately stops retaining selected source precision. Offline mode then resolves against its cached reference, so a successful update is not a promise that the source was refreshed or that the newest remote commit was observed. The two-commit fixture exercises that difference without contacting a remote service.

The path override is a `[patch]`, not equivalent source replacement. The latter assumes matching source content, whereas a patch deliberately offers another compatible package. Preserve the existing version/source rules and test general constraints separately. This case does not qualify mirrors, vendoring, authentication, multi-package Git update coupling, transitive patching, or registry/MSRV/semver resolution.

## Interface and design decisions

Preserve the existing flags, lockfile format, metadata fields, and status codes. The existing lock-change diagnostic already suggests removing the locked flag and trying offline mode; another command is unnecessary. The source-access error identifies the offline restriction. A caller should keep that useful cause and name whether the failure concerns acquisition or lock publication rather than summarize every 101 as “resolution failed.”

For a surrounding operation receipt, report the project/lock outcome independently from observed cache effects. Do not promise to delete a newly fetched source automatically after a lock refusal; other operations may legitimately retain it. A consumer cache key should carry its resolution basis and required source/file evidence, without inventing a new Cargo identity format. The keep-current alternative is to use existing diagnostics and complete metadata/lock snapshots correctly. No Cargo patch, upstream defect claim, public schema extension, or saved-state migration is selected.

For empack, retain the distinction between observed/acquired inputs, the author's selection intent, an exact resolved selection, and authorized publication. A successful offline operation does not establish current provider knowledge. A lock-admission check cannot substitute for source freshness or atomic project publication. These are comparative design constraints; production behavior and deferred implementation intents remain unchanged.

## Verification and preservation

The [native record](../evidence/cargo-lock-sources-20261126T012306815691Z/receipt.json), [setup](../evidence/cargo-lock-sources-20261126T012306815691Z/setup.json), frozen producer, original streams, initial/final states, Git transcript, and [collection basis](../evidence/cargo-lock-sources-20261126T012306815691Z/collection-basis.json) remain intact. Each command group was absent after its wait; a later exact private-work argument scan found no remaining process. This is scoped retirement evidence, not an arbitrary detached-descendant census. The private fixture occupied 376 KiB allocated at the end of collection and remains preserved, including its source/cache state. No target cleanup or cache retirement is claimed.

The frozen collector's `read_text` normalized CRLF in captured text while recording the original byte hash and length independently. The observer reconstructs only the known formatting control, verifies that raw digest and length, and checks raw preservation separately. It rejects other unexplained encodings instead of silently normalizing them. No native observation is rewritten.

The [observer](lock_sources_observations.py) derives requests from actual arguments and before-state manifests, lockfiles, and cache witnesses. It derives outcomes independently from after-state locks/cache and actual JSON, validates stream/file hashes and the authorized between-call edits, and checks the current private artifacts in owner mode. Thirteen [source identities and inspected ranges](../sources/cargo-lock-sources-selections.json) support the selected policies; this is not a reproducible source-to-Cargo build.

[Lean](LockSources.lean) and [Bend](LockSources.bend) each state fourteen laws. The [proof gate](../evidence/cargo-lock-sources-20261126T012306815691Z/proof-gate.json) checks two Lean modules and one Bend file. Initial Bend binder-order errors were corrected without changing the native trace. The [retained replay](lock_sources_conformance.py) compares sixteen seven-field boundary outcomes and rejects twelve unsupported DTOs, five changed premises, and six changed raw observations:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/cargo/lock_sources_conformance.py
```

`--public-only` excludes current executables, private artifacts, and source-cache readbacks explicitly. Neither mode runs Cargo, Git, a compiler, or source acquisition. No full feature or scenario status is advanced. The earlier [package study](PACKAGING.md) already covers selected normalized manifest fields; it was not rerun here. General source replacement, conditional-only graphs, registry resolution, malformed/partial caches, concurrency, other hosts, compilation, and full lock recovery remain open.
