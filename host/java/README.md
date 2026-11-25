# Java host overlays

Java 17 is the shared baseline, with Java 21 and Java 25 overlays. An overlay qualifies selected APIs on a named JDK and host. It does not qualify every Java feature or an application merely because its declared runtime requirement is satisfied. Java 18 is not a reference target.

The original `check` procedure compiles and runs the file, terminal, loopback, cancellation, virtual-thread, and scoped-value witnesses described in [profiles](../../profiles/README.md). Those observations retain their original platform and API limits. Windows runtime comparisons remain pending.

## Java 25 native-memory scopes

[ArenaAccess.lean](ArenaAccess.lean) and [ArenaAccess.bend](ArenaAccess.bend) describe read, write, and close admission for one valid aligned long segment. A confined arena permits its creating Java thread; a shared arena admits other Java threads. Closing the arena revokes subsequent modeled access. A wrong-thread close refuses and preserves the open scope.

The [retained witness](evidence/java25-arena-20261125T043213057721Z/receipt.json) used Temurin 25.0.4.1+1-LTS on macOS 26.7.1, arm64. Eleven operations distinguish wrong-thread refusal, successful close, repeated close, and reads after close. A joined worker writes the shared segment, followed by an owner read; a later joined worker closes it. Both executable models match the captured outcomes, scope states, and returned values. [Comparison receipt](evidence/arena-conformance.json).

`historicalValue` records the last fixture value; it is not readable memory after closure. The model retains both closed-scope and wrong-thread reasons when both apply, without predicting which exception a JVM checks first. That combination is model-only here. There is no simultaneous read/close race in the native witness.

The [Arena API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/foreign/Arena.html) has been stable since Java 22. This Java 25 witness uses no preview flags. The probe does not establish availability on the Java 17 baseline or qualify the preview API on Java 21. An arena's owner thread is not an application principal, and shared access supplies no application authorization or synchronization. Scope invalidation does not measure physical RAM reclamation, establish GPU completion, or qualify escaped raw pointers, JNI, or foreign calls.

Run the pure comparison after `scripts/check-rules.py` has compiled the model:

```sh
python3 host/java/arena_conformance.py
```

The owner-run collector is separate from ordinary CI. Select an actual JDK 25 explicitly; the shell's default Java can be another release:

```sh
python3 host/java/arena_probe.py --jdk /path/to/jdk25 --private .build/java25
```

The collector freezes its sources, records the JDK release and executable hashes, compiles with `--release 25`, and retains raw channels and child-group retirement. `export_arena.py` exports authored sources and observation bytes, while retaining exact local command paths privately. No Minecraft or other application is started.

## Filesystem identity

The [filesystem comparison](../filesystem/README.md) separately observes 15 standard-library calls on Java 17, 21, and 25. Equal missing Paths can produce a true `Files.isSameFile` result while attribute reads report absence. Preserve API/provider provenance and object-existence evidence; this library Boolean is not a universal native identity witness or mutation grant. The fixture does not start an application or daemon and remains outside ordinary CI.

## Signed arithmetic

The [32-bit word contract](WORD32.md) compares 30 authored runtime operations across Java 17, 21, and 25. It distinguishes positive operands from a positive wrapped aggregate and is consumed by the selected Minecraft sound controls. Numeric decoding, random algorithms, JVM correctness, and native Windows/Linux execution are separate qualifications.

## Runtime declarations and actual consumers

The [Minecraft target graph](../minecraft/TARGETS.md) separately records Java 21 requirements through 1.21.11 and Java 25 for 26.3. Its artifact-version model checks the declared major prerequisite only. The arena witness expands the host API overlay; it is not evidence that Minecraft calls `Arena`. Static direct calls, library dependencies, runtime execution, and native/backend qualification have separate evidence states.

The separate [ordered array-search contract](ARRAY-SEARCH.md) is documented for Java 17, 21, and 25 and consumed by the original Minecraft 1.21.4 range helper. Its duplicate-choice permissions are weaker than a stable-index prediction. It does not extend FFM or other native qualification.

The [selected float-order contract](FLOAT-ORDER.md) adds signed zero, one NaN class, total order versus numeric comparison, and exact scaling by plus or minus one. It is consumed by the original Compat item-program comparison on Java 21/macOS. Java 17/21/25 API references are separate from native qualification; this is not general IEEE arithmetic or a replacement for the narrower array-search contract.

The [CodecUI comparison](../minecraft/POLYTONE-CONTRACTS.md) separates bundled-library declarations, actual selected class-path bytes, schema hints, decoder admission, and re-encoding. It observes authored callers on Java 21/macOS; it does not qualify a Java 17 runtime for those class files, native JarJar negotiation, or the library on every host. A version declaration or UI schema is not a substitute for the effective consumer contract.

The [provider policy and geometry comparison](../minecraft/PROVIDERS.md) adds 87 selected original entrypoint calls on the pinned Java 21/macOS profile. Explicit dependency metadata and test libraries qualify the isolated calls only. They do not establish actual FML selection, transformed classes, configuration-file effects, whole startup, Java 17 availability, Java 25 behavior, or native Windows/Linux execution. Preserve no-op, refusal, missing, and eligible outcomes separately; emitted matrices do not qualify a graphics backend. The generic host baseline and other overlays remain unchanged.

The [class-lookup contract](CLASS-INITIALIZATION.md) is shared across the 17 baseline and 21/25 overlays, with 57 authored native observations on the three pinned macOS JDK builds. A class descriptor, target initialization, loader effects, and application compatibility are different facts. Original Polytone bytecode confirms the consuming default lookup call; no provider class was executed. Native Windows/Linux lookup qualification remains pending.

## Managed scopes and library-owned native addresses

The [selected shader source chain](../minecraft/SHADERS.md) identifies LWJGL/shaderc allocations in Minecraft Java Edition 26.3 resource preparation, with separate include-cache, compiler, pending-result, and pipeline-cache owners. Original bytecode confirms the selected allocation/free calls; none was executed by that source inspection. These pointers are outside the Arena witness. Java 25 availability and Arena close checks do not qualify arbitrary native addresses, library callbacks, device completion, or safe post-close access. Keep native library/backend, host, thread/context, generation, and operation retirement as explicit profile obligations.

## Aggregate futures and listener ownership

The [original reload-orchestrator comparison](../minecraft/RELOAD-SCHEDULING.md) observes 108 controlled snapshots across four Java 21 client profiles and the selected Java 25 client. A failed aggregate can coexist with a pending listener future; partial authored application effects can remain after failure. An empty listener set can complete independently of its initial gate. These are selected library/consumer contracts, not a new Java 17 run or a proof of real worker retirement. Direct executors and manual futures make order observable without claiming scheduler latency, cancellation, native completion, or rollback.
