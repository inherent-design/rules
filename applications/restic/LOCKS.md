# Repository locks, interruption, and recovery evidence

This band uses restic 0.20.0 on macOS arm64 and pinned source `9c88ff768f10c192dc6a87619a65a16374080e33`. Twenty-one commands operate on a new private local repository. A separate three-command follow-up establishes an actual retry-wait transition on an independent byte copy. Passwords, encrypted repositories, and original identity-bearing streams remain in ignored working storage. No personal repository is opened.

## Domain and source rules

A repository/backend location, published lock record, lock mode, creator PID/host observations, age, operation admission, process retirement, and lock removal are separate facts. Logical read/write labels do not determine lock mode. Backup appends under a non-exclusive lock. Check and actual prune acquire exclusive locks. Ordinary unlock follows its own stale-record removal rule without acquiring an exclusive repository lock.

The [selected source](../sources/restic-locks-selections.json) checks other locks, publishes a candidate, waits 200 ms, and checks again before returning admission. Any published exclusive record conflicts with another ordinary lock request; a requested exclusive lock conflicts with non-exclusive records too. A readable, compatible candidate can be observed before the caller's admission has been established. A backend upload filename is not itself a published lock ID.

Unreadable lock data is not treated as absence during admission. Empty upload objects have a separate source rule. Ordinary stale removal skips records it cannot load. Those branches were inspected and modeled; unreadable/empty published-lock faults were not injected into the native fixture. Predicate laws assume the relevant observations are complete and truthful. They are not a distributed mutual-exclusion proof for every backend.

The current stale predicate uses age above 30 minutes or a same-host process probe that fails. On Unix, that probe sends SIGHUP and returns false on any signal error. The repository code installs a SIGHUP handler for restic processes. A negative signal result is not a general proof of process absence or creator identity; permission failures and PID reuse were not exercised here. Long refresh, standby, and remote-host behavior remain source context only.

## Native lifecycle

The [primary trace](../evidence/restic-locks-20261124T082746005710Z/trace.json) and [lock observations](../evidence/restic-locks-20261124T082746005710Z/observations.json) establish these bounded transitions:

| Transition | Observation |
| --- | --- |
| Seed backup completes | One snapshot, no remaining lock. |
| A and B publish non-exclusive records while their stdin pipes stay open | Both records coexist, identify the owned processes, and report the same host. A later completes; B is interrupted. |
| Ordinary unlock while both are live | Returns 0 and preserves both records. |
| Check, prune, and an expired one-second retry | Return locked status 11 while those records remain. |
| SIGINT to B with stdin still open | No retirement within the three-second wait. EOF is then supplied; B returns 130 and its record disappears. A's record remains. |
| Complete A's input | A returns 0 and publishes one new snapshot; its record disappears. |
| Kill C while its empty stdin stays open | The process is reaped with signal status -9, but its published record remains. Check still returns 11. |
| Ordinary unlock after the collector verifies the former PID is absent | Removes C's record. A subsequent full data check returns 0. |
| Pause a checker after a canonical exclusive record appears | The owned stopped state is observed. An append request returns 11. Admission at the stop point is explicitly unestablished. After resume, the checker completes successfully and removes its record. |
| Dump A's completed snapshot | Exact generated stdin bytes remain readable after the interruption and stale-lock cleanup. Final references are the seed and A snapshots. |

The B/C outcomes establish no incomplete-source or partial-pack recovery guarantee: both were waiting on empty input. The collector's `neededEOFToRetire` field means EOF was supplied after a three-second wait expired. It does not prove that the process could never retire without EOF, nor that EOF was the only cause of eventual retirement. Do not turn a signal request into retirement evidence.

The primary `retry-after-release` call finishes in less than its two-second retry interval. Although the holder was live when the process started, the first conflicting acquisition was not observed. It is retained as a completed release/control result, not counted as a proved wait-success case.

The [follow-up receipt](../evidence/restic-wait-20261124T083844392124Z/receipt.json) corrects that gap with a stage-specific observation. JSON output suppresses the retry message in this version, so the follow-up deliberately uses human output. It sees `repo already locked, waiting up to 3s for the lock` while both processes are live and the holder's record remains. Only then does it complete the holder. The waiter subsequently succeeds. Mere process liveness was insufficient; the explicit message establishes the first conflict/wait stage.

The follow-up copies the completed repository and password into a separate private backend/cache. Exact source bytes and distinct inodes are checked before use; the original image remains unchanged afterward. This is not a shared-backend or distributed-lock test. Its retained work is about 104 KiB; primary work is about 184 KiB. Original raw streams are consequential evidence, not disposable cache.

An [initial incomplete capture](../evidence/restic-locks-20261124T082601843612Z/disposition.json) counted a local temporary-upload filename as a published ID. The controlled stop froze that upload before rename, and the native ID parser correctly refused it. The corrected observer retains noncanonical directory entries separately and uses a new capture identity. The earlier capture is excluded from the qualifying counts; original files and cleanup disposition remain.

## Evidence privacy and models

Public stream copies replace local user/host names and UID/GID details. Raw bytes and the private redaction map remain under ignored `work/private/`; raw and public digests are recorded separately. Diagnostic `--no-lock cat lock` calls inspect the controlled records and are excluded from ordinary reader-admission evidence. Their success must not be used to claim that normal readers can bypass an exclusive lock.

[Lean](Locks.lean) separates compatibility, current stale policy, ordinary removal, known retirement with or without cleanup, and publication versus admission evidence. Nineteen case projections match the retained observations. Some positive cases are published compatible candidates, not separately confirmed admission of the interrupted/killed operation; the [comparison record](../evidence/restic-locks-20261124T082746005710Z/conformance.json) labels them. [Bend](Locks.bend) compares 19 compatibility/removal/refinement decisions, including two explicitly source/proposal controls. Twelve Lean laws and four Bend laws retain the relevant distinctions. Three invalid research inputs are refused.

The [owner-local replay](locks_conformance.py) checks frozen producers, selected source hashes, public and private stream identities, deterministic redaction, lock metadata, statuses, the explicit wait marker, repository-copy preservation, and final readable data. It launches only Lean and Bend:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/restic/locks_conformance.py applications/evidence/restic-locks-20261124T082746005710Z applications/evidence/restic-wait-20261124T083844392124Z
```

Compile the models with the pinned formal check first. Full replay requires the ignored private originals and selected source cache. A fresh public checkout can inspect the redacted observations and models but cannot establish equivalence to withheld raw bytes. No plaintext password, key, or original lock user/host field is copied into the public report. Recorded local tool and capture paths remain for provenance. The official binary matches its recorded publisher checksum; this is not a reproducible source/binary build proof.

## Preserve recovery; improve owner-probe classification

Preserve compatible append locks, exclusive maintenance, normal stale removal, and retry semantics. Do not automatically equate stopped, interrupted, retired, stale, and removed. A dead owner can leave valid recovery evidence. That record blocks maintenance until normal cleanup removes it; it does not imply repository corruption. The tested full data check and dump passed afterward. Force-all unlock was not used.

The Unix source raises a correctness concern: a negative signal result can classify a non-expired same-host record as stale without establishing that its creator is gone. No permission-denied or PID-reuse incident was reproduced, and supported deployment assumptions still need review. A focused internal candidate is a non-intrusive process probe that distinguishes reachable, confirmed absent, permission denied, and unknown. Prefer preserving a record on observation failure instead of silently interpreting every signal error as absence. Removing SIGHUP probing could also remove that dependency on an application-specific ignored signal. Preserve the age policy as a separate decision. The models' `candidateStale` rule preserves a non-expired unknown owner; it is proposed behavior, not a patch or a native permission/PID-reuse finding.

Review Unix/Windows process APIs, mixed-user access, older clients, hostname identity, reboot, clock changes, and optional creator-lifetime evidence before adopting that candidate. Keep lock encodings compatible unless an actual schema change is selected. More lifetime metadata alone would not change older clients' probes. No unrelated process should be signaled to manufacture a test. The keep-current alternative is to retain documented same-user restic ownership assumptions and normal age/cleanup behavior, with better diagnostics and boundary tests; it does not establish arbitrary process identity.

An optional cleanup result could identify removed, retained-live, unreadable, and unknown records, plus whether force was requested. In the live case, success with no removal currently gives little feedback; a report should not imply that “unlock succeeded” means “the repository has no active locks.” Reuse existing removal callbacks and retry/reporting paths before adding another service. Preserve current exit codes and keep any new machine fields opt-in and stable.

Before broader qualification, test permission failures with a safe controlled adapter, malformed/unreadable and zero-sized published records, refresh failure and long standby, remote consistency, multiple cleanup owners, interrupted pack/snapshot publication, nonempty stdin cancellation, actual partial-source failures, and cross-platform process semantics. Preserve unknown outcomes and original recovery objects. For empack and the shared host contracts, the useful rule is the same: publication, admitted ownership, process observation, retirement, and cleanup each need their own evidence and resource scope.
