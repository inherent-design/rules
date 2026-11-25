# Shader and post-effect definitions

Shader declarations, source text, include resources, pipeline descriptors, compilation, publication, draw submission, and final native retirement change independently across the five selected Java releases. This is source and asset linework. No shader compiler, graphics device, game, provider, or post-effect execution was started.

The [shared ledger](text-shader-sources.json) binds original classes, private inspection views, type-scoped field clauses, built-in JSON structure, and selected direct invoke facts. Source hashes and structural JSON inspection are not original parser acceptance or rendering evidence. The original assets, code, binaries, mappings, native libraries, and views remain private. Associated field clauses are locators; delegated codecs, native ABI, and complete consumer/effect closure remain open.

## Versioned definition paths

| Selected release | Program and stage path | Post-effect contract |
| --- | --- | --- |
| 1.21.1 | ShaderInstance and EffectInstance consume legacy JSON declarations and vertex/fragment sources. Includes, uniforms, attributes, samplers, and actual bindings have separate consumers. | PostChain manually reads target/pass arrays. Targets can be names or objects with name and dimensions defaulting to screen size. Pass/program, input/output, auxiliary targets and uniforms require their legacy grammar and renderer. |
| 1.21.4 | ShaderManager discovers stage sources and ShaderProgramConfig JSON. Config requires vertex/fragment IDs; samplers, uniforms, and defines have declared empty defaults. | PostChainConfig has optional target map and pass list. Pass names a `program`; inputs and uniform assignments have their own records and validation. |
| 1.21.5 | The selected manager no longer loads the preceding standalone program JSON grammar. Native RenderPipeline descriptors supply the pipeline contract; stage/include files remain resources. | Pass names `vertex_shader` and `fragment_shader`, not the old program field. Uniform declarations add a type and optional bounded value list. |
| 1.21.11 | Native pipeline descriptors, stage/include resources, and separately loaded post effects remain distinct. | Internal targets have optional positive width/height, persistent default false, and clear-color default 0. Uniforms become named blocks containing typed values. |
| 26.3 | ShaderSource separates stage strings and cached native include records. GpuDevice compilation yields pending results with a later finish step. Required/optional pipelines and source/cache owners are explicit. | The selected post schema retains the later target/pass/block shapes. Actual target access, shader layouts, buffers, passes, and backend behavior remain separately versioned. |

Built-in asset inspection confirms shader-directory JSON counts of 71 and 65 in 1.21.1/1.21.4 and zero in the three later selected releases. The later artifacts still contain `post_effect/*.json`: six in 1.21.4/1.21.5/1.21.11 and five in 26.3. Stage/include counts and exact JSON identities are in the ledger. These are artifact facts, not a general claim that later clients or mods cannot consume shader JSON elsewhere. A directory count alone does not establish a grammar or capability removal.

## Fields and composition boundaries

The selected 1.21.4 ShaderProgramConfig declares vertex/fragment identifiers; sampler records with name; and uniform records with name, type, count, and float values. Its count validator differs from simply requiring equal lengths: the source rejects mismatched lists only when their length exceeds one. Type/count/storage and native binding behavior still need their consumers; do not invent a positive-count or complete layout guarantee from those fields. Defines have a separate declaration and merge path.

Legacy ShaderInstance sampler parsing reads a name and tests whether `file` is a string. That selected method does not itself load the named texture; actual sampler binding belongs to a caller. Treating every declared file-like string as an asset load would misdescribe effects and dependencies. Likewise, uniform parsing and GLSL/driver validation are distinct stages.

In 1.21.4/1.21.5 the post target union includes fixed dimensions and a fullscreen alternative. The fixed record declares positive width/height, but the composed either/unit codec has its own fallback behavior. This source band does not establish that every malformed dimension object is refused by the whole union. The later optional-dimension record is a different contract. Missing fields, explicit invalid fields, unit/fallback branches, and resize-time dimensions need direct decoder/consumer comparisons.

Post pass input codecs use a texture/target alternative. Texture input declares sampler name, location, positive dimensions, and bilinear default false. Target input declares sampler name, target ID, depth-buffer flag and bilinear flag, both default false. Repeated sampler names are rejected by the inspected pass validation. The xor composition and delegated identifier/codecs need their own admission evidence; a field list is not an unknown-field or ambiguity policy.

Later uniform blocks use `UniformValue` dispatch with a value field. The selected types are int, ivec3, float, vec2, vec3, vec4, and matrix4x4. Each delegates to its scalar/vector/matrix codec and writes through the corresponding Std140 builder operation. This is not a proof of all codec edge cases, GPU layout limits, shader ABI equivalence, or faithful conversion from the old named-uniform list.

Target references are also scoped. The selected `isPostEffectValid` method explicitly compares externally referenced targets with an allowed-target set, and post-chain construction receives that set. Validation is separate from cache lookup: the inspected cache keys chains by effect ID and can return an existing chain. Actual callers must establish the context/reuse contract; an eligibility method or parameter does not prove a fresh check on every cache hit. This render-target capability is different from filesystem permissions, pack selection, or a general authorization grant. Actual texture/buffer ownership and pass execution still need native evidence.

## Source loading has effects before publication

The selected 26.3 reload path loads configs asynchronously, starts required and optional pipeline compilation, schedules pending-result finalization on the supplied reload executor, crosses the preparation barrier, and applies the completed results. The barrier does not imply that preceding work was free of native allocation or device effects. Executor names also do not by themselves prove thread/context authority.

ShaderSource.CachedIncludeSource creation allocates a native shaderc include-result record and UTF-8 name/content buffers. Its close frees those native allocations. Existing original Class-File API facts independently identify the selected allocation/free calls; the ledger binds their class hashes and direct invokes. They are static instructions, not observations that allocation/free succeeded.

GlslCompiler owns reusable missing/malformed-include records and its compiler pool. A normal include lookup borrows the cached record from ShaderSource; its per-include release callback is empty. Cached records therefore have a different owner from compiler-result/options/source buffers and the returned intermediate module. The inspected compile path has specific cleanup/finally blocks, but all allocation faults, exceptional futures, cancellation, and backend consumers remain unqualified. No leak or race is alleged from this partial chain.

PipelineCache retains ShaderSource. Clearing the cache closes its compiled entries and clears that map; closing also closes the source afterward. PostChainCache closes cached chains rather than owning include disposal. Calls can fail partway, so return from a different cleanup action or loss of one reference cannot substitute for the relevant acknowledgement. The source getters do not independently prove that represented native addresses are still valid after their owner closes.

Normal required-pipeline failure has an inspected cleanup path; optional failures are reported separately. Successful apply replaces post-chain and current-pipeline cache owners, then closes the old cache. Exceptional completion before apply, partial cleanup, retained readers, future lazy compilation, context loss, and submitted GPU uses need their own obligations. Compile completion and finishing a pending object are not GPU draw completion or retirement of every resource owner.

## Cross-version fidelity and host requirements

A JSON migration, shader-source conversion, runtime pipeline adapter, and new graphics implementation are distinct proposals. A converter must account for paths/includes, defines, stages, vertex format, uniform/block layouts, samplers, target capabilities, resize/persistence/clear semantics, pass order, error/recovery policy, and actual backend features. Renaming fields or reproducing a plausible image is insufficient.

The selected clients declare Java 21 or Java 25 as appropriate. The 26.3 native include path uses LWJGL/shaderc allocation; it is not established by the separate Java Arena witness. Windows/Win32, Darwin, GNU/Linux, selected native libraries, device/driver/backend, thread/context affinity, and runtime capability remain independent profile axes. Static OpenGL/Vulkan/RenderPearl call sites do not establish which backend is active or supported on a particular host. No new all-platform native result is claimed here.

Modefite, Polytone, Compat, custom shader providers, and external renderers need actual injection/registration/configuration/coexistence contracts. Their model/definition capabilities do not imply shader support, and the selected vanilla paths do not exclude independent mod paths. Bedrock is an independent edition lane; its material/effect formats and consumers are not aliases of Java program JSON or native pipeline descriptors.

## Independently selectable design work

- Keep a current renderer/profile when it supplies the required semantics. Select restricted conversion only after naming preserved inputs and observable losses.
- A possible provider can validate complete definitions and resource dependencies before publishing a generation. Native source buffers, compilation jobs, compiled objects, post-chain targets, and submitted uses still need distinct leases and cleanup owners.
- Report the failed stage: resource/include lookup, schema, shader compile, pipeline finish, target admission, binding, pass execution, or device failure. Preserve the prior usable generation or explicitly report partial/uncertain effects before suggesting a retry. Do not call a successful parse “shader applied.”
- A versioned adapter can expose exact backend/layout/context requirements and refuse unsupported cases. Missing old gameplay/context data or a native graphics capability must not be replaced by invented defaults.
- A fuller qualification plan needs native decode, compile/link/layout, controlled draw output, failure/cancellation/context loss, generation handoff, and final retirement on the selected hosts/providers. This source band does not implement or satisfy those tests.

No shader/native backend implementation, mod install, pack mutation, or rollout was selected. These field and owner contracts remain part of the unfinished wider research intent.
