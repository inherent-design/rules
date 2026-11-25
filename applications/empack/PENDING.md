# Manual acquisition and saved builds

This band compares a two-input build continuation through the installed empack 0.8.8-beta CLI. It changes no product behavior. The current [source ledger](../sources/empack-pending-selections.json) pins 17 files at `0b4462e3032b4f09230b15329722eabefb7f574c`; source/binary equivalence is not established. The [capture](../evidence/empack-pending-20261125T065233392919Z/baseline.json) and [comparison](../evidence/empack-pending-conformance.json) retain the actual commands, streams, filesystem images, and model basis.

## Observed flow

The fixture declares two fictional exact CurseForge selections with manual acquisition, SHA-256, and sizes of 13 and 14 bytes. These are not downloaded provider records or usable resource packs. An independent authored-wire fixture adapter created the documents; the real CLI decoded and checked them before the workflow ran. All project, state, cache, home, and download paths were private to this capture. Proxy settings refused ordinary outbound acquisition; this was not an OS network sandbox.

| Boundary | Native observation |
| --- | --- |
| Preview a new build | Exit 0, unchanged project, and no state directory. |
| Build without manual inputs | Exit 1, no product, and an explicitly saved continuation. |
| List and show | No measured project/state/cache/download content or mode change. Files remain unverified; `needed` is unknown until reconstruction. |
| Preview resume with a nonexistent download folder | No scan or measured change; unresolved inputs remain visible. |
| Wrong bytes with the expected filename and size | Checksum refusal, with unchanged measured scopes. |
| Unknown or repeated exact key | Refusal, with unchanged measured scopes. |
| Supply only the first file under a different name | Exit 1 with a saved partial continuation. Only state changed; no product appeared. |
| Inspect again in a fresh process | First file is labeled `retained; verification required`. Its host-path field remains null. The public ID changed. |
| Select the old ID | Refusal, with unchanged measured scopes. |
| Damage the private retained blob without changing its size | Inspection still reports an unverified retained file. Resume refuses the checksum mismatch and changes no measured scope. |
| Restore the original and discover two renamed copies of the second file | One verified association, successful publication, and no remaining pending recipe. The archive contains the exact 27 input bytes. |

There were 20 fresh CLI commands: three fixture/build setup commands and 17 pending commands. Every owned command group retired. The 795-byte mrpack was read independently, including its member names and contents. The author files and supplied downloads remained intact. The old pending-content blob remains after successful publication; recipe cleanup does not mean content collection.

The deliberate fault touched only the isolated first blob after all prior CLI groups had retired. Its original bytes were retained separately. Bytes, mode, inode, and mtime were restored before completion; ctime was not preserved. This is a controlled content-integrity test, not a crash-recovery or live-store repair qualification.

The first continuation collector stopped after its eighth command because it incorrectly expected `supplied_candidate` to hold a retained path. The public `verification` label carried that fact. The original producer, streams, failure attribution, and separate correction are preserved. No native command was repeated to hide the collector error.

## Model and evidence boundaries

[Lean](Pending.lean) has 12 laws and [Bend](Pending.bend) has 10. Both compare the 17 pending observations. The replay rejects six malformed/out-of-profile DTOs, changes five meaningful input premises, and checks four changes to raw native observations. Its filesystem projection derives state from recorded recipe hashes, content hashes, and actual product presence; it does not use model output to construct native expectations.

Record numbers label the two observed opaque selectors. Content tokens label the independently checked fixture bytes. Neither is a production codec or cryptographic proof. The models assume quiescent, admitted roots and the selected two-obligation profile. They do not establish general error priority, execution authority, hash collision resistance, or arbitrary recipe behavior.

Read-only means the measured regular-file/directory content and mode scopes. Baseline snapshots did not include directories; later snapshots did. Neither captures all metadata, inode access, OS-shared effects, durability, or private temporary-file history.

One important source distinction survives the projection: dry-run resume reconstructs the saved recipe and restores retained content before suppressing download discovery and publication. Explicit `--file` arguments also precede the dry-run branch. A dry run is therefore not a general promise to avoid reading or verifying inputs. Only the nonexistent-download-folder control was exercised natively here.

## Design and interface consequences

Keep a requirement, a supplied candidate, verified privately held bytes, retained backing, a saved recipe, and a published product as separate values. The existing current-source boundaries already do much of this. A portable extraction should preserve these contracts rather than reducing them to one “download complete” flag.

Keep filename hints separate from exact association keys and content assertions. Discovery should return distinct verified content candidates, not a list of authoritative filenames. Reverify selected candidates at continuation: a prior scan or retained label cannot grant future bytes.

A partial save should return its new selection alongside the still-missing obligations. Callers should refresh their reference rather than retrying an obsolete ID. The existing CLI reports that a continuation was saved; a future presentation proposal can make the new next command and unresolved inputs easier to see without describing a partial result as publication.

Keep inspection cheap and explicit about unknowns. `requirements_complete: false`, unknown `needed`, and retained-but-unverified are distinct facts. They can support concise human guidance without changing stable machine fields or pretending the selected recipe was executed.

## Remaining qualification

The parent manual-pending, cache/lease, and consumer-build operations remain pending in the inventory. This component does not qualify browser opening, bounded wait/interrupt, scan limits, weak-assertion ambiguity, symlink races, missing retained backing, concurrent writers, stale author documents, discard, failed publication/cleanup, cache eviction, or power loss. Import, synchronization, and instance continuations have their own schemas and boundaries; they were not executed here. Windows/Linux parity and real restricted provider/game integration remain open.

Replay the retained comparison without running empack:

```sh
LEAN=/path/to/lean BEND=/path/to/bend python3 applications/empack/pending_conformance.py applications/evidence/empack-pending-20261125T065233392919Z
```

Do not rerun the one-shot producers over the completed capture. New native controls need their own explicit, isolated fixture and provenance.
