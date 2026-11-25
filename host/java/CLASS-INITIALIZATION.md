# Class lookup, initialization, and effects

A returned `Class` descriptor, initialization of that class, its loader's effects, and application compatibility are separate facts. The shared [Lean](ClassInit.lean) and [Bend](ClassInit.bend) contracts model a serial authored fixture on the Java 17 baseline and Java 21/25 overlays. They do not model arbitrary class loaders, concurrent/recursive initialization, module policy, class unloading, or every linkage/VM failure.

## Documented API and actual caller

The one-argument `Class.forName(String)` requests initialization through the calling class's defining loader. The explicit overload accepts an initialization flag and loader. An array-class lookup does not initialize its component class. These distinctions are documented for [Java 17](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Class.html#forName(java.lang.String)), [Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Class.html#forName(java.lang.String,boolean,java.lang.ClassLoader)), and [Java 25](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Class.html#forName(java.lang.String,boolean,java.lang.ClassLoader)). The selected observations below test a finite part of those contracts.

An original Polytone GUI-manager [instruction scan](../minecraft/evidence/polytone-class-target-invoke-20261125T111850323262Z/receipt.json) confirms one `INVOKESTATIC java/lang/Class.forName(Ljava/lang/String;)Ljava/lang/Class;` inside `parseWithLevel`. That scan parses unchanged provider bytecode as data using the previously frozen Java 25 class-file scanner. It never defines or initializes a provider class. Source inspection connects the call to general class-name targets in GUI definitions and a local `ClassNotFoundException` catch. Actual pack/UI reachability, loader policy, target compatibility, and provider failure handling remain unqualified.

## Retained native boundary

Each pinned Temurin build compiled the same authored source with `--release 17`, then ran 19 serial calls in its own JVM. All generated class files have header 61.0. Their compiler bytes need not be identical. The three profiles are macOS 26.7.1 arm64, with the actual kernel/build and executable/release identities retained in their receipts:

| Overlay | Actual runtime | Native receipt |
| --- | --- | --- |
| Java 17 | `17.0.21.1+2` | [19 calls](evidence/class-init-17-20261125T110836234813Z/receipt.json) |
| Java 21 | `21.0.13.1+2-LTS` | [19 calls](evidence/class-init-21-20261125T110911696411Z/receipt.json) |
| Java 25 | `25.0.4.1+1-LTS` | [19 calls](evidence/class-init-25-20261125T110912140164Z/receipt.json) |

The fixture uses only its authored classes and standard Java APIs. Initializers increment owned in-memory counters; two deliberately fail after incrementing. Two controlled child-first loaders count `findClass` attempts and read owned compiled fixture bytes. No game, provider, GUI, account, world, native plugin, or external service is selected or executed. Compilation and evidence collection write private fixture files, so the study makes no host-wide “no effects” claim.

| Operation | Observed distinction |
| --- | --- |
| Class literal or explicit `initialize=false` before initialization | Descriptor returned without running that target initializer. |
| Default `forName` | Initializer runs; repeating initialization in the same loader does not rerun it. |
| Same binary name in two controlled loaders | Different `Class` references and separate initialization effects. A name alone is not class identity. |
| Non-initializing lookup through a controlled loader | The loader still executes and changes its counter. Skipping the target initializer does not make lookup pure. |
| Missing target through that loader | `ClassNotFoundException`, with the loader-attempt effect retained. Refusal does not imply no effects. |
| Initializer throws `IllegalStateException` | Initial counter effect survives; caller receives `ExceptionInInitializerError`. |
| Retry initialization of that erroneous class | `NoClassDefFoundError`, without rerunning the initializer. |
| Non-initializing lookup after initializer failure | Descriptor can still be returned; it does not repair the initialization state. |
| Initializer throws an `AssertionError` | That error is propagated rather than wrapped in `ExceptionInInitializerError`; retry still refuses without rerunning. |
| Array literal/default array lookup | Component initialization is deferred until the separate component-class request. |

These failure transitions agree with the detailed initialization procedures in the [Java 17](https://docs.oracle.com/javase/specs/jls/se17/html/jls-12.html#jls-12.4.2), [21](https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html#jls-12.4.2), and [25](https://docs.oracle.com/javase/specs/jls/se25/html/jls-12.html#jls-12.4.2) language specifications. The fixture observes completed serial calls; it does not inspect private JVM initialization flags or exercise allocation failure, superclass failure, reentrancy, initialization locks, or a concurrent waiter.

## Model, projection, and checks

The model keeps disposition per selected `(loader, target)` and distinguishes initializer counters from controlled-loader counters. Descriptor keys include loader, target, and array form. Numeric class identities are first-seen observer labels of actual `Class` reference equality, not persistent handles or authority. The initialization decision is shared across the three overlays; JDK/runtime identities remain separate evidence.

Twenty-two Lean laws and fourteen Bend laws distinguish descriptor lookup, initialization, retained effects, error categories, and loader-scoped identity. The [comparison receipt](evidence/class-init-conformance.json) records 57 matching outcomes, including before/after continuity, six effect counters, class identity/loader labels, returned descriptors, and the two measured catch classifications. Eleven unsupported DTOs and seven malformed observations refuse; ten changed-observation interpretations contradict both model traces. Diagnostic causes and runtime `Class`/`ClassLoader` byte hashes are retained but not predicted.

The source consumer's `ClassNotFoundException` catch and the shared reloader's `Exception` catches cannot be treated as handling every initialization/linkage failure. That is a documented type distinction plus a statically confirmed caller, not an observed Polytone failure or whole-game crash claim.

After compiling the formal modules:

```sh
python3 host/java/class_init_conformance.py
```

Ordinary CI runs this retained comparison without Java. Native collection remains owner-run:

```sh
python3 host/java/class_init_probe.py --jdk /path/to/selected/jdk --private .build/java-class-init
```

The collector freezes its source and helper, records actual commands/JDK/host/class identities, and checks process-group retirement. The three compiler and three execution groups exited. The separate original-instruction scan reused a verified scanner binary, ran one JVM, and also retired. Small heap/CPU settings do not measure RSS, bound host-wide concurrency, or prove global reclamation. Native Windows and GNU/Linux comparisons remain pending.

## Design and UX implications

A proposed class-target resolver can perform explicit non-initializing lookup when it needs only identity, then validate the expected target relation and owning loader before indexing the result. This changes observable behavior from the current default overload, so it is a separately selectable design change, not a faithful preservation claim. A custom loader can still execute; this proposal is not a sandbox or complete effect-admission mechanism.

Keep the current behavior with an explicit contract when initialization is intentional. In either alternative, distinguish “class not found,” linkage/initialization failure, target-type incompatibility, and unavailable application context. Preserve the affected definition and partial changes, and avoid retry advice that assumes a failed initializer can simply rerun in the same loader. A different loader, a restarted process, or an implementation repair is a different operation requiring its own ownership and qualification. No production change or automatic retry is selected here.
