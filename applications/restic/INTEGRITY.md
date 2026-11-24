# restic check scope and index recovery

A successful check establishes its requested scope. In this local restic 0.20.0 fixture, ordinary `check` accepted a repository containing a same-size damaged data blob. `check --read-data` and dumping the affected file rejected it. This is the documented separation between metadata consistency and reading stored file data, not a newly identified integrity bypass.

## Native evidence

The [collector](integrity_probe.py) made a new byte-for-byte copy of the completed [lock fixture](../evidence/restic-locks-20261124T082746005710Z/receipt.json). Every copied repository file had a distinct inode; no hardlinks were used. The original image was hashed before and after and never opened by these restic commands. Two snapshot objects and four encrypted packs formed the fixed input.

The [receipt](../evidence/restic-integrity-20261124T085942925906Z/receipt.json), [trace](../evidence/restic-integrity-20261124T085942925906Z/trace.json), and [controls](../evidence/restic-integrity-20261124T085942925906Z/controls.json) identify 20 native commands. The tool is the previously publisher-checksummed macOS arm64 binary. This is local evidence, not a remote-backend, other-platform, or reproducible-build qualification.

| Repository state and request                                      | Observed result                                                                                            |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Pristine: `check`, `check --read-data`, known-file `dump`         | All exit 0; dump matches the exact 24-byte payload.                                                        |
| Same-size data-body fault: `check`                                | Exit 0.                                                                                                    |
| Same fault: `check --read-data`                                   | Exit 1, with blob authentication and unexpected pack-ID diagnostics.                                       |
| Same fault: `check --read-data-subset 1/2`                        | Exit 0; this half excludes the damaged pack.                                                               |
| Same fault: `check --read-data-subset 2/2`                        | Exit 1; this half includes it.                                                                             |
| Same fault: affected file `dump`                                  | Exit 1 with a ciphertext-verification diagnostic.                                                          |
| Same fault: `repair index --read-all-packs`                       | Exit 0; index objects change, damaged pack bytes do not.                                                   |
| After index repair: `check`, full data read, affected file dump   | Metadata check still passes; full read and dump still fail.                                                |
| Pristine pack bytes restored by the fixture                       | Full read and exact dump both pass. This is external byte restoration, not restic recovering lost payload. |
| All copied index files removed: `check`                           | Exit 1. The packs and snapshots remain present.                                                            |
| Missing indexes: `repair index --read-all-packs`, full read, dump | All exit 0; exact file bytes and both original snapshot objects remain.                                    |

The payload is `Completed held A input.` followed by LF. Native `cat index` identifies its one data blob by the SHA-256 of those plaintext bytes. The injected XOR changes byte 32 inside that blob's encrypted body, retaining the pack's name, length, header region, and mode. It does not substitute a random pack or damage a tree. Repair operations change only index objects in the captured repository images; snapshot and pack bytes remain unchanged across every native command. The fixture itself performs the explicitly recorded fault, pristine-byte restoration, and index removal between commands.

Checks use their default temporary cache, visibly reported in the streams. No `--with-cache` or `--no-cache` workaround is used. Other commands use a private normal cache. A successful dump is independently compared with known bytes; a successful checker exit alone is not used as that comparison.

The [first attempt](../evidence/restic-integrity-20261124T085920873194Z/disposition.json) is excluded from integrity qualification. Five baseline commands finished, but fault injection was refused by the copied pack's read-only mode. Its source and copied images remained identical. The corrected collector briefly enables owner writing only on the cloned target and restores its mode. Both originals and the failed-attempt evidence remain retained.

## Source and models

The [source ledger](../sources/restic-integrity-selections.json) pins revision `9c88ff768f10c192dc6a87619a65a16374080e33`. The public CLI checks index/pack metadata and tree references before optionally reading selected packs. The repository reader verifies blob decoding/authentication and the pack hash. Half subsets select packs by the first ID byte modulo two; they do not mean the first or last half of a sorted listing. Snapshot-filtered checks have a further pack-selection boundary, which this fixture does not exercise.

Index repair reconstructs index information from pack files and rewrites the index namespace. Its success is not a claim that file payload was reconstructed. The experiment establishes this distinction without executing `repair packs`, destructive snapshot repair, or forgetting missing file references.

[Lean](Integrity.lean) models captured pack identity/health, index and tree consistency, requested read scope, one-file availability, and header-based index reconstruction. Ten laws preserve these distinctions. [Bend](Integrity.bend) independently projects four decision laws. The [owner-local comparison](integrity_conformance.py) checks 18 command outcomes across both models, plus five invalid research-input refusals. The two native `cat index` commands supply fixture identity rather than outcome-model cases. The model's `fullDataClaim` is an allowed interpretation of a successful all-data request over the captured set, not an additional native output field or an independent measured result.

Model premises are deliberately narrower than restic: trees remain intact, all pack observations are available, one data blob changes, and index reconstruction has recoverable headers. Metadata consistency includes tree/reference validity; it is not generally equivalent to an index directory being nonempty. No law claims general repair success, undiscovered-pack coverage, authenticated publisher intent, arbitrary snapshot selection, or recovery from lost keys.

## UX and compatibility

Keep the distinct check modes. The useful reporting improvement is to state what was checked: metadata, selected data packs, or all data packs in the captured scope. A successful subset should retain that qualifier. Repair completion should identify the repaired namespace and direct users to the relevant post-repair check; it must not imply recovered file contents.

These are reporting candidates, not selected restic CLI or wire-format changes. Preserve existing exit codes, options, repository formats, and the ability to rebuild indexes without reading every file body. Before adopting new output, compare structured and text reports against these same requests, including subset success with an unselected damaged pack and index-repair success with still-unreadable data.

For empack, apply the same distinction to existing checks and exact repair: metadata/selection agreement, verified cached content, materialized files, and runtime behavior are different claims. An operation should name its verified set and basis. A successful metadata check must not imply every optional consumer artifact was built or the game launched. This study does not select a new checker, change authenticated release meaning, or authorize a production implementation.

## Retention and remaining work

The completed copy, password, pristine pack/index files, raw streams, and identity-redaction map stay in ignored `work/`, about 176 KiB. They are consequential evidence, not disposable cache. Public stream copies mask OS user/host identifiers and retain separate raw/public hashes. Full redaction equivalence and source-cache replay require the owner-local originals; a fresh public checkout does not possess them. All 20 owned processes were reaped, and no lock remains.

Tree/header faults, unavailable keys, interrupted repair publication, remote partial reads, snapshot filters, cache reuse, larger multichunk file output, general restore metadata/traversal behavior, and concurrent owners remain separate verification obligations. The later [restore-policy band](RESTORE.md) adds bounded overwrite and verification-scope controls. No complete restic integrity, repair, or restore family is qualified.
