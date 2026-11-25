# Pack detection, filenames, and path context

The five selected original Java clients make the same bounded detection decisions on 16 generated cases each. A regular file's lowercase `.zip` suffix, a directory's regular `pack.mcmeta`, link validation, and the eventual factory result are separate facts. Detection neither opens an archive nor admits its metadata, selects a pack, applies resources, or proves rendering compatibility.

The comparison exposes a conditional path-context problem: after validating a top-level link, the original detector uses `Files.readSymbolicLink`'s returned path directly. A relative target is then interpreted from the process working directory. With an authored allow-all matcher, detection can throw despite an existing parent-relative target, or pass an unrelated working-directory path to the factory. This is original API behavior on controlled inputs, not a demonstrated default Minecraft workflow failure or a security assessment.

## Exact scope and custody

[The capture manifest](pack-detector-captures.json) binds all five selected client identities, normalized public payloads, original private receipts, and measured profiles. Java 1.21.1, 1.21.4, 1.21.5, and 1.21.11 ran on the selected Java 21.0.13.1 installation. The selected 26.3 client ran on Java 25.0.4.1. The recorded host was macOS 26.7.1, aarch64, APFS. These results do not qualify Java 17 client execution, another filesystem, Windows, Linux, or native pack loading.

[PackDetectorProbe.java](PackDetectorProbe.java) invokes original `PackDetector` and `DirectoryValidator` methods. The only overrides are the abstract pack factories, which record their arguments and return a string, return null, or throw an authored `IOException`. No resource-pack archive or pack metadata reader is called. The validator is original; its `PathMatcher` is an authored all/none policy, not the production allowlist. The four original loaded classes per profile are the detector, validator, validator visitor, and forbidden-link record. No game bootstrap, GUI, world, renderer, application build, or provider runs.

[Collection](pack_detector_probe.py) freezes its producers, original names/signatures, fixture recipe, generated subclass, tool/library identities, commands, channels, class-load metadata, input attributes, and before/after images. Compiler heaps are bounded to 128 MiB and observer heaps to 96 MiB, with two processors and one selected profile at a time. All ten successful compiler/JVM groups were terminal and absent. Fixture file/link images and the deliberately different working-directory shadow bytes remain unchanged. This is a measured preservation scope, not a sandbox or whole-host no-I/O claim.

The first fixture placed its unsigned helper in the default package. Java refused to load a signed client class into that same loader/package before any detector call. That zero-call run is preserved and excluded. The corrected helper uses a named package, with its authored subclass in a separate loader. Original JARs and class bytes remain unchanged; Java's original signer checks remain enabled. The observations record signed detector/validator classes, an unsigned adapter, and separate loaders. They establish this fixture arrangement, not a general signature-verification or trust model.

## Detection outcomes

| Input or boundary | Original observed outcome |
| --- | --- |
| Opaque regular `payload.zip` | ZIP factory called; its authored result returned. The bytes are deliberately not a valid archive. |
| Regular `.jar`, uppercase `.ZIP`, or `.txt` spelling | Null result, with no factory call. On this APFS fixture, lowercase and uppercase ZIP spellings name the same observed file key; their lexical suffix decisions still differ. |
| Missing entry | Null result. This differs from an allowed link whose raw target lookup is missing. |
| Directory with regular `pack.mcmeta` | Directory factory called without interpreting metadata bytes. |
| Directory without metadata, or with a metadata directory | Null result after directory validation. |
| Absolute link, matcher allows | ZIP factory receives the absolute target path. |
| Absolute link, matcher denies | One forbidden-link record, one matcher call, no factory call. |
| Directory containing one denied link | One issue, no factory call, even though a regular metadata entry exists. |
| Same directory with its link allowed | Directory factory called after the matcher. |
| Factory returns null | Null result **with** a factory invocation. Null alone does not identify which earlier gate refused. |
| Factory throws | Exception propagates; the recorded factory attempt remains. |

The retained normalized requests, observations, channels, and receipt are under `evidence/pack-detector-<release>-<capture>/`. [The observer/exporter](pack_detector_observations.py) independently rechecks original clients, mappings where applicable, actual tool/library bytes, frozen producers and compiled adapter/helper classes, streams, loaded class identities, and current retained fixture images. Public normalization replaces only each capture's absolute path prefix. Original proprietary classes, exact argv, inputs, and class-load logs remain private.

## Relative targets need an explicit anchor

Two separate generated cases establish the distinction:

1. A link's relative `payload.zip` exists beside the link, while the working directory has no such entry. Validation allows it, then detection throws `NoSuchFileException`; no factory runs.
2. A link's relative `shadow.zip` names one owned payload beside the link. A different owned `shadow.zip` exists in the working directory. Detection returns the ZIP callback result and passes the working-directory path to the callback. Independent retained hashes distinguish the two backings. The fixture records a factory argument, not an actual archive read from that path.

All five clients reproduce both boundaries. The operational conclusion is narrower than “resolve all paths”: retain the operation's path context and bind validation to the same intended object/context used by the consuming factory. An identifier, a raw target string, a callback's successful return, and backing identity are distinct evidence. No detected pack result grants mutation authority.

A proposed parent anchor uses the link's parent when resolving a relative target and preserves absolute-target behavior. In the finite models, it changes exactly ten rows, the two relative examples for each client. Those proposal rows are not native observations of a patch. They do not implement a race-safe resolver, validate production allowlist semantics, follow arbitrary link chains, establish tree containment, or solve reparse/provider differences. A production change also needs caller reachability, factory/open behavior, clear path diagnostics, and stale/changed-target recovery. Keeping current behavior while reporting the exact failed context is a separate option.

## Rules and retained comparison

[PackDetection.lean](PackDetection.lean) has 15 laws; [PackDetection.bend](PackDetection.bend) has ten kernel-checked laws. The state distinguishes file kind, literal suffix, directory metadata and links, raw and parent-relative target bindings, matcher policy, factory policy, return value, exception, issues, and callback invocation. Binding numbers are case-local roles, not persistent filesystem IDs. Directories are limited to zero or one link, callbacks are non-reentrant, and fixture bindings remain quiescent. General I/O errors, concurrent changes, arbitrary trees, and recursive link resolution remain outside this comparison.

[The case inputs](pack-detector-cases.json) come from the frozen fixture recipe, not detector results. Input file attributes, before/after images, and callback argument paths remain separate observations. The decoder requires evidence only for the selected branch: a denied top-level link does not need target attributes, and a directory already refused by link validation does not need metadata or factory-binding facts. Placeholder values in unused model slots do not turn unknown fields into observed absence.

After compiling the model with the pinned toolchain, run only the retained-data comparison:

```sh
LEAN_PATH="$PWD/.build/formal" python3 host/minecraft/pack_detector_conformance.py
```

It compares 80 native outcomes, each with six scoped result fields, through both models. Eleven malformed/unsupported or needed-unknown research packets refuse. Two unneeded-unknown profiles preserve the original outcomes. Four wrong interpretations and four altered raw-observation controls are rejected. Candidate anchoring is checked separately against its ten changed model-only expectations. The checker does not invoke Java, a game, a package manager, or native collection.

This band advances the detector boundary only. [Repository/UI ordering](BREADTH-LINEWORK.md), actual pack opening, metadata/overlays, full validation, resource publication/retirement, provider coexistence, and the wider five-family/host work remain incomplete. A suffix readiness check can inform the application [content-kind study](../../applications/empack/content-kinds/README.md), but it must not silently rename user files or equate structural archive admission with consumer compatibility.
