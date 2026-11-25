# Backup roots, exclusions, and file-list admission

This band compares restic 0.20.0 on a local macOS filesystem with source at `9c88ff768f10c192dc6a87619a65a16374080e33`. It uses ten generated regular files, generated list files, and a fresh repository. No existing repository or user content was opened. The [source selections](../sources/restic-inputs-selections.json), [native receipt](../evidence/restic-inputs-20261125T025013712984Z/receipt.json), and [model comparison](../evidence/restic-inputs-20261125T025013712984Z/conformance.json) retain the precise scope.

## Distinct states

A requested target, admitted existing root, visited descendant, excluded path, missing source, and saved snapshot entry are different facts. In particular, exclusion does not mean absence, and a nonzero command status does not mean no snapshot was saved.

Restic deliberately gives explicit roots priority over exclusions. Descendants remain subject to filtering. File-list expansion creates explicit roots too; it is not a separate way to apply exclusions. The selected source's `collectTargets`, filter fold, and archiver `save` boundary support those roles. Normal and case-insensitive exclusion groups reject independently. Negation within one group does not undo a different group's rejection; that last distinction has source/model evidence, not a combined-group native case here.

Backup negation also differs from restore inclusion. The inspected `IncludePatternOptions` belongs to a separate restore filtering path. This backup study does not establish a general `backup --include` command or execute restore includes.

## Native observations

Twenty backup cases and their listings produced 37 commands. Every owned process group retired. Input bytes, sizes, modification times, and inodes remained unchanged. The verifier independently reads raw/private and redacted/public streams, saved paths/types/sizes, snapshot IDs, final locks, and source/tool identities.

| Input                                                | Observed result                                                                                         |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Directory with no excludes                           | Saves all ten generated files.                                                                          |
| Directory with `*.tmp` excluded                      | Omits the two matching descendants.                                                                     |
| Explicit `secret.tmp` with `*.tmp` excluded          | Saves the file because it is an explicit root.                                                          |
| Explicit directory `nested` with `nested` excluded   | Saves the directory, filters its children, and publishes a snapshot with no files.                      |
| `*.tmp`, then `!secret.tmp`                          | Includes both matching files again. Reversing the order excludes them.                                  |
| Excluded `pruned`, then `!pruned/keep.txt`           | Does not visit the excluded parent, so the child remains absent. Reopening the parent allows traversal. |
| `--iexclude '*.TMP'`                                 | Excludes the lowercase suffixes; the ordinary case-sensitive form does not.                             |
| Normal line list                                     | Ignores the `#literal.txt` line as a comment and selects the other two files.                           |
| Verbatim line list                                   | Selects all three literal filenames, including the leading `#`.                                         |
| Normal list containing `*.tmp`                       | Expands to the matching top-level file, which is then an explicit root despite an exclusion.            |
| Verbatim list containing `*.tmp`                     | Treats the string literally, finds no such file, and refuses without a snapshot.                        |
| Normal versus verbatim `[literal].txt`               | Glob syntax finds no matching name; verbatim selects the literal bracketed filename.                    |
| NUL-delimited raw list                               | Preserves both a newline-containing name and a leading-`#` name.                                        |
| Missing trailing NUL or an empty raw entry           | Refuses before saving a snapshot.                                                                       |
| Verbatim list with one existing and one missing file | Returns status 3 and saves a snapshot containing the existing file.                                     |

The first collector incorrectly expected absolute physical source paths in `ls` output. Backing up `.` instead rooted the observed entries at the snapshot root. That initial backup and listing succeeded; the collector then failed its projection assertion. The [original run](../evidence/restic-inputs-20261125T024920808343Z/collector-failure.json), frozen producer, streams, repository, and retired-process record remain intact. A corrected fresh cohort supplies the comparisons above. This is a harness correction, not a restic defect or a retroactive success claim for the first collector.

## Models and boundaries

[Lean](Inputs.lean) models ordered exclusion groups, explicit roots, recursive traversal, admitted selections, and publication outcomes. [Bend](Inputs.bend) checks the equivalent per-file ancestor-chain projection and outcome rules. Laws preserve root priority, pruning, order-sensitive negation, independent groups, invalid framing, and partial publication. The [research decoder](InputsCase.lean) bounds its closed fixture identities and rejects malformed witnesses and unsupported input shapes.

The [pure replay](inputs_conformance.py) matches twenty native outcomes and ten file-selection bits per case in both models. Target/list admission and finite pattern-match witnesses come from a checked Python adapter. They are external premises of these models, not formal proofs of Go glob syntax, arbitrary raw/line parsing, case conversion, or filesystem existence. The adapter admits only the exercised spellings. It reads frozen list bytes, constructs proposed roots and matching witnesses, and compares against the independently recorded snapshot inventories. Changed-observation controls and refused research inputs protect that boundary.

The native check lists saved paths, node types, and sizes; it does not restore or dump every saved payload. Chunking, encryption, crash durability, remote backends, concurrent edits, permissions, special files, symlinks, device boundaries, and cloud placeholders remain separate obligations. Relative targets on this Mac do not establish every platform's path or filename behavior. The acquired filter-test source remains marked uninspected; acquisition alone supplies no test qualification.

## Preserve policy; explain its effect

No implementation defect was established in these cases. Preserve explicit-root priority and efficient directory pruning. Replacing them with a universal “exclude always wins” or “include searches through excluded parents” rule would change documented author intent and traversal costs.

A useful reporting improvement would distinguish requested roots, admitted roots, excluded descendants, missing inputs, and the snapshot actually saved. Reuse existing warnings, summaries, and saved snapshot IDs. A partial-source diagnostic should direct the operator to inspect that snapshot before retrying; a failed raw list should identify framing without suggesting a partial snapshot exists. Do not infer either result from the exit code alone. Existing docs already explain these rules, so a new warning or report surface needs a concrete workflow benefit rather than another blanket summary.

Before broadening coverage, exercise absolute and overlapping roots, exclude-file/environment expansion, both exclusion groups together, all list encodings, duplicates, permissions, and actual snapshot payload recovery. Add platform-specific filename and filesystem cases under their own profiles. A production reporting change is a separate decision. The feature's full input-policy operations remain pending; this band records bounded components and full local backup/list observations without implying complete parser or traversal coverage.
