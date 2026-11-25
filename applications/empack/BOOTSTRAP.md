# Exact engine bootstrap and delegated lifetime

This band compares the retained packaged JAR with selected CLI, cache, argument, and lifetime boundaries. It changes no production implementation. The [source ledger](../sources/empack-bootstrap-selections.json) pins 12 inspected files at `0b4462e3032b4f09230b15329722eabefb7f574c`. The [capture receipt](../evidence/empack-bootstrap-20261125T072046883468Z/receipt.json) and [comparison](../evidence/empack-bootstrap-conformance.json) preserve the actual evidence and limits.

## Artifact and host

The reused JAR is 3,109,006 bytes, SHA-256 `8feefc756fa96b0f16e1e91a7d4bcc566c3d19cf02a655fae90b8ea6b2df7d40`. Its retained build manifest matches all 13 recorded source/configuration identities at the source revision above. Its 18 bootstrap base classes have class-file major 52. That target is not evidence of execution on Java 8, nor a proof that the build or all dependencies are reproducible. The JAR identifies its own build as `0.0.0-dev`; that is separate from the exact native engine version it requests.

The JAR was copied once into ignored private work. No Maven, Rust, or product build ran. Most cases used an owned Python-script engine with exact probe responses, argument/event recording, and a compatible loopback cancellation peer. It is not native empack, a game, or a runtime-ownership implementation. Four separate cases delegated to the unchanged installed empack 0.8.8-beta binary, SHA-256 `99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f`, using a copied fictional project for read-only `check --json`.

Collection comprised 29 JAR commands and two separate native display probes. Preparation also recorded three `java -version` results. All owned command groups retired. The captured fixture occupies about 3.6 MiB, including the single private JAR copy. All cache, home, project, and tool records belonged to this fixture; no installed user cache, personal account, launcher, game, or global engine changed. Every bootstrap command was offline. The authored cache records are private fixture inputs, not authenticated official download metadata.

## Observed distinctions

| Boundary | Observation |
| --- | --- |
| UTF-8 static record plus appended arguments | The child receives the exact strings, including spaces and `Ω 日本`, in the distribution base directory. The record remains unchanged. |
| Record refuses appended arguments | Exit 2 before any engine probe. |
| Unsupported/duplicate fields, unsupported schema, malformed UTF-8 | Exit 1 before an engine probe. Diagnostics do not echo record contents. |
| Non-ASCII record filename or symlinked record | Refused before engine execution. This does not qualify every path alias or race. |
| Exact version spelling | A `v` prefix, range, build metadata, and a leading-zero numeric prerelease are refused with exit 2 in the selected controls. |
| Explicit engine | Version/protocol mismatch refuses that selection; it does not fall back to cache. Explicit development policy admits the fixture's `0.0.0-dev` response. |
| Matching engine beside the JAR | Used without opening cache. The version preflight and subsequent exact engine/protocol probes are distinct calls. |
| Wrong-version engine beside the JAR | Warning retained; an admitted cached engine is used instead. |
| Warm private cache | The selected executable is verified and delegated. Writer coordination can be created even on a cache hit. |
| Corrupt cached executable, wrong target, or empty offline cache | No delegation. Cache directories/coordination can change despite refusal. Offline is an acquisition policy, not a no-write preview. |
| Wrong first cancellation peer | Refused; the later correct peer authenticates and completes. No connection nonce is recorded. |
| Cancel Java after child authentication | The fixture receives the explicit cancellation byte. Its result 7 remains the JAR result, rather than becoming generic interruption. |
| Kill Java after child authentication | Parent result is signal 9, represented by subprocess status -9. The separate fixture observes EOF and exits 6. This is not a Java cleanup receipt. |
| Real native `check --json` | Java 17.0.21.1, 21.0.12.1, and 25.0.5.1 pass on macOS arm64. Java 25 also passes under `C`, with the static UTF-8 input and Unicode project path. Measured source/cache/home scopes remain unchanged. |

Probe subprocesses do not inherit the deliberately invalid fixture `EMPACK_BOOTSTRAP_CONTROL` value. Delegation gets a new per-invocation control connection. In the selected source, that connection carries cancellation/lifetime input, not argument transport. The JVM still passes native argv to the child; the record avoids the initial external argv boundary for static strings. These results do not establish arbitrary Unicode argv support across JVMs, operating systems, or locales.

The engine owns preparation, installation, runtime containment, terminal restoration, and recovery. Bootstrap source waits for the delegated process result; that does not itself prove descendant retirement. The script fixtures supply only the explicitly observed child behavior. The native checks do not launch Java/game processes.

## Models and comparisons

[Lean](Bootstrap.lean) has 12 laws and [Bend](Bootstrap.bend) has 11. Both compare all 29 JAR cases. Six DTO refusals, six changed input premises, and four changed native-observation controls protect the comparison. The two display probes establish the native version/protocol inputs separately. The projection reads the original static files, duplicate-preserving JSON, authored cache metadata and executable hashes, actual child events, native JSON output, and independent before/after images. Original child JSONL logs are exported byte-for-byte; their ignored private originals remain available. It does not derive expected results from the models.

These are closed profiles. Boolean admissions are not general JSON/SemVer/ACL parsers, and opaque equality is not a cryptographic proof. The parent-loss law deliberately describes this controlled fixture's EOF result 6, not every native operation's exit policy. Ordinary cache coordination, selected executable, delegated execution, returned child result, and observed parent result remain separate facts. The modeled finish branch assumes successful control finalization. In the inspected source, a later cancellation/connection cleanup exception instead retains the completed native status in its diagnostic and reaches the bootstrap error classifier. Those failure paths were not injected here; preserving a child fact does not always mean returning that child’s numeric status.

The collector was amended before its first collection to correct explanatory text and retire any surviving owned fixture descendants after failure. The original preparation producer and exact amendment hashes remain retained. No native collection failed or was silently repeated.

## Design and interface consequences

Preserve strict explicit selection versus automatic local fallback. They express different user intent. A caller can request an exact local executable without consenting to another cached binary, while an automatically discovered candidate can be rejected before ordinary resolution continues.

Keep selected version, actual executable identity, capability response, acquisition provenance, and live process ownership separate. A version probe is a self-report by already selected local code. The release/channel's minimum engine compatibility is another native check, not permission to change the bootstrap's requested version.

Expose scoped effects independently of success. A cache miss or invalid ready object can leave coordination state without changing project content. This matches the broader [exit-versus-effects rule](../COMPARISON.md); reports should not equate refusal with “nothing ran” or “no files changed.” Existing corruption diagnostics name the cache path to inspect. Preserve that useful precision.

Treat a stop request, connection loss, returned child status, and parent death as different events. A portable application interface should retain the actual terminal outcome and any cleanup uncertainty. It should not infer success from signal delivery, or infer child death from loss of a Java/UI parent.

Keep dynamic runtime credentials out of persisted static invocation records. Preserve exact literal arguments, explicit append policy, strict record capture, and redacted parser errors. Broader security claims require their own race, resource-bound, and native command-authorization qualification.

## Remaining qualification

Bootstrap and process-console parent operations remain pending. This band does not qualify official HTTPS/catalog acquisition, archive extraction, cold download publication, cache contention or interruption/recovery, metadata tampering races, probe timeout/output bounds, disconnect during native mutation, real runtime retirement, terminal transfer, or generated Prism/server commands. Native Java 8, Windows/Linux, other `C` combinations, nondefault filesystems, ACLs, and external arbitrary Unicode argv remain open.

Replay without launching a JVM or empack:

```sh
LEAN=/path/to/lean BEND=/path/to/bend python3 applications/empack/bootstrap_conformance.py applications/evidence/empack-bootstrap-20261125T072046883468Z
```

The one-shot collection is complete. New native scenarios require separate provenance; do not rerun it over the existing capture.
