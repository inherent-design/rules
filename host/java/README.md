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

## Runtime declarations and actual consumers

The [Minecraft target graph](../minecraft/TARGETS.md) separately records Java 21 requirements through 1.21.11 and Java 25 for 26.3. Its artifact-version model checks the declared major prerequisite only. The arena witness expands the host API overlay; it is not evidence that Minecraft calls `Arena`. Static direct calls, library dependencies, runtime execution, and native/backend qualification have separate evidence states.

The separate [ordered array-search contract](ARRAY-SEARCH.md) is documented for Java 17, 21, and 25 and consumed by the original Minecraft 1.21.4 range helper. Its duplicate-choice permissions are weaker than a stable-index prediction. It does not extend FFM or other native qualification.

The [CodecUI comparison](../minecraft/POLYTONE-CONTRACTS.md) separates bundled-library declarations, actual selected class-path bytes, schema hints, decoder admission, and re-encoding. It observes authored callers on Java 21/macOS; it does not qualify a Java 17 runtime for those class files, native JarJar negotiation, or the library on every host. A version declaration or UI schema is not a substitute for the effective consumer contract.

The [class-lookup contract](CLASS-INITIALIZATION.md) is shared across the 17 baseline and 21/25 overlays, with 57 authored native observations on the three pinned macOS JDK builds. A class descriptor, target initialization, loader effects, and application compatibility are different facts. Original Polytone bytecode confirms the consuming default lookup call; no provider class was executed. Native Windows/Linux lookup qualification remains pending.
