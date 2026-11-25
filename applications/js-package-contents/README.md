# Package file selection and link representation

This band compares local `pack` artifacts from npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 with Node 26.13.1 on macOS arm64. It separates authored selection rules, required entry points, source bytes, archive entries, and link relations. A package manifest's `private: true` does not prohibit the tested local pack operation; publication is a separate boundary.

## Domain and source basis

The package directory supplies regular files and authored links. `files` and ignore rules select paths. Main/bin declarations and standard metadata add required paths. The packer then writes a publish manifest and typed archive entries. A selected path, a regular payload, and a symlink target name are different values; an archive inventory must preserve their types.

The [source ledger](../sources/js-package-contents-selections.json) pins npm CLI `d12b9434dd010b5fb7044c3cc149cdda317813f8`, pnpm `b8d388835f9a40ee1ac53fbc2d4b58c3ebfa5600`, Yarn `62edcb0e2f62c93b7b2ec2ef6a79edeaf2e06b3c`, and npm-packlist 10.0.4 at its resolved Git commit. That npm-packlist body matches the installed dependency exactly. Fifteen inspected files include one separately attributed [post-capture link-admission context](../sources/js-package-contents-link-context.json); the original fourteen-file native source ledger stays unchanged.

npm's pack command delegates archive construction, with npm-packlist providing selection and excluding nonregular/nondirectory entries. pnpm separates `SelectedPackageFiles`, required entries, publish-manifest preparation, and tar writing. Its link admission accepts contained links while retaining unknown target kind for a missing target. Yarn's `IgnoreList` and `genPackList` select paths, and `genPackStream` writes regular data or a symlink entry based on `lstat`. These are inspected source contracts, not reproducible-build proofs for the entire native pnpm or bundled Yarn program.

## Native fixture

The [collector](probe.py) creates six separate, dependency-free packages per manager. Each has a main file, bin file, two `dist` files, an ordinary root note, README, LICENSE, and a private package manifest. No package contains hooks or dependency declarations. Commands use private HOME/configuration/cache/state directories, the pinned tools, disabled acquisition settings, and dead loopback proxy/registry endpoints. No publish or install command is invoked. This is not host-I/O tracing or an OS sandbox.

Each command writes its archive outside the package directory. The [receipt](../evidence/js-package-contents-20261125T181340790945Z/receipt.json) records twenty-one completed commands: three help calls and eighteen packs. Every recorded group was absent at completion. Source file bytes, modes, link text, and the owned outside-project target remained unchanged. Private allocation was 3,428 KiB. Native collection inspects archives in memory. The publication audit separately copies verified regular payloads into owned audit files for scanning; it creates no archive links and installs no package.

| Fixture | Result common to all three selected builds |
| --- | --- |
| No `files` or ignore file | Ordinary note and both `dist` files included |
| `.gitignore` excludes the note; no `.npmignore` | Note excluded |
| Empty `.npmignore` beside that `.gitignore` | Note included; the npm ignore file replaces fallback selection |
| `files: [dist]` with a root ignore excluding `dist`, main/bin, README, and LICENSE | `dist` files included; required main/bin/metadata also retained |
| Same explicit `files` plus `dist/.npmignore` excluding its private marker | Nested marker excluded; selected public file and required entries retained |

These observations concern the literal patterns in this fixture, not every ignore syntax. In particular, `files` is not an unconditional rule that every other path disappears: declared entry points and standard metadata still matter. Root and nested ignore scopes also have different roles.

The sixth fixture adds three links under the selected `dist` directory:

| Authored link | npm | pnpm | Yarn |
| --- | --- | --- | --- |
| `internal-link.txt -> public.js` | Omitted | Symlink retained | Symlink retained |
| `missing-link.txt -> missing-target.txt` | Omitted | Symlink retained | Symlink retained |
| `external-link.txt -> ../../outside.txt` | Omitted | Omitted | Symlink retained |

The outside target is an owned synthetic file. The Yarn archive carries its link name, not that file's bytes. The pnpm source's missing-target branch keeps an admitted internal relation with unknown target kind; admission does not assert that the target exists. Link chains, platform aliases, and races need separate qualification. No consumer-resolution, extraction-safety, data-exfiltration, or security-defect conclusion follows from this table alone.

Across eighteen archives, all 134 selected entries are accounted for, including five symlinks. Every packaged manifest is semantically equal to its authored fixture manifest. All other regular-file bytes and retained link texts match their authored inputs. Different ordering and manifest serialization are not presented as byte-identical archives.

## Models and independent comparison

The [Lean model](Contents.lean), [decoder](ContentsCase.lean), and [Bend model](Contents.bend) separate type admission, global exclusions, required files, explicit selection, root ignore fallback, and nested exclusions. Twelve Lean laws and nine Bend laws preserve those distinctions. Literal pattern matches and the simple fixture link classes are explicit premises, not replacements for the programs' glob parsers, complete source walkers, or physical link resolution.

The [observation adapter](observations.py) derives those premises from the retained authored manifests, ignore files, and source images. Expected inclusion is independently read from actual tar members. It also compares manifest semantics, regular bytes, link text, and archive hashes. The [pure replay](conformance.py) checks command streams, available source/tool identities, and source preservation before comparing all 177 file-membership decisions through both models. Changed interpretations and invalid decoder packets must be rejected. It does not rerun a package manager.

The original setup's broad read-scope wording is preserved with an explicit [qualification](../evidence/js-package-contents-20261125T181340790945Z/scope-qualification.json): selected fixture inputs and prohibited actions do not establish a general host-read fence. The current collector only clarifies that description; no native case was recollected to change an outcome.

## Per-application decisions

**npm:** preserve its regular-file-oriented packlist and required-file rules. The current file listing is useful artifact evidence. A detailed explanation could reuse `PackWalker` rules and required-file facts to distinguish files retained by entry-point requirements from ordinary `files` selection. Keep existing JSON keys and ordinary listing behavior; any additive reason field needs an explicit compatibility decision. Do not create a second matcher solely for preview explanations. Keeping the present compact output is reasonable if its documentation makes required files and root/nested scopes clear.

**pnpm:** preserve `SelectedPackageFiles` and `AdmittedSymlink` rather than collapsing links into ordinary files or assuming an admitted target exists. `PackResult.contents` can support an optional typed explanation using the already available relation/target-kind facts. A missing target kind remains unknown. Review single/recursive callers and JSON consumers before adding fields. Keep-current compact output remains defensible, but callers must inspect archive types before making a regular-payload claim.

**Yarn:** preserve its explicit regular-versus-symlink writer distinction and current source ownership. A detailed pack preview could expose link type and link name from the existing walk/stream information. That would let an author notice an external or dangling relation without silently dereferencing it or promising that the preview is a final immutable capture. Changing link policy would alter legitimate package contents and needs a separate compatibility decision and consumer tests. This band selects no such policy change.

For empack and other exporters, describe source selection, materialized payload, link relation, and resulting consumer object separately. Do not infer another tool's source or preservation policy from matching path lists or digests. No production implementation, publishing service, or shared host abstraction is added here.

## Remaining qualification

General glob/negation/case rules, workspace ancestry, bundled dependencies, publish-directory overrides, generated manifests, pnpm variants, hooks and hook failure, concurrent source changes, link chains, filesystem aliases, invalid source types, failed output publication, consumer install/extraction, other hosts, and current unreleased upstream behavior remain open. Parent feature operations are not promoted by this partial component. The earlier [publication study](../js-peers/PUBLICATION.md) supplies different upload/acknowledgement evidence; a local archive cannot establish registry acceptance.
