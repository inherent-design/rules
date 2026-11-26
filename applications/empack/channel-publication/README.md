# Channel publication and exact payload retries

The selected publisher guard accepts an authenticated previous channel and a same-sequence candidate when their decoded documents are equal. The subscriber instead requires the same **payload bytes** at an already observed sequence. In the source comparison, whitespace or key-order changes preserve decoded equality but fail that subscriber check. Formatting only the outer envelope preserves acceptance because the signed payload stays unchanged.

This is a bounded source-component mismatch, not a completed channel publication or subscriber update. The normal producer's canonical output retries successfully in the control. The counterexample needs a valid earlier pointer with a different serialization, such as an authenticated pointer written by another encoder. The study changes no production implementation or deferred UX intent.

## Boundary and source

The [source ledger](../../sources/empack-channel-publication-selections.json) pins empack `0b4462e3032b4f09230b15329722eabefb7f574c`. The [collector](probe.py) reuses the earlier [channel fixture](../CHANNELS.md)'s unchanged crypto, codec, enrollment, previous-pointer, and subscriber-floor functions. It adds the unchanged sequence guard extracted from `release_publication/channel.rs`. A small wrapper supplies the admitted channel/key context; it does not prepare a staged release, inspect its assets, acquire hosted content, or publish files.

The [capture](../../evidence/empack-channel-publication-20261126T112857119598Z/receipt.json) identifies the frozen earlier generated source, new guard cut, driver, compiler, seven reused direct libraries, and new binary. Compilation and observation completed in separate owned groups, both absent afterward. No Cargo/full-engine build ran. Matching direct artifacts do not establish full transitive source or reproducible-build correspondence. The earlier rejecting release-decoder and diagnostic-format adapters remain outside the exercised contract.

All signing uses a fixed public test seed in [the driver](oracle.rs), not a real publisher credential. An [independent OpenSSL check](verify_crypto.py) verifies nine distinct public signature inputs associated with the 22 prior/candidate envelopes. It verifies the actual domain-prefixed payloads; it does not establish origin, engine policy, release availability, or private key custody. The native library result and that independent signature result remain separate observations.

## Measured cases

Eleven controlled cases form one source comparison, not eleven complete producer workflows.

| Prior/candidate relation | Publisher local guard | Subscriber against prior floor |
| --- | --- | --- |
| Exact retry | Accept | Accept |
| Same decoded document; prior payload has surrounding whitespace | Accept | Refuse changed payload at observed sequence |
| Same decoded document; prior payload uses another key order | Accept | Refuse changed payload at observed sequence |
| Only prior envelope has surrounding whitespace | Accept | Accept |
| Same sequence, changed release ID | Refuse | Refuse |
| Same sequence, changed envelope byte bound | Refuse | Refuse |
| Candidate has an earlier sequence | Refuse | Refuse |
| Higher sequence, same release | Accept | Accept |
| Higher sequence after prior payload whitespace | Accept | Accept |
| Higher sequence after an earlier pointer's engine requirement becomes unsuitable | Accept | Accept at the selected new engine |
| Invalid prior signature | Refuse authentication | Not run without a prior floor |

The old-engine control obtains its earlier floor at engine `99.0.0` and tests the new compatible offer at `0.8.8-beta`. Publisher authentication of previous state deliberately serves ordering, not current installation eligibility. A proposed correction must preserve that distinction; replacing it wholesale with current-engine offer admission would change another policy.

The [raw records](../../evidence/empack-channel-publication-20261126T112857119598Z/observe.stdout) retain documents, exact payload text/digests, envelopes/digests, errors, and floors. The observer independently reconstructs the bounded ASCII struct/envelope encodings, compares document equality with payload identity, and checks the returned floors. That adapter does not implement arbitrary JSON equivalence, duplicate-field policy, Ed25519, or every compatibility requirement.

## Candidate and compatibility

At an unchanged sequence, preserve the authenticated payload identity. One focused option refuses a changed payload and directs the publisher to advance the sequence. Another retains the exact authenticated prior payload for an idempotent retry instead of re-encoding it. Either needs access to the previous authenticated bytes or their identity alongside the decoded document. Reuse the existing verifier and payload hashing; do not replace publisher trust or weaken the subscriber floor.

Compare payload identity, not the outer envelope digest. Additional signatures, key rotation, or envelope formatting can change the envelope while retaining the same offer bytes. Keep previous-pointer authentication separate from current-engine eligibility and higher-sequence advancement. No channel schema or general migration framework is required for the narrow rule.

The keep-current alternative is credible only with an explicit constraint that every prior pointer uses the same canonical payload encoder. The selected decoder authenticates other valid JSON serializations, so that constraint has not been established for all admitted prior state. Normal native-producer retries remain controls, not proof that every authenticated old pointer is canonical.

Before adoption, exercise the actual producer through hosted verification and local publication, inspect repeated canonical output, noncanonical authentic prior state, key rotation, same/higher/lower sequences, stale approval/source changes, and the subscriber's durable floor. Preserve previous files and keys on failure. A source guard accepting a candidate does not establish that acquisition or publication succeeds.

## Models and retained replay

[Lean](Publication.lean) has twelve laws; [Bend](Publication.bend) has nine finite checked laws. Their generic projections retain authenticated-prior admission, sequence ordering, semantic versus payload equality, absent subscriber execution, and envelope independence. The stricter proposed rule adds payload equality at an unchanged sequence. Its Lean law implies subscriber acceptance under the profile's admitted identity/runtime/codec witnesses; it does not prove crypto, transport, or publication.

The [decoder](PublicationCase.lean) admits a bounded research profile, not a public API. Signature validity comes from independently retained OpenSSL results plus closed origin/codec/engine premises, not from the publisher's Boolean. Inputs derive from captured requests and bytes, while native outcomes are separate comparison targets. The [pure replay](conformance.py) matches 22 measured publisher/subscriber fields across eleven cases and compares both models' proposed results. Nine reason-specific decoder refusals and five changed-observation controls pass.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> \
  python3 applications/empack/channel-publication/conformance.py --public-only
```

Replay runs Lean/Bend and reads retained evidence. It never invokes Rust, OpenSSL, the released CLI, or a server. Owner mode additionally checks the original/new generated sources, compiler, native binary, direct libraries, and current OpenSSL binary. Public mode names those excluded checks; its model/results agree otherwise.

The [first compilation](../../evidence/empack-channel-publication-20261126T112827565929Z/disposition.json) is excluded: the injected wrapper lacked the existing `ensure` macro import, and no source case ran. A fresh capture fixes that adapter. A later replay control initially dereferenced a missing next-floor object; an explicit shape assertion now refuses that inconsistent result. Original diagnostics and private pre-correction replay source remain retained. Neither failure is attributed to empack.

## Hosted-production boundary remains open

Native `release channel create` verifies the hosted immutable envelope and assets before publication. The selected source permits HTTPS; its loopback HTTP origin mapping is test-only. Its ordinary client builder exposes no per-operation CA input through this CLI. The locked reqwest default uses platform certificate verification; on macOS the verifier uses platform roots/keychain facilities. [Verifier documentation](https://docs.rs/rustls-platform-verifier/0.7.1/rustls_platform_verifier/), [reqwest certificate configuration](https://docs.rs/reqwest/0.13.5/reqwest/struct.ClientBuilder.html#method.tls_certs_merge).

This pass made no host trust change, disabled no verification, and performed no TLS request. A successful local HTTPS producer flow was not selected without an admitted test trust arrangement. That is a specific unexercised boundary, not a product failure or a whole-goal blocker. Native hosted creation, transport, actual artifact publication, process loss, and consumer installation remain required before a full workflow claim. Existing [signed local inputs](../subscribed-flow/README.md) and [saved-offer checks](../saved-offer/README.md) retain their separate scopes.
