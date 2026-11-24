# Prism: update cleanup and override records

This band compares selected source methods and their disposable native fixtures with formal models for Prism Launcher 11.1.1 at `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. It establishes cleanup and record-path counterexamples at this method boundary. It does not qualify complete launcher updates or select a production change.

## Captured boundary

The [collector](update_probe.py) executes the unmodified `scheduleToDelete` method, the deletion block from `InstanceCreationTask::executeTask`, `Override::createOverrides` and `readOverrides`, and two filesystem helpers. The [source ledger](../sources/prism-update-selections.json) retains exact upstream revisions, hashes, inspected ranges, and licenses. Generated upstream excerpts and binaries remain in the ignored working directories.

The [primary receipt](../evidence/prism-update-20261124T185142536633Z/receipt.json) covers 22 cleanup cases and eight joined override-record cases with real Qt 6.12 on macOS arm64. All files, links, directories, and unrelated-content canaries belong to disposable fixtures. The joined cases connect the selected writer, reader, scheduler, and cleanup block through an explicit old-install copy adapter. They do not run the complete importer, staging system, update task, or GUI.

Dialog answers, the save-choice cache, the override flag, and the task event/continuation interface are controlled adapters. Cleanup continuation is a fixture marker, not whole-operation success. An existing override-list replacement branch is explicitly excluded. The [earlier capture](../evidence/prism-update-20261124T185030965131Z/receipt.json) retains the first 28 cases before adding the joined cleanup and two cached-refusal cases; the compiled primitive hashes agree across both captures.

## Observed decisions and effects

- **Save protection uses the raw prefix.** `saves/world/level.dat` prompts and remains when the answer is No. `./saves/world/level.dat` and `mods/../saves/world/level.dat` reach the same fixture file without prompting and remove it. Both aliases also remove it when the cache is explicitly No. The fixture creates the intermediate `mods` directory, so the latter path is traversable on this host.
- **Recorded override paths can lose their destination.** A file named `config/my-overrides-settings.toml` is recorded as `settings.toml`, and `config/overrides/rules.json` becomes `rules.json`. The source derives a relative path by splitting the full path on the override directory's name. The joined fixture removes unrelated files at those shortened destinations and leaves the original override files behind. The corresponding client-overrides case has the same problem.
- **Line records do not preserve every host filename.** Reading trims leading/trailing whitespace, including the tested nonbreaking spaces. A filename containing a newline produces multiple records. In the joined fixtures, those records remove unrelated canaries. This establishes selected helper behavior for valid Mac filenames, not acceptance of those names through an actual pack archive or every supported platform.
- **Failure does not undo preceding cleanup.** A scheduled directory fails `QFile::remove`, but the loop still removes regular files before and after it, then reports failure. No rollback occurs in this selected block. A failed task must not be described as having made no changes.
- **Other cases retain distinct meanings.** Indexed-file scheduling includes enabled/disabled counterparts; override scheduling does not request that pairing. Missing files and dangling links are skipped by the existence check. A valid file symlink is removed while its fixture target remains. A changed `options.txt` scheduled as an old override is removed; these methods provide no seed-ownership policy.

The [observation checker](update_observations.py) validates source/fragment identities, captured streams, inputs, preserved post-run fixtures, recorded path losses, cached refusal cases, and partial effects. The [summary](update-observations.json) records the bounded findings. It runs no compiler, launcher, or deletion operation. Native probe exit zero means collection completed; individual cleanup failures remain recorded inside that successful collection.

## Models and replay

[Lean](Cleanup.lean) models lexical normalization, cached save choices, scheduling, disabled pairing, ordered cleanup over typed static nodes, current record transformation, and proposed destination-preserving rules. Twenty laws include failure persistence, preservation of untargeted cells, known-No protection, accepted filename preservation, and the concrete counterexamples. They retain the input-state and host-profile premises; they do not establish native construction or realpath safety.

[Bend](Cleanup.bend) implements scheduling, record text, and failure aggregation, with nine checked laws. Failure aggregation consumes admitted paths, including the protection decision, rather than every requested path. Its normalized destination is an independently checked lexical host witness. It does not independently model the complete typed filesystem mutation. Small character-list operations keep the Lean laws kernel-reducible; the models do not claim equivalence with every QString UTF-16 or Unicode-whitespace operation.

The [replay](cleanup_conformance.py) derives inputs from captured requests and preimages, then compares the Lean model with 22 cleanup outcomes and eight joined record/effect outcomes. Bend matches all 22 schedules, eight record bags, and 22 failure summaries. The proposed schedules also agree between the models. Override record/path comparisons use bags because filesystem iterator order is not qualified. The joined final effects match these particular fixtures; this does not prove arbitrary cleanup reordering is harmless.

The proposed destination guard preserves all four aliased-save fixtures. Correct relative recording and delimiter-safe reading preserve unrelated canaries in five other fixtures; a newline filename is refused before any candidate deletion. These ten changed outcomes are model comparisons, not execution of a patched launcher. Nineteen malformed research inputs are refused by the Lean decoder, including unknown state/operation/profile, missing answers, unsafe paths, ambiguous cells, unmodeled link changes, and unsupported UTF-16 slicing. Research refusals are not claims about Prism's own input validation.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/prism/cleanup_conformance.py
```

This command compiles the current Lean model into ignored private output and replays retained data. It runs no native collector, launcher, or deletion operation. The [comparison receipt](cleanup-comparison.json) retains the model/source/stream basis. `scripts/check-rules.py` separately checks all tracked formal modules.

## Design and verification direction

Preserve raw author spelling, validated destination identity, record serialization, selected deletion, actual file effects, and final task outcome separately. Save protection should operate on an admitted destination inside the game root, before scheduling any destructive action. Lexical normalization alone does not establish safety through arbitrary symlinked directories. The existing host contracts can express these distinctions; no new universal host primitive is selected.

A focused override-record candidate should derive paths relative to the known override root and preserve filename bytes through serialization. For the existing line format, reject unrepresentable record delimiters explicitly and remove only line terminators when reading, rather than trimming filenames. A structured format is an alternative, not an adopted requirement. Neither change repairs an already-corrupted historical list: uncertain old mappings need retained evidence and a safe review/reconstruction path, not guessed destructive targets. Changing records also does not introduce seed ownership; that requires a separate application policy.

The save-choice field is declared without an initializer, and the selected Modrinth constructor does not initialize it. This fixture supplies explicit states. Native constructor/initialization behavior remains an unresolved source-level obligation; do not infer a reliable NotAsked state from these controlled calls or manufacture a product observation by reading indeterminate storage.

Actual archive admission, extraction, optional resources, staging failure, publication, cancellation, historical records, symlinked ancestors, dynamic referents, and supported platforms still need separate native flows. Keep enumeration order, source versus installed bytes, and constructor authority explicit. The earlier [indexed hash-filter study](README.md) remains a distinct planning boundary. Most Prism features and the full joined transition remain pending.
