# Configuration: stored assignments, effective values, and write destinations

This band compares npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 on macOS arm64 with Node 26.13.1. It uses one nonempty public registry URL per source layer, not real registry credentials. No install, resolution, package publication, or request to a service is exercised.

## Native evidence and scope

The [collector](probe.py) creates private home, configuration, state, cache, temporary, and project directories. npm's user/global paths are explicit. Yarn's first profile uses a fixture rc filename to avoid unrelated ancestors; the standard-filename follow-up checks that its actual ancestors contain no such rc. The tool bytes are pinned before execution. This is not an OS-wide filesystem or network audit.

Three receipts retain distinct profiles, not an undifferentiated repeat count:

- [42 commands](../evidence/js-config-20261124T142130206303Z/receipt.json): all three tools, project/environment/command values, default and explicit writes, inspection, and removal.
- [13 commands](../evidence/js-config-20261124T142228313404Z/receipt.json): Yarn with the standard rc filename as a discriminating control.
- [Nine commands](../evidence/js-config-20261124T142301476569Z/receipt.json): npm and pnpm effective versus global-mode/location reads.

The standard-filename receipt retains a shared-template sentence about the custom basename; its [scope qualification](../evidence/js-config-20261124T142228313404Z/qualification.json) points to the actual profile and frozen producer without replacing the original record.

Each trace retains command, selected overlay, exit status, raw/public stream identities, and before/after file contents. All 64 commands return 0. Read/explanation commands preserve the measured configuration/project files. Writes change only the selected file in those images. Native logs and caches are outside that image claim. No personal configuration is copied into the fixture, and the public projection masks local account labels; private originals remain available for verification.

## Current meanings

| Boundary                                                               | npm                                              | pnpm                                                  | Yarn                                                                               |
| ---------------------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Default `config set` destination                                       | User npmrc                                       | Global `auth.ini` for this registry key               | Project rc                                                                         |
| Project value masks a lower-file write                                 | Yes                                              | Yes                                                   | Yes                                                                                |
| Environment value masks a file write                                   | Yes                                              | Yes                                                   | Yes                                                                                |
| Selected generic registry CLI override                                 | Wins over environment                            | Wins over environment                                 | Not exposed/tested through an equivalent flag                                      |
| Global-mode/location-global read with project, user, and global inputs | User value; project omitted                      | Global value                                          | No matching global-mode request in this profile                                    |
| Project assignment removed                                             | User fallback                                    | Global fallback                                       | Home fallback with standard rc filename; default fallback with the custom filename |
| Explanation used here                                                  | `config list` names files and overridden entries | `config list` gives merged values and registry routes | `config npmRegistryServer --json` gives effective value, source, and default       |

The key is `registry` for npm/pnpm and `npmRegistryServer` for Yarn. pnpm routes this key to INI rather than general YAML settings. Its other setting classes can have different destinations; this table is not a rule that every pnpm setting lives in `auth.ini`.

A successful file edit does not promise a changed effective value. npm and pnpm's default lower-scope writes persist even while the project continues to supply the registry. A later environment-free read exposes the appropriate file precedence. npm's global mode is also not a raw-global-file query: the user layer still participates. Preserve those distinctions rather than flattening all three tools into one meaning of “global.”

## Two Yarn findings

**The success headline reports the reloaded effective value as the value set.** In both filename profiles, `config set npmRegistryServer https://home-write.invalid/ --home` with an environment override writes the requested home value, but reports:

```text
Successfully set npmRegistryServer to 'https://environment.invalid/'
```

The file images and a later environment-free read distinguish what was saved from what remains effective. The [pinned set command](https://github.com/yarnpkg/berry/blob/62edcb0e2f62c93b7b2ec2ef6a79edeaf2e06b3c/packages/plugin-essentials/sources/commands/config/set.ts) reloads configuration after the write and uses its effective value in that headline. The candidate reporting change is to name the destination and requested stored assignment, then explain any masking source. Reuse the request, reload, and source information; a second configuration engine is unnecessary. JSON/report compatibility and nested or secret settings need review before implementation.

**A custom rc basename is written at home but not loaded there.** With `YARN_RC_FILENAME=.fixture-yarnrc.yml`, `--home` changes that file in the private home directory. After removing the project assignment, fresh root and child reads return Yarn's default rather than the saved home value. With the standard `.yarnrc.yml`, the same workflow returns the saved home value. The pinned core's `updateHomeConfiguration` delegates to the configured-basename writer, while `findFolderRcFile` uses the default basename for its separate home load. Neither result is inferred from a stale process: each read is a new CLI invocation.

This is a bounded read/write destination mismatch, not a package-resolution or credential-loss claim. A correction must deliberately align the home reader and writer. Honoring the configured basename on both sides is one candidate; preserving the current canonical home read and targeting that file explicitly is another. Do not silently combine conflicting home files. Existing users may have both, so precedence, documented scope, and ambiguous old assignments require compatibility review. No product patch or upstream issue is selected here.

## Models and source comparison

[Lean](Configuration.lean) checks 17 laws; [Bend](Configuration.bend) checks nine. They retain each tool's default write target, file assignments, explicit location, effective-source rules, environment/command context, and current Yarn headline. A model-only aligned-home reader is separate from current behavior. It does not bypass environment masking or select a production compatibility strategy.

The [pure replay](conformance.py) matches both models to the 64 command records and verifies actual changed-file scopes. Effective values are compared only where the command exposes one. A computed effective value during a silent write is a model result, not an invented native observation. Yarn's explicit JSON source field and npm's overridden-source listing have their own retained evidence; other source labels remain source/model interpretations. Seven malformed research profiles are refused. These checks exercise the research decoder, not a general production configuration parser.

The [ledger](../sources/js-config-selections.json) pins 11 source files and inspected ranges. npm's command, loader, and location definition match the installed files byte for byte. pnpm and Yarn's corresponding source behavior is inspected separately; reproducible correspondence between their source trees and installed executables is not proved. General YAML/INI parsing, property paths, merged maps/arrays, and all precedence combinations are outside the models.

## Preservation, candidates, and verification

Keep file editing distinct from effective evaluation and operational use. npm and Yarn already offer useful provenance views; preserve them. A pnpm per-key source view could improve diagnosis, but the current merged report does not itself prove that every origin is retained internally. Inspect that collector before adding attributable origin metadata; do not reconstruct the winner by comparing equal strings or build a competing evaluator.

For empack, this supports explicit target, stored change, effective meaning, and completion facts in configuration results. A host config edit, project intent edit, sync, and instance update are different actions. A UI can explain a masked saved value without suggesting that the write failed or that a runtime already adopted it. The proposed portable editor should preserve raw documents and scope while delegating existing interpretation rather than maintaining a frontend-only precedence table.

Before adoption, qualify standard/custom basenames, both home files present, equal values from different sources, invalid values, nested settings, null/deletion, arrays/maps, secret redaction, failed or interrupted writes, comments/raw preservation, concurrent edits, workspaces, and other platforms. Existing redaction, authentication, settings admission, and operational registry use remain pending; these harmless registry URLs establish none of them. Production changes require a separate decision.
