# Cargo package selection and verification

A local source archive, a successful build check, and a published registry version are different results. Cargo 1.92.0 deliberately supports creating an archive without compiling it. Its default package flow also creates the archive before verifying that it builds. An existing `.crate` file alone establishes neither successful verification nor publication.

## Observed fixture

The [receipt](../evidence/cargo-package-20261124T060420484446Z/receipt.json), [trace](../evidence/cargo-package-20261124T060420484446Z/trace.json), and [input cases](../evidence/cargo-package-20261124T060420484446Z/cases.json) retain 12 commands on five generated, dependency-free Git crates. The owner-run [collector](package_probe.py) uses the pinned Cargo executable on macOS arm64, private home/config/target directories, and offline mode. One tiny crate builds successfully; one contains a deliberate Rust syntax error. Every manifest sets `publish = false`. No registry, third-party package, user project, credential, or publication was involved.

| Request | Observed result |
| --- | --- |
| `package --list` on four fresh fixture roots | Exit 0, proposed file names, no archive created. |
| `package --no-verify` | Exit 0 and an archive, including for deliberately invalid Rust. |
| Default `package` on the valid crate | Archive created, unpacked build checked, exit 0. |
| Default `package` on the invalid crate, with no prior archive | Archive created, compile fails, exit 101; the archive remains. |
| `package --no-verify --exclude-lockfile` | Archive omits `Cargo.lock`; other selected entries remain. |

Named author inputs retain identical hashes before and after every command. That is not a claim that the target, cache, logs, or lock state are unchanged. The retained private work is about 908 KiB; its final move happened after native snapshots. Each created archive is retained independently with its checksum, entries, and entry bytes.

The selection cases distinguish these policies:

- With neither field, the private Git ignore rules exclude `ignored.txt`; tracked ordinary data enters the archive.
- An explicit `exclude` removes the selected data file.
- An explicit `include` selects its listed source/data and even the Git-ignored file. Other ordinary files are omitted.
- With both fields, include controls selection: the included data file remains even though exclude also names it. Cargo warns that both fields are present.
- The package's manifest, original-manifest copy, declared root README and license, generated lock, and available VCS information have separate archive roles. Required root metadata can enter despite not matching the ordinary include patterns.
- The nested package and root `target` content stay outside these archives.

These are selected patterns and root metadata paths, not a complete glob, Git discovery, or filesystem traversal qualification. The generated `Cargo.toml` differs from the author file, supplies normalized target fields, and retains the tested package fields. `Cargo.toml.orig` preserves the exact authored manifest. The study does not exercise path-dependency rewriting, workspace inheritance, symlinks, or arbitrary external metadata paths.

## Source and models

The [source selections](../sources/cargo-package-selections.json) pin Cargo revision `344c4567c634a25837e3c3476aac08af84cf9203`. The command and manifest documentation explain archive generation, inclusion rules, and optional verification. The selected path source implements include-versus-Git/exclude selection. The package module adds generated manifest/lock/VCS entries and declared metadata files, writes the archive, and then invokes verification. The verification module unpacks into its build area, compiles, and compares source fingerprints around the build.

A comment in `create_package` suggests that the temporary archive moves only after testing, but the inspected control flow and fresh invalid-source case establish that build verification happens later. Treat that comment as stale context rather than proof of a publication guarantee. A focused source-comment correction would be reasonable; this study changes no Cargo source.

[Lean](Package.lean) models matched source facts, the exact controlled fixture inventories, and three requests: list, unchecked archive, and verified archive. Nine laws cover prohibited inputs, required root metadata, include precedence, Git-ignored selection, listing, and the distinction between archive presence and success. [Bend](Package.bend) checks four laws and executes the source-membership/outcome projection. Neither implements Cargo's glob engine, archive writer, Git traversal, or compiler.

The [retained replay](package_conformance.py) compares 12 complete controlled inventories/outcomes in Lean, 132 source-membership decisions and 12 outcomes in Bend. It independently reads each actual tarball, checks every captured entry and checksum, compares original and normalized manifests, and verifies stream/source/input identities. Unknown schema, profile, and a request to publish are refused. A replay runs neither Cargo nor a compiler.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/cargo/package_conformance.py applications/evidence/cargo-package-20261124T060420484446Z
```

Compile the formal modules with the pinned toolchain first. `python3 applications/cargo/package_probe.py` collects a fresh owner-run fixture outside ordinary CI. Its only compilation is the small generated valid/invalid source check.

## Design and UX implications

Preserve source selection, transformed distribution manifest, local archive identity, build-check result, and remote publication as separate facts. `publish = false` does not prevent local packaging. VCS metadata is a best-effort description; the pinned docs explicitly do not guarantee that its revision describes the tarball's actual bytes.

A candidate diagnostic for failed package verification could name the retained archive and state that it was created but failed verification. The current detailed error already identifies the compile failure, so keep-current behavior remains credible for experienced callers. A wrapper should retain the actual failure and must not publish the archive merely because the expected path exists. It should also avoid suggesting that `--no-verify` repairs invalid source; that flag changes the requested check.

For machine consumers, prefer an additive result carrying the exact archive checksum, selected request, verification scope/outcome, and publication status when independently known. Before adding a new API, inspect existing Cargo JSON/unstable packaging output and downstream consumers. Do not silently change lock contents, stable list output, saved package identity, or the semantics of `--no-verify`.

For empack, this supports its existing distinction between candidate output, verification, and delivery. A generated archive or successful callback must not mint a stronger proof than the checks performed against its captured inputs. It does not require copying Cargo's flags or weakening managed-recipe checks. Complete project backup and lossy consumer export retain different meanings.

Remaining checks include package dependencies and registry identity, workspace selection, source mutations during build, failed archive finalization, stale outputs, symlinks and case collisions, reserved names, cross-platform extraction, upload uncertainty, and actual publication. This band supplies no registry acceptance or release qualification.
