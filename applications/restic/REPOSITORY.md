# restic: repository admission and format migration

Repository location, persistent identity, password access, format version, and command completion are different facts. In the selected local restic run, an unknown migration name returns status 0 without changing the repository. A mixed unknown/valid request also returns 0, reports the unknown name, and completes the valid upgrade. Automation cannot treat that status alone as evidence that every requested migration was applied.

The format upgrade itself preserves the measured repository identity, chunker parameters, and every non-config file record. A final full data check and payload dump succeed. Those observations qualify this local normal-completion flow; they do not prove backend atomicity, interruption recovery, or general repository health.

## Profile and evidence

The program is restic 0.20.0, Go 1.27.4, macOS arm64. Its [binary pin](../sources/restic-tool.json) matches publisher release-asset and checksum-file digests; GPG release provenance and a reproducible source-to-binary build were not verified. Nine [source identities and inspected ranges](../sources/restic-repository-selections.json) are pinned to `9c88ff768f10c192dc6a87619a65a16374080e33` with Git blob and SHA-256 checks.

The [native capture](../evidence/restic-repository-20261126T024414054889Z/receipt.json) contains 22 full CLI calls. Eighteen primary requests cover initialization, authenticated opening, listing migrations, and requested migration application. Four calls supply version/setup, a tiny backup, payload readback, and a full integrity check. They are not eighteen additional unit or model comparisons. Only new owned local repositories and fake data are used.

Two missing-config states are explicitly authored derivatives of the new repository. One retains a key but removes config, snapshots, data, and indexes; the other retains snapshots while removing config and keys. Their refusal behavior is useful evidence of conservative admission. They are not observations of a crashed initializer, nor recipes for repairing a real backup.

## Creation, opening, and persistent identity

| Request | Result | Independently observed boundary |
| --- | --- | --- |
| Initialize unsupported format 99 | Status 1 | Endpoint is not created. |
| Open a missing repository | Status 10 | No config or repository is created. |
| Initialize format 1 | Status 0 | Config and key appear; authenticated read reports format 1. |
| Initialize an already configured repository | Status 1 | Existing file records are unchanged. |
| Open with the other generated password | Status 12 | Existing file records are unchanged. |
| Initialize the key-only derivative | Status 1 | Recognized key evidence is preserved; config stays absent. |
| Open that missing-config derivative | Status 10 | A remaining key does not establish a usable repository. |
| Initialize the snapshot-only derivative | Status 1 | Recognized snapshot evidence is preserved; config stays absent. |
| Initialize with the default selector | Status 0 | Authenticated read reports format 2, the pinned stable default. |

Source inspection explains the distinct gates. `CreateRepository` rejects unsupported versions before creating a backend. The local backend refuses an existing config. `Repository.Init` also checks recognized key and snapshot IDs before minting new identity. These are guards against reinitialization, not proof that every arbitrary file is repository evidence. Directory existence, key presence, successful password access, and valid authenticated config must not be collapsed into one “repository exists” boolean.

The selected opening path checks config presence before authentication, then searches a password wrapper and loads/validates config. The model admits valid positive-version config and usable-key context from the controlled fixture; it does not prove decryption, key search, or malformed-config handling. An authenticated readback reveals the format to the observer; a failed password request does not itself disclose it.

Keep these existing conservative guards and differentiated status codes. A partial state needs preservation and inspection, not automatic initialization. Source order creates a key before saving config, but this band has no terminated initializer or recovery test. The author's missing-config derivatives cannot close that gap.

## Applying a format upgrade

The actual local sequence is format-1 initialization, backup, migration inspection, an unknown-only request, a mixed unknown/upgrade request, authenticated format-2 readback, an inapplicable repeat, a full data check, and a payload dump. No force option, prune, remote backend, or production backup participates.

| Migration request | Status and reporting | Saved result |
| --- | --- | --- |
| List on format 1 | Status 0; upgrade is listed | Config unchanged. |
| Unknown name only | Status 0; unknown-name diagnostic | Repository file image unchanged. |
| Unknown name plus `upgrade_repo_v2` | Status 0; unknown-name diagnostic and upgrade-success message | Config becomes format 2. |
| Repeat `upgrade_repo_v2` on format 2 | Status 0; inapplicable diagnostic | Config unchanged. |
| List on format 2 | Status 0; no migrations listed | Config unchanged. |

The mixed request replaces only the encrypted config record in the observed file namespace. Separate authenticated reads tie each plaintext config to its exact encrypted-file digest. The repository ID and chunker polynomial are unchanged; key, snapshot, index, and pack file bytes, modes, and mtimes are preserved. The dump equals the original source payload, and `check --read-data` passes.

Equal before/after images do not mean no writes occurred: migration commands acquire an exclusive lock, and may affect cache, temporary, or directory state. This observer records the repository file boundary. General concurrency and all other effect scopes remain unqualified.

The selected upgrade source changes the config version and preserves a temporary encrypted-config backup during its replacement attempt. Its fallback/reupload and retained-backup error paths are source-only here. The local backend advertises atomic replacement; this is not a crash/durability proof. The [pinned repository guide](https://github.com/restic/restic/blob/9c88ff768f10c192dc6a87619a65a16374080e33/doc/045_working_with_repos.rst) distinguishes the format upgrade from later compression/repacking. This run does not establish that a migration rewrites existing file data, reclaims storage, or preserves compatibility with older clients.

## Reporting proposal and compatibility

Preserve explicit format upgrades, password/key separation, and the identity-preserving normal transition. Already-current status can remain a successful skip. An unknown request name has a different meaning: the command did not recognize that requested operation. The current loop prints that diagnostic without assigning its returned error; it can continue with known names. The global `--json` option also leaves these measured migration outputs as human text, because this command chooses its human printer. Do not invent a current structured report or scrape a final success line as complete application evidence.

A focused internal candidate is one per-name result: unknown, inapplicable, applied, or failed, retaining the actual error and confirmed or uncertain effects where relevant. Compose the command summary from those results. Reuse existing migration checks and errors rather than introduce a universal status framework or change config encoding.

An opt-in structured result could provide stable per-name outcomes. A proposed strict-unknown completion policy returns nonzero for an unrecognized name while preserving independently completed valid migrations. It does not promise preflight rejection or rollback. The models explicitly retain a nonzero result with format 2 already published. This is a model-only proposal; no native candidate, new flag, product schema, or default behavior change was implemented.

The repeat diagnostic suggests `--force`; the inspected upgrade callee itself only accepts format 1. A clearer already-current message would describe the successful skip without suggesting a generic forced retry. A forced CLI invocation was not executed, so its full outcome remains a separate verification obligation.

The keep-current alternative retains existing statuses/text and requires callers to inspect diagnostics and independently read the repository version. That avoids breaking scripts, but does not provide general per-name acknowledgement. Any default exit-status or JSON change requires caller compatibility review; an opt-in report is a narrower path. Repository version, encrypted object format, keys, and backups need no migration for this reporting proposal. Before an upstream patch, compare the current implementation with these pinned sources and confirm the intended command contract.

For empack, keep request validity, exact repository/project identity, format admission, completion, and confirmed effects separate. Format changes need explicit reader capability and data-preservation rules. This comparison does not justify adding a migration framework to the selected clean-break portable project design or changing native recovery authority.

## Verification and limits

[Lean](Repository.lean) states ten laws and [Bend](Repository.bend) states nine. The [gate](../evidence/restic-repository-20261126T024414054889Z/proof-gate.json) checks two Lean modules and one Bend file. Initial binder syntax failures were corrected without changing any native observation; the original local gate logs remain retained.

The [observer](repository_observations.py) reconstructs requests from actual arguments and recognized before-state object names, associates config reads with encrypted records, checks continuity and authored edits, and derives outcomes from saved file images and original streams. Owner mode additionally verifies current private files, binary, source pins, redaction correspondence, and controlled credential profiles. This is an independent observation pipeline, not a model-refinement proof for all repository inputs.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/restic/repository_conformance.py
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/restic/repository_conformance.py --public-only
```

The [replay](repository_conformance.py) compares eighteen native primary outcomes and three separately labeled model-only proposal cases, with sixteen decoder refusals, eight changed premises, and eight changed raw observations. Neither mode executes restic, a Go compiler, a backup, or a backend operation. Public mode checks the six recorded artifacts, allowing only the explicit declaration of excluded private checks to differ. Those exclusions cover current private files, raw streams, credentials, the binary, and source caches. [Control record](../evidence/restic-repository-comparison/controls.json).

All recorded native groups retired, and the later exact-work argument scan found no remaining fixture process. That is bounded process evidence, not a universal descendant census. Passwords, encrypted repositories, raw streams, source caches, and authored derivatives remain private and retained. Remote backends, unsupported on-disk formats, corruption, forced/failed upgrades, reupload, interrupted creation/publication, and concurrent owners remain open. No complete feature/scenario status or production implementation is advanced.
