# Signed 32-bit arithmetic

Java 17 is the baseline; Java 21 and Java 25 retain the same selected integer contract. [Word32.lean](Word32.lean) and [Word32.bend](Word32.bend) represent an `int` by its 32 bits and interpret the high bit separately from positivity. Addition and subtraction wrap modulo 2³². A nonzero word is not necessarily a valid positive bound.

The [pure comparison](word32_conformance.py) matches ten authored runtime operand pairs on each of the three pinned macOS arm64 JDKs: 30 observations, eight Lean laws, six Bend laws, five research-decoder refusals, and four changed-observation controls. The [receipt](evidence/word32-conformance.json) binds sources, raw channels, JDK release identities, and actual process-group retirement. The collector uses explicit JDKs, `--release 17`, bounded heaps, and two available processors. No Gradle daemon is involved.

The Java language contract specifies integer overflow without an overflow indication. See the versioned [Java 17 language specification](https://docs.oracle.com/javase/specs/jls/se17/html/jls-4.html#jls-4.2.2). The native 21/25 observations qualify these exact JDK builds and cases; they are not a proof of a JVM implementation or native Windows/Linux behavior.

This host rule is consumed by the [Minecraft sound study](../minecraft/SOUNDS.md). Individually positive weights can produce a negative, zero, or positive wrapped aggregate. A caller that needs a bounded positive total must establish that property over the aggregate, rather than infer it from the entries. A checked/wider accumulator would be a separate application policy with compatibility and failure behavior to specify.

The [GUI scaling comparison](../minecraft/PRESENTATION.md) independently exercises original codecs in five Java targets. Nonnegative border fields can wrap during a center-size guard and be accepted where unbounded natural addition would refuse. The actual drawing path then applies different destination clamping. Preserve the arithmetic, admission, layout, and rendering contracts separately; this codec observation does not establish a rendered defect or qualify a new host platform.

The model excludes arbitrary JSON conversion, multiplication, floating-point arithmetic, checked arithmetic, random-number algorithms, concurrency, and native allocation. The processes perform incidental JVM, stream, and native work; the observations do not assert a process-wide absence of JNI or other effects. No Minecraft client or audio device is started by this primitive fixture.

After compiling the models with `scripts/check-rules.py`, run `python3 host/java/word32_conformance.py`. This replays retained evidence and executable models; it does not launch Java. Owner-run collection is `word32_probe.py --help` and requires an explicitly selected existing JDK.
