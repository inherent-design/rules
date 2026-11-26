# Prism export selection and archive completion

The selected Prism source omits hidden regular files while traversing hidden directories. It writes directly to the selected archive path, so a failed or canceled write can replace the prior archive before the outer task reports its result. These are qualified source-component observations, not reproduced failures of the full installed launcher.

## Scope and evidence

The [source ledger](../sources/prism-export-selections.json) pins Prism commit `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4` and its actual tree object. Per-file ranges distinguish inspection from acquisition. The commit-addressed tree API response initially repeated the requested commit identity; the commit object's `tree.sha` established the actual tree. Raw file bytes matched their individual Git blob identities.

The installed Mac launcher is 11.1.1. Its isolated GUI attempt reached setup and then the launcher window without adding an account, but was interrupted when the user needed the desktop. It produced **zero exports**. The private process was terminated and its group retired; desktop access was released. Conflicting focus/object observations remain inconclusive, and the user reports that overlapping personal work probably interfered. This is not an attributed launcher or general automation defect. Raw GUI scripts, images, profile, and observations remain local; only the [qualification](../evidence/prism-export-20261126T072754396584Z/qualification.json) is public evidence here.

The [headless receipt](../evidence/prism-export-headless-20261126T075341047978Z/receipt.json) records eight owned cases using real QtCore 6.12.0 and libarchive 3.8.11 on macOS. Six `ArchiveWriter` bodies and the recursive collector are unchanged; `ExportToZipTask::exportZip` has one class-qualifier rename. Translation, task interfaces, a constant cancellation witness, and an exact exclusion callback are explicit adapters. This does not execute bundled Qt 6.9.3, `FileIgnoreProxy`, `QFuture`, the outer task's cleanup/signals, or a full product export. Generated source and binary remain private and attributable; no upstream implementation body is distributed as our source.

Two earlier compiler attempts are excluded. One lacked an explicit SDK; the other lacked libarchive headers. Their frozen producers, errors, and terminal process records remain retained. The successful attempt used an explicit SDK and matching already-installed libarchive headers/library. No dependency installation, global toolchain change, or new desktop access was needed.

## Observed boundaries

| Case | Retained result |
| --- | --- |
| Instance root, following file links | Six members include instance metadata and ordinary files inside a hidden directory; hidden regular leaves are omitted. |
| Game root, retaining links | Five members; the generated file link remains a link relation containing its absolute target. |
| Exact exclusion and destination prefix | The named file is omitted; four regular members use `overrides/`, while the extra metadata member remains at archive root. This is an archive mechanism test, not a Modrinth pack. |
| Missing root | The fixture does not invoke the writer; the previous output sentinel remains. |
| File removed after collection | The writer reports a read error after two entries. A partial ZIP replaces the previous output. |
| Cancellation witness set before entries | The method returns an empty optional error, and an empty ZIP replaces the previous output. This is not a successful task or proof of actual cancellation/retirement. |
| Output path is an existing directory | Opening fails; the directory remains. |
| Every enumerated file excluded | The method completes with a valid empty ZIP, replacing the previous output. |

The independent [reader](observations.py) reconstructs enumeration from the frozen preimage, reads archive payloads and link modes, verifies hashes against source bytes or explicit link-target bytes, and checks the scoped after-image. It checks 18 archive members. The generated fixtures contain no personal worlds or account data; their world-like sentinel and logs test the unfiltered collector, **not the GUI's default exclusion policy**. Ordinary ASCII filename ordering is admitted only for this controlled tree. Unicode payload bytes are verified; Unicode filename behavior is untested.

## Selection and distribution semantics

The instance ZIP dialog selects from the instance root. The Modrinth dialog selects from the game root and later builds a manifest plus `overrides/`. Its source distinguishes host-resolvable artifacts from bundled local files, component versions, optional-file metadata, and download eligibility. The complete Modrinth exporter, provider lookup, manifest admission, and importer have not been executed here.

Both dialogs show hidden entries, but the shared collector's file enumeration omits hidden leaves. The hidden `.packignore` control file is omitted as well. This supports a selection/serialization discrepancy worth a normal UI regression; it does not yet prove which hidden rows the user can select or the resulting full-product artifact.

Both dialogs save `.packignore` before testing acceptance; the pack dialog also saves export metadata on Cancel. Those are remembered author preferences, not an export artifact or publication receipt. The ignore file is a literal blocked-path list in the inspected proxy, not a general gitignore parser.

Following a file link preserves its archive-relative destination but reads backing outside the instance. The fixture's backing is still inside its owned temporary tree. Keeping the link instead stores the target relation, which need not be useful or portable to a recipient. Neither equal filenames nor a ZIP extension establishes a self-contained backup, privacy policy, or safe extraction contract. Directory-link cycles, missing link targets, permissions failures, cross-host names, and hostile archive paths remain outside this band.

## Models, proposals, and compatibility

[Lean](../prism/Export.lean) models finite enumerated entries, hidden/excluded selection, destination and link roles, ordered read failure, output replacement, and completion evidence. Sixteen laws preserve those distinctions. The [decoder](../prism/ExportCase.lean) rejects unsupported profile values and duplicate identities. [Bend](../prism/Export.bend) supplies ten laws and separately compares selection, writer state, replacement, completion, and written link roles. It does not prove archive encoding or duplicate the entire ZIP implementation.

The [comparison](conformance.py) matches all eight retained cases against Lean and 57 Bend scalar observations. Five changed-result controls, five decoder refusals, three changed input-premise controls, and four corrupted raw-evidence controls keep the comparisons falsifiable. No application, compiler, or GUI is launched by this replay. Source caches and old private tool artifacts can be unavailable without inventing revalidation; their absence is recorded.

Keep-current preserves formats and remembered selection behavior. Candidate improvements are to preview the **actual** selected archive inventory, explain hidden/link/source roles, distinguish saving preferences from creating an archive, and report completion only after final task outcome. A separate model-only publication policy keeps the previous archive unless a completed, non-canceled candidate is admitted. No staged/atomic replacement implementation was exercised. Filesystem replacement, overwrite authorization, durability, outer cleanup, and recovery need their own host-qualified design before adoption.

Including hidden leaves would change output content and privacy expectations; showing an omission or refusing an inconsistent selection may be safer until policy is reviewed. Changing symlink behavior changes portability and disclosure semantics. Cancellation preference persistence may be intentional; any change needs explicit save/discard behavior and compatibility review, not merely new wording.

For empack, preserve project backup, distributable snapshot, and installed consumer as separate contracts. A saved project or successful archive method is not a verified consumer export. No production Prism or empack changes are selected by this study.

## Verification and remaining work

With the pinned Lean/Bend tools, run `python3 scripts/check-rules.py`, then `python3 applications/prism-export/conformance.py`. A focused gate may provide its compiled module directory with `PRISM_EXPORT_FORMAL`; the replay writes only its private `.build/prism-export-replay` output. `headless_probe.py` and `probe.py` collect new native evidence only when explicitly selected; neither belongs in ordinary CI.

A future coordinated desktop session must export a disposable instance through the normal dialogs, compare selected hidden/link rows with actual members, cancel after changing preferences, and qualify successful/failed/canceled Task cleanup with an existing output. Modrinth output requires an independent manifest/member/reference readback and a disposable importer, followed by supported-platform checks. Keep the current source-component evidence and the unresolved GUI obligation separate. The full nine-application goal remains incomplete.
