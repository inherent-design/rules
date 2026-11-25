# Filesystem provider lifetime and writes

The installed VS Code 1.147.0 API reports a removed provider's old writable/read-only capability even after reads correctly fail with `Unavailable`. The pinned bridge forwards the historical provider's capabilities on removal instead of removing the cached entry. This is a bounded capability-cache finding, not evidence of a security bypass. A one-expression invalidation candidate is compared separately from current behavior; no VS Code or empack product code changed.

## Native observations

Three disposable macOS desktop processes used ordinary in-memory custom providers through `workspace.fs`, provider registration, and file watchers. The product identifies [the pinned source commit](../sources/vscode-source.json). Each collection retains its extension, launcher, settings, API results, provider calls, before/after backing maps, process arguments, exit, and closure check.

| Collection | Observed scope | Retained limit |
| --- | --- | --- |
| [First run](../evidence/vscode-filesystem-20261125T124652990742Z/observed.json) | 21 rows: missing schemes/files, read copies, writes, duplicate registration, read-only policies, queued buffers, provider replacement, and a watcher | Its final `detached` fixture incorrectly waited for capability knowledge to disappear and timed out. That error is preserved. |
| [Removal follow-up](../evidence/vscode-filesystem-20261125T125524932768Z/observed.json) | Six rows in a fresh process: writable removal, read refusal, read-only replacement/removal, and read refusal | Immediate or 500 ms samples alone do not prove indefinite staleness. |
| [Write controls](../evidence/vscode-filesystem-20261125T125958897211Z/observed.json) | Four rows in a fresh process: parent creation before refusal and caller-side buffer copying | Local callback behavior, not OS or remote permissions. |

An earlier [preparation-only directory](../evidence/vscode-filesystem-20261125T124545684898Z/meta.json) has no process or API observations and contributes no native cases. Later extensions differ intentionally: the second measures removal rather than waiting for an assumed result, and the third adds parent-refusal and caller-copy controls. Frozen producers remain unchanged.

All three processes exited with status 0; their owned groups were absent, and closure checks found no remaining workspace processes. A control acknowledgement is not that retirement evidence. Private user-data/extensions/workspace directories and in-memory secret storage reduced interference. Shared host stores and incidental external profile writes were not measured; complete application isolation is not claimed. Desktop access was released after the runs.

## Distinct contracts

**Capability knowledge and live registration.** An unknown scheme returns `undefined`. After unregistering a writable provider, `isWritableFileSystem` still returns `true`; after replacing and unregistering it as read-only, it still returns `false`. Both reads fail with `Unavailable`. A capability result is neither a live-provider lookup nor an authorization grant.

**Scheme and backend permissions.** Scheme-wide read-only registration blocks the write before the provider callback. Per-file read-only metadata does not prevent the writable provider's local shortcut from receiving it. The deliberately permissive fixture accepts that write; an enforcing provider rejects it with `NoPermissions`. The API already requires the backend to reject insufficient permissions. The permissive fixture is a control, not a demonstrated permission bypass. Keep backend responsibility rather than invent a universal permission layer.

**Partial effects.** A write to a new parent creates that directory before the provider rejects the file. The file inventory remains intact and the empty directory remains. A refusal does not prove that nothing changed. Automatic removal of the parent would require ownership and concurrency evidence this fixture does not provide.

**Borrowed and captured bytes.** The read shortcut makes a copy: mutating the returned array leaves provider backing unchanged. The queued write shortcut retains the submitted array reference. Mutating it while another write holds the queue changes the later callback's bytes. In a fresh process, submitting `bytes.slice()` preserves the original content. This is a caller-side snapshot control, not a patched API or general thread-safety guarantee. Automation requiring an exact saved/exported image should own its immutable input snapshot.

**Provider incarnation and pending work.** A queued write captures the old provider. Disposal and registration of a new provider for the same scheme change later reads, but the old write still completes against the old backing. The new backing remains intact. Unregistration is not cancellation or retirement of pending work, and URI equality does not identify a backing incarnation.

**Watchers.** One requested event arrives, followed by no additional event during a 250 ms window after disposal, with zero active watches. This does not qualify arbitrary native filesystem notifications, event ordering, or universal quiescence.

## Source comparison and models

[Source selections](../sources/vscode-filesystem-selections.json) pin six files at `8a14f0cc1b08d531eb83255ea3764ae22aa932b5`. Excerpts retain the registration producer, consumer shortcuts, bridge, capability map, and masks. Selected source inspection does not establish a reproducible source-to-binary build.

`FileService` emits removal as `{ added: false, scheme, provider }`, retaining the historical provider object. `MainThreadFileSystem` forwards `e.provider?.capabilities ?? null` without considering `added`. `ExtHostFileSystemInfo` deletes only on `null`, so removal instead writes the old capabilities back into its map. The native samples match this source explanation. Later re-registration updates the entry.

The candidate expression is `e.added ? (e.provider?.capabilities ?? null) : null`. The [source replay](../evidence/vscode-filesystem-source/fragment.cjs) executes unchanged bridge/map/query bodies with a URI identity adapter, JavaScript `Map`, and six ordered fixture events, then compares the explicitly changed candidate. The two ordinary removals carry the old provider; the final absent-provider removal is a synthetic compatibility control. An unrelated scheme must not overwrite the fixture scheme. The candidate clears removals and preserves additions under this ordering. Out-of-order delivery, general RPC behavior, and full application qualification remain open. No upstream issue or implementation was selected.

[Lean](FileSystems.lean) has ten laws; [Bend](FileSystems.bend) has six. They separate current/proposed capability knowledge, write admission and parent effects, borrowed/copy input, and the captured completion target. The [case decoder](FileSystemsCase.lean) and [comparison](filesystem_conformance.py) check 32 scalar results: six current/candidate event pairs, six native write boundaries, and two native queue boundaries. The 31 independently audited native rows also retain read-copy, incarnation, errors, and watcher facts; they are not all claimed as separate model executions. The captured-target law is an identity projection, not an implementation of queuing or cancellation.

The observer rejects six changed observations and two malformed/unsupported inputs. Its [basis](../evidence/vscode-filesystem-source/basis.json) hashes frozen evidence and comparison inputs. [Conformance](../evidence/vscode-filesystem-source/conformance.json) records the actual scope. Unknown is not absent, and a source candidate is not a native product fix.

Compile the two Lean modules with the pinned tools, then replay:

```sh
mkdir -p .build/vscode-filesystem-formal/applications/vscode
LEAN_PATH="$PWD/.build/vscode-filesystem-formal" <pinned-lean> -DwarningAsError=true -o .build/vscode-filesystem-formal/applications/vscode/FileSystems.olean applications/vscode/FileSystems.lean
LEAN_PATH="$PWD/.build/vscode-filesystem-formal" <pinned-lean> -DwarningAsError=true -o .build/vscode-filesystem-formal/applications/vscode/FileSystemsCase.olean applications/vscode/FileSystemsCase.lean
<pinned-bend> applications/vscode/FileSystems.bend --verdict
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/filesystem_conformance.py
```

Replay reads retained observations and runs pure models plus the retained Node fragment. It never launches VS Code. `filesystem_source.py` regenerates the fragment from the checksum-pinned ignored source cache and records Node's actual version. `filesystem_probe.py` collects native evidence only under separately coordinated desktop access; `request quit` must be followed by the process/closure result.

## Remaining work and UX implications

Keep the existing distinctions between callbacks, capabilities, and backend errors. Applications built on these services should retain the provider identity and exact input bytes with pending work, report actual refusal and retained effects, and avoid treating a capability hint as live-storage evidence. Review existing error and lifecycle APIs before adding another status surface. The narrow invalidation candidate is preferable to a new generation framework for the observed ordered path; stronger concurrency requirements need their own evidence.

Native OS backends, remote providers, browser handles/renewal, real permission changes, watcher guarantees, GUI feedback, and interruption recovery remain open. This band neither closes nor reattributes the earlier custom-provider document save/dirty race. The full nine-application study remains active and incomplete.
