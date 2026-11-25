# Joined portable authoring and Prism export

The selected research workflow now runs from actual file import through save/reopen and verified Prism export on native macOS, Chromium, and WebKit. The three exports are byte-identical. The installed empack 0.8.8 CLI independently builds the same artifact from the captured author and files. This qualifies a bounded vanilla, bundled snapshot scenario, using a new research project format and shared Rust adapter. It does not establish a production 0.9 engine, provider resolution, a general project format, or a successful Prism/game launch.

## Shared implementation and source boundary

The [source ledger](../sources/empack-joined-selections.json) and [successful build](../evidence/empack-joined-20261125T111512569488Z/build.json) pin empack `0b4462e3032b4f09230b15329722eabefb7f574c`. The complete current core and `DocumentCodec` tree compile unchanged. Current layout/runtime helpers, INI encoding, and the default Prism template are unchanged. The Prism profile generator/verifier and selected template helpers use exact source slices, with an isolated module/import facade. The synchronous cancellation slice excludes Tokio waiting. This is not a complete `empack-lib` or executable build.

The [research engine](joined-study/lib.rs) owns the draft wire, interpretation calls, source hashing, inventory selection, output paths, profile/config generation, ZIP assembly, and archive verification. JavaScript supplies storage, framing, worker scheduling, and delivery; it does not parse YAML or duplicate consumer/domain rules. The exact locked `url` package substitutes for the current `reqwest::Url` re-export, as in the [document band](PORTABLE-DOCUMENTS.md).

New code remains explicit: the research snapshot format, immutable-image encoding, chunk protocol, bounded ZIP sink/verifier, native storage script, and browser storage/UI are proposed adapters. A validated dependency-free vanilla project is constructed for this scenario; authored dependency roots, custom discovery/layout, and other loaders refuse. The real `BuildSelection` runs before content demand, and `BuildInventory::project` checks completed representations. The study is not a second provider resolver, native ownership implementation, or publication service.

Source imports are opaque UUID-backed assets with digest/length witnesses. An image includes raw author/binding slots, virtual entries, placements, portable attributes, and logical asset references. Native and browser captures can therefore have different image IDs while producing identical distributions. The wire/hash is study-specific. Invalid authoring and declared missing references survive save/reopen; content declared available must verify before saving. Missing size is unknown, while a present empty file has known size zero.

## Observed workflow

The [native receipt](../evidence/empack-joined-flow-20261125T113211837178Z/native.json) contains 13 events, four completed artifacts, and two fresh native peer processes. The [browser receipt](../evidence/empack-joined-flow-20261125T113211837178Z/browser.json) contains 11 events and one actual download for each of Chromium 156.0.8078.4 and WebKit 27.2, using Playwright 1.64.1 and private persistent profiles.

| Boundary | Actual observation |
| --- | --- |
| Import | A real FileList supplies a 318-byte opaque fixture JAR and a Unicode configuration file. OPFS bytes are closed and read back before publishing references. |
| Incomplete draft | Malformed author text and a declared missing file save at revision 1 and reopen intact. Interpretation failure is distinct from storage failure. |
| Edit and preview | The current Rust codec repairs/renames the author, and the shared draft changes the configuration placement to `config/renamed Ω 日本.json`. The missing placeholder is explicitly removed. |
| Save and restart | Revision 2 survives closing and relaunching each browser context. An expected-revision-0 save refuses without replacing it. Native reopen uses a fresh process. |
| Captured export | Export captures saved image A; the editor changes to B before input transfer. The artifact still names A, while B remains the current unsaved draft. |
| Verification and delivery | No artifact can be read before verification. CRC, member set, modes, content hashes, and Prism profile checks precede transfer. Playwright records a completed browser download separately from the page's download request. |
| Lost save acknowledgement | The IDB transaction commits revision 3, the test barrier withholds its reply, and the actual worker is terminated. The UI retains its earlier saved basis and reports uncertainty. A new worker reopens revision 3. This is not power-loss durability evidence. |
| Input/output refusals | Selected missing input, corrupted retained bytes, case-alias destinations, and an injected truncated ZIP refuse. The deliberately corrupted private source is explicitly restored. An opposite-side missing input is excluded before acquisition. |
| Streaming and cancellation | A 102,400-byte incompressible owned input crosses several source and artifact chunks. Cancellation after one input chunk removes the logical operation and leaves no readable artifact. Cancellation after readiness reports that bytes may already have been copied. |
| Text handling | HTML-like metadata renders as text with no injected image or executed handler. This single check is not an XSS/security audit. |

Independent [ZIP inspection](../evidence/empack-joined-flow-20261125T113211837178Z/independent-archives.json) checks all main members and bytes, permissions, Unix directory modes, CRC, literal `{{ NAME }}` configuration content, and the generated vanilla Prism profile. Native, Chromium, and WebKit main archives contain four files and three directories, totaling 1,381 compressed bytes. These are fixture sizes, not predicted real-pack or release sizes. The executed fixtures use default file modes (0644) and directories (0755); nondefault readonly/executable cases are not qualified by this join.

The [installed CLI comparison](../evidence/empack-joined-flow-20261125T113211837178Z/installed-reference.json) uses the existing 0.8.8 executable by exact hash, explicit private state/cache/project directories, and ordinary `sync` plus `build --ad-hoc prism --delivery bundled --environment client --updates snapshot --format zip`. Its inventory, bytes, and modes match; the archive hash also happens to match. This is independent executable behavior, not a source-to-binary reproducible-build proof. No host installation, personal project, instance, world, or live operation store changes.

The [independent backend probe](../evidence/empack-joined-flow-20261125T113211837178Z/backend-probe.json) reads IDB directly and hashes OPFS bytes using WebCrypto, without the study store/engine. Both browsers have exactly two retained objects and three history records. Roots, history, and asset bytes remain unchanged before/after the probe. The probe then checks the maintained external stylesheet visually. Original workflow screenshots were unstyled because the CSP blocked inline CSS; the original HTML, screenshots, and producers remain retained. The follow-up changes only stylesheet delivery, with domain code unchanged and CSP retained.

## Protocol, bounds, and host obligations

Inputs and verified artifacts transfer in at most 16 KiB chunks. The controlled wire is bounded to 64 KiB, author/binding documents to 8 KiB each, 16 entries, 8 MiB per source/total output, 16 MiB private ZIP, and four logical operations. ZIP assembly and final verification are synchronous bounded research calls; the whole archive is still held privately in memory. The host yields between source/artifact chunks. This does not qualify arbitrary-size packs, responsiveness budgets, backpressure, memory-exhaustion resistance, or a general cancellable scheduler.

Browser saves coordinate a root Web Lock and publish root/history in one IDB transaction. Native saves use a private temporary file, fsync, replace, and directory fsync in a single-writer fixture. No general native multi-writer lock or garbage collector is implemented. Export inputs are immutable in the cooperative fixture and no reclamation runs. A missing backing object is not silently substituted with another handle or an equal filename. Collection must eventually retain saved/current/history/plan roots under an independently qualified publication/reclamation protocol.

The private native peer is NDJSON, not empack's CLI/RPC. Its line iterator allocates a line before checking the protocol bound; it is unsuitable as an untrusted public endpoint. Native peer exit 0 carries typed response success/refusal and says nothing about product CLI exit classification. Worker termination establishes worker loss, not retirement of a native process tree or rollback of committed storage.

## Build investigation and preservation

The first [attempt](../evidence/empack-joined-20261125T110839827038Z/build.json) preserved compile errors from an include path, over-broad Prism coupling, and a fallible ZIP filename API. No runtime cases ran. The [second attempt](../evidence/empack-joined-20261125T111025677257Z/build.json) compiled natively but failed WASM linkage: its `psm` archive was 96 bytes with no object symbols. The same shipped WASM object, archived with the installed LLVM archiver, produced 628 bytes and the required four functions. Original and comparison archives/symbol outputs remain attributed.

The final build sets only the target-specific `AR_wasm32_unknown_unknown` to the recorded LLVM archiver. It retains original dependency versions and stack checks. Native compilation took 1.8 seconds and WASM 3.7 seconds using the existing private target cache; held prior binaries remain unchanged. The [read-only observer](portable_joined_observations.py) checks 134 exact locked registry archives and 5,577 extracted source files, plus Git sources/fragments, artifacts, profiles, producers, saved-image encodings, and downloaded bytes. Ambient compiler/linker configuration and all subordinate tool provenance are not a reproducible-build guarantee.

The ZIP dependency introduces genuine WASM entropy imports. Matching official `wasm-bindgen` 0.2.129 generates the web module/glue; no fake import or disabled security check substitutes for them. The [tool receipt](../evidence/empack-joined-20261125T111512569488Z/bindgen.json) pins the official release archive digest and outputs. A native 102,400-byte protocol smoke and 24 identical Node-WASM replies precede the browser flow; they are separate evidence, not full browser coverage. The Node replay producer was not frozen before execution, so its current file is a reproduction aid rather than a contemporaneous producer attestation.

All native peers, compiler groups, reference CLI commands, browser contexts, and loopback collectors are terminal. Private binaries, inputs, profiles, archives, sources, locks, and original failures remain protected evidence. The shared target cache stays under the existing active storage hold until this joined cohort is fully handed off; no cleanup, live-state sweep, Moment retention change, or historical recovery deletion is part of this band.

## Models and maintained checks

The [export model](JoinedExport.lean) adds ten Lean laws and five Bend laws for input completion versus verification, captured basis, readable output, and cancellation copy uncertainty. It composes the existing authoring admission distinction. The existing [portable-store model](PortableStore.lean) is reused unchanged for save/reopen and acknowledgement loss.

The [retained conformance](../evidence/empack-joined-flow-20261125T113211837178Z/conformance.json) compares 55 source/byte-derived protocol boundaries against both models and 12 browser save/reopen boundaries against both existing storage models. It compares only returned or independently observed fields; editor epochs and unobserved retirement state are excluded. Eight DTO refusals, six changed protocol fields, and four changed source/backend/artifact observations are detected. Hashing, parser correctness, source admission, and actual sink completion remain external checked witnesses, not formal theorems about Rust or browsers.

```sh
# First compile the model dependencies into the private directory recorded in
# .build/empack-joined-formal-current, using the pinned Lean/Bend toolchain.
LEAN=<pinned-lean> BEND=<pinned-bend> \
  python3 applications/empack/portable_joined_conformance.py
```

Collection/build scripts are explicit owner-run procedures. Ordinary CI may typecheck the pure models and inspect retained data; it must not run Rust builds, package operations, browsers, the installed CLI, or game consumers. Parser, template, ZIP, digest, browser, or WASM-tool upgrades require new version/source identities and focused recollection at the changed boundary. Keep old captures attributed instead of rebinding them to a newer dependency graph.

## Design consequence and remaining scope

Keep a shared interpretation/inventory/consumer owner, with small native and browser storage/delivery adapters. Save incomplete work separately from export readiness. Present the current draft, saved image, source availability, export capture, and finalized delivery as distinct facts. A late edit must not rewrite an export's meaning, and an unknown save reply must lead to reopen/reconciliation before retry. The harness is evidence tooling, not a production UI design.

The selected research join has now been exercised. Remaining production work includes the complete format and history policy, all provider/runtime/recipe capabilities, richer bindings/policies, native ownership/authorization, quota and contention, browser eviction/backing recovery, interrupted import/save/export, large-pack scheduling, consumer import/launch, and qualified delivery/publication. The full nine-application goal and parent feature/operation coverage remain incomplete. This band does not activate deferred product UX work or select a production migration framework.
