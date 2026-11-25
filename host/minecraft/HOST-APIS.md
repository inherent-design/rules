# Minecraft 26.3 host API discovery

[host-api-26.3.json](host-api-26.3.json) records a static scan of the original selected client. Java 25's stable [Class-File API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/classfile/ClassFile.html) read class files as data. The scanner never defined, initialized, linked, or invoked game classes. The original JAR and all external native libraries remain private and were not installed or loaded.

The scan traversed 11,383 class entries and 98,739 methods. Every class header was version 69.0; no class in this client declares the preview minor 65535. It found 12,593 direct invocation instructions across eleven selected host/middleware/graphics families, plus 32,235 `invokedynamic` instructions whose targets are not resolved by this census. Counts include constructors, accessors, and exception construction; they are not counts of side effects.

| Static family | Selected instructions | Next consumer contract |
| --- | --- | --- |
| Filesystem/streams | 1,705 | Paths, providers, opening/closing, replacement, partial read/write, resource-pack lifetime. |
| Java network | 307 | URI interpretation, downloads, local/server sockets, interruption, acknowledgement. |
| Netty | 868 | Event-loop ownership, framing, channels, cancellation, shutdown/retirement. |
| Work/scopes | 1,388 | Futures, threads, atomics, locks, publication, timeout vs actual retirement. |
| Process/runtime | 183 | Runtime queries, process identity, exit, library loading, shutdown hooks. |
| Desktop | 74 | Actual dialog/server UI context, display availability, interaction and closure. |
| Reflection/loading | 136 | Dynamic lookup and linkage; unresolved dispatch needs separate witnesses. |
| Security/crypto | 54 | Signed/hashed input identities and cryptographic API outcomes; no crypto proof inferred. |
| JNA/OSHI | 63 | Native platform identity and resource queries; platform access/availability remains pending. |
| LWJGL | 2,278 | Native allocation, SDL input/windowing, audio, fonts, image codecs, shader compilation, OpenGL/Vulkan. |
| RenderPearl | 5,537 | Device/backend, command encoder, pipelines, submission, GPU/native resource retirement. |

The symbolic owner/name/descriptor of each direct invocation is retained, with its caller method and instruction-element ordinal. Virtual dispatch can execute a different overriding implementation. Reflection, dynamic invocation targets, external Java dependencies, callbacks, native libraries, drivers, and runtime reachability are not resolved. [InvokeInstruction's contract](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/classfile/instruction/InvokeInstruction.html) identifies this static instruction boundary.

## Concrete graphics boundaries

The JAR contains 249 RenderPearl classes, including `GpuDevice`, OpenGL and Vulkan backends, and a frontend device. ShaderC calls use `org.lwjgl.util.shaderc`, not a guessed `org.lwjgl.shaderc` package. Direct SDL calls occur in `Window`, `SDLEventHandler`, `TextInputManager`, and device/backend code. The 249 SDL invocation instructions are concrete discovery evidence; there are no direct GLFW invocations in this selected JAR. That absence does not rule out other dependencies or runtime-loaded integrations.

The launcher metadata declares LWJGL 3.4.3 modules, including SDL, ShaderC, SPVC, VMA, and Vulkan, plus the selected FreeType build. [The map](host-api-26.3.json) preserves all library coordinates, download identities, and original platform rule predicates. It does not evaluate those rules as a guarantee that a library loads on a host. For example, Vulkan's declared macOS native artifacts do not qualify a Vulkan backend, driver, translation layer, or deployment.

No direct FFM or Unsafe invocation was observed in this client. That is a scoped absence, not proof about external dependencies, reflection, or native code. The separate [arena witness](../java/README.md) is a host contract, not a claim that this game uses FFM. GPU submission completion, retained consumers, native memory release, and physical memory usage still require their own contracts and observations.

## Evidence and replay

The [receipt](evidence/host-api-26.3-20261125T044400945429Z/receipt.json) binds the client, frozen scanner sources, JDK/tool identities, generated scanner class, raw output, and terminated owned process groups. [Compressed facts](evidence/host-api-26.3-20261125T044400945429Z/invoke-facts.jsonl.gz) contain authored metadata records, not original class files or executable method bodies. The earlier seven-family scan remains owner-local; this final eleven-family census supersedes its discovery counts without replacing native evidence.

`host_api_replay.py` checks retained-byte identities, caller references, counts, class versions, and the aggregate map without Java or a game. It is a census/integrity check, not semantic conformance or a Lean/Bend model of the listed APIs. API laws, provider adaptation, backend failure, reload, and actual user-facing effects remain the next breadth-first work.
