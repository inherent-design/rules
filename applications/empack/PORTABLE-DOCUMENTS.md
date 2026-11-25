# Shared authoring interpretation

The current `DocumentCodec` and all its submodules compile unchanged for native Rust and browser WASM. Thirty-four controlled requests produce identical output bytes on native macOS arm64, Node WASM, Chromium, and WebKit workers. This advances the portable engine boundary beyond inventory selection: author/bindings interpretation, canonical encoding, inspection, and selected syntax-preserving edits can share the current Rust implementation. Project storage, asset capture, consumer assembly, and the required joined export remain separate.

## Source and build boundary

The [build receipt](../evidence/empack-portable-documents-20261125T102640306478Z/build.json) identifies 28 unchanged source files at `0b4462e3032b4f09230b15329722eabefb7f574c`: the complete core and document module/submodules. The [source ledger](../sources/empack-portable-documents-selections.json) also pins the original Cargo lock. This is an isolated crate facade, not a build of empack's executable, complete engine, or production WASM package. Compiling a module does not exercise every function or its tests.

The only facade substitution is the package behind `reqwest::Url`. Reqwest 0.13.5 re-exports `url::Url`; the study aliases the exact same locked `url` 2.5.8 package as `reqwest`. The unchanged source still calls that parser, with no HTTP framework linked. No download or catalog request occurs. A production extraction could use `url` directly at that existing pure boundary; it need not copy URL policy into the frontend or introduce another URL validator.

Both offline Cargo commands use Rust 1.100.0, two jobs, no incremental compilation, and no debug information. Native compilation took 12.7 seconds and WASM 6.2 seconds. The selected lock contains 71 packages, including the two local study/core crates. Independent inspection checks the 69 registry archives against original locked checksums and compares all 3,151 packaged files with their unpacked registry bytes. The reqwest re-export is checked against its own archive too. This verifies retained source provenance, not reproducibility of every generated/compiler output or the entire ambient Cargo configuration.

The native executable is 9,804,840 bytes and WASM 3,964,949 bytes with this unoptimized study profile. Initial private work occupied 280,588 KiB before browser profiles. These are measured local development artifacts, not predicted release sizes. No complete product or workspace build occurred.

## Actual requests and outcomes

The [research adapter](document-portable/lib.rs) calls the actual `decode_authoring`, `encode_authoring`, `inspect_authoring`, and `replace_intent` methods. Its versioned JSON wire carries raw author/binding bytes as hex, preserving invalid UTF-8 and absent bindings. The 64 KiB transport bound is a fixture constraint, not a proposed document limit. The native wrapper exits 0 with an explicit result object; its exit behavior is not evidence about empack CLI classification.

The [completed capture](../evidence/empack-portable-documents-20261125T102919154918Z/native-cases.json) contains 12 successes and 22 refusals:

| Request | Observed result across all four targets |
| --- | --- |
| Minimal author input and comment-only variant | Same semantic revision; different raw revision. |
| Absent versus present-empty bindings | Same semantics and author revision; distinct bindings precondition. |
| Inline seed policy versus equivalent separate binding policy | Same semantic revision; different raw document basis. |
| Valid Unicode rename | Syntax-preserving prepared edit with the original author/bindings revisions retained as expectations. |
| No-op rename with absent bindings | Original author bytes and absent binding slot are preserved exactly. |
| Rename with a leading comment | The leading comment survives the prepared output. |
| Empty name, malformed YAML/UTF-8, duplicate YAML key, old/incorrect schema types, unknown fields | Refused with the actual codec cause; no replacement document is returned. |
| Unknown binding root or conflicting inline/binding policies | Refused before manufacturing normalized intent. |
| Local dependency whose file does not exist | Valid intent; source availability is not established by decoding. |
| Canonical Modrinth project/version IDs with a pin | Valid intent without contacting the provider. This is not catalog existence or compatibility evidence. |
| URL without evidence, insecure HTTP URL, or credential-bearing persistent URL | Refused by the existing source/evidence policy. Explicit first-observation HTTPS intent remains valid. |
| Incompatible Prism recipe environment | Refused; the ordinary Prism profile succeeds. |
| Unsupported study schema/action/field or malformed hex | Refused by the research transport, separately from author-schema errors. |

The first collection stopped after 22 rows because its vector incorrectly predicted that a Modrinth slug plus an exact pin would be valid. The actual codec required an eight-character base62 identity. Original inputs, producer, rows, and refusal remain in the build capture. The [continuation](../evidence/empack-portable-documents-20261125T102919154918Z/reused-build.json) reuses the same verified binaries, retains that slug case as a refusal, and adds a valid canonical-ID case. Nothing was recompiled or reattributed to the failed prediction.

## Browser and retained verification

The [browser receipt](../evidence/empack-portable-documents-20261125T102919154918Z/browser.json) records the actual Node binary, Playwright 1.64.1, Chromium 156.0.8078.4, WebKit 27.2, source/module hashes, and every result. The same source-backed WASM executes in dedicated workers. JavaScript transports bytes and does not interpret YAML, choose schema defaults, calculate semantic revisions, or patch author documents.

The module imports nothing. Node observed at most 1,572,864 bytes of linear memory; that excludes compiled code, host memory, and process RSS. Both browsers reject an over-limit packet. The shared byte adapter checks memory bounds and copies output before yielding. This does not qualify arbitrary untrusted RPC, all malformed documents, memory exhaustion, parser security, or general browser capability admission.

The [read-only observer](portable_document_observations.py) independently checks raw author/bindings SHA-256 values, packet/request association, exact runtime bytes, prepared expected revisions, no-op bytes, comment retention, original source/artifact/tool identities, and dependency archive/source correspondence. Its first checksum lookup assumed a registry metadata file absent from this host. The [correction record](../evidence/empack-portable-documents-20261125T102919154918Z/observer-review.json) retains that failure and replaces the assumption with direct archive-member byte comparison; no source or measured outcome changed.

The [closure receipt](../evidence/empack-portable-documents-20261125T102919154918Z/browser-closure.json) reports closed contexts/server, collector exit 0, absent original process group, and no remaining fixture-workspace process. Every native request and both compiler commands separately record absent owned groups. No GUI, personal document, account, world, live project, or operation store was used.

Both maintained collectors now refuse an existing capture before execution or writes. Their bodies match the frozen executed producers after excluding exactly those new preflight lines. The [guard checks](../evidence/empack-portable-documents-20261125T102919154918Z/collector-guard-review.json) exercise both refusals and compare the original files before/after; they recollect no codec/browser results. Derived conformance reports can be regenerated independently of immutable runtime captures.

## Existing laws and their limits

The [document laws](DOCUMENTS.md) already distinguish semantic currency, raw author/binding basis, absent versus empty input, and broader execution admission. They remain unchanged. The [retained comparison](portable_document_conformance.py) adds 16 explicitly model-only projections using actual codec revision labels and a hypothetical saved lock, plus the corresponding Bend predicates. A changed comment or empty bindings can preserve semantic currency while refusing a prior raw-bound write; equal seed meaning authored in different documents has the same distinction. These examples do not claim an actual lock, write, approval, or source-parser proof.

The [conformance receipt](../evidence/empack-portable-documents-20261125T102919154918Z/conformance.json) keeps those model-only results separate from the 34 real codec calls per runtime. Three malformed model inputs refuse, and eight changed observation fields are detected. The ten Lean and four Bend document laws were rechecked in a private output directory. The whole repository proof gate was not repeated because no formal source changed.

```sh
# Compile Documents.lean first with the pinned tools.
LEAN=<pinned-lean> BEND=<pinned-bend> \
  python3 applications/empack/portable_document_conformance.py
```

Replay reads retained artifacts and runs pure models. Collection and compilation are owner-run procedures outside ordinary CI.

Parser, serialization, URL, or digest-library updates need a fresh source/lock identity and native/WASM comparison. Recheck duplicate keys, malformed UTF-8, strict schemas, raw/semantic identity, binding presence, and preserving edits; update syntax-span and inspection expectations where the actual APIs change. Retain earlier captures under their original versions rather than rebinding them to the new dependency graph.

## Design and UX consequence

Retain this codec as the shared interpretation owner. A frontend can keep raw incomplete authoring in its draft, show typed field/span diagnostics, and submit an edit proposal against a captured raw basis. A valid interpretation is not proof of source availability, provider truth, a complete lock, native ownership, or export readiness. A prepared document is not permission to write it. Preserve the raw author and binding slots independently, including comments and presence; canonical output is an interchange/normalization operation rather than a lossless save.

The next extraction should bind the shared codec and inventory planner to retained virtual inputs, then share consumer configuration, namespace policy, archive generation, and verification. The [core extraction sequence](PORTABLE-CORE.md) owns that remaining join. The existing browser storage adapter still has a separate study format; no full project format or migration framework is selected here. Until shared consumer export is implemented and checked, the browser must report that capability as unavailable rather than silently substituting a native companion or a second JavaScript implementation.
