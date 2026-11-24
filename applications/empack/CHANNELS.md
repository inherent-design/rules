# Signed channel source observations

An authenticated offer is separate from a durable subscription observation, release acquisition, and installation. This record studies the current channel boundary at empack source revision `0b4462e3032b4f09230b15329722eabefb7f574c`. It does not execute the installed 0.8.8 CLI or a complete engine, publisher, or update workflow.

## Compiled source and adapters

The [collector](channel_probe.py) compiles selected unchanged functions from `engine/release/trust.rs`, actual release helper functions, and the diagnostic definitions/constructor. The [source ledger](../sources/empack-channel-selections.json) identifies nine implementation/contract files and inspected ranges. The native receipt additionally identifies each selected source range, generated file, compiler, direct dependency artifact, and resulting binary.

These APIs are in the engine, not the previously reused pure-core library. Existing dependency artifacts require the matching Rust 1.99.1 toolchain. The fixture reuses seven direct libraries from the existing dependency directory; it performs no Cargo or full-engine build. Transitive dependency source and reproducible-build correspondence are not established. The source-fragment executable is its own tested artifact.

Channel schema decoding, signing, enrollment, signature verification, origin checks, engine compatibility, and floor checks use the selected implementation. Release decoding is a rejecting fixture stub because no release payload is exercised. The diagnostic data types and `new` constructor are source selections; `Display` is a fixture adapter. The complete production terminal formatter and error classifier are outside this compilation. Generated closure braces and parent imports are scaffold, not additional production behavior.

The [driver](channel_oracle.rs) uses fixed public test seeds, fictional `.invalid` HTTPS addresses, and in-memory data. Those seeds are not publisher credentials. No network request, real key custody, native instance mutation, release acquisition, or installation occurs.

## Retained observations

The [corrected receipt](../evidence/empack-channels-20261124T130523942359Z/receipt.json) and [raw records](../evidence/empack-channels-20261124T130523942359Z/observe.stdout) contain 39 observations: 37 enrollment/channel evaluations and two separate decode/sign refusals. They are source-fragment observations, not 39 end-to-end update tests.

| Boundary                                                                                                                                        | Observed behavior                                                                                                                                                                  |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Initial offer and identical retry                                                                                                               | Accepted, including retry against the retained floor                                                                                                                               |
| Earlier sequence                                                                                                                                | Rejected with a floor; accepted when no previous floor is supplied                                                                                                                 |
| Same sequence with changed envelope bound                                                                                                       | Rejected                                                                                                                                                                           |
| Same sequence, semantically equal JSON with different whitespace                                                                                | Rejected because the exact payload digest changes                                                                                                                                  |
| Higher sequence with changed metadata                                                                                                           | Accepted                                                                                                                                                                           |
| Added signature, unchanged payload                                                                                                              | Accepted against the existing payload floor                                                                                                                                        |
| New signer without explicit enrollment                                                                                                          | Rejected                                                                                                                                                                           |
| New signer explicitly added to current enrollment                                                                                               | Accepted                                                                                                                                                                           |
| One valid enrolled signer among multiple enrolled keys                                                                                          | Sufficient for authentication                                                                                                                                                      |
| Invalid additional enrolled signature                                                                                                           | Rejected even when another enrolled signature is valid                                                                                                                             |
| Invalid additional unknown-key signature, structurally valid entry                                                                              | Does not contribute authentication and does not invalidate the valid enrolled signature                                                                                            |
| Empty or duplicate enrolled keys                                                                                                                | Refused during enrollment                                                                                                                                                          |
| Wrong pack, selected channel, release origin/port, or floor identity                                                                            | Refused                                                                                                                                                                            |
| Default HTTPS port, or path/query on the enrollment URL                                                                                         | Normalized to the same enrolled origin                                                                                                                                             |
| HTTP or credentials in the enrollment URL                                                                                                       | Refused                                                                                                                                                                            |
| Selected engine constraints                                                                                                                     | Exact/current and same-channel lower-patch beta requirements admit `0.8.8-beta`; stable-only, restrictive upper-bound, different prerelease channel, and higher-minor cases refuse |
| Wrong envelope kind, unsupported algorithm, duplicate signature key, uppercase payload encoding, bad known signature, or unknown envelope field | Refused                                                                                                                                                                            |
| Old `expires` field                                                                                                                             | Refused by schema decoding                                                                                                                                                         |
| Duplicate signing input                                                                                                                         | Refused by the signing API                                                                                                                                                         |

The exact payload identity is not the envelope identity. Signature metadata can change while the payload floor remains identical. Conversely, changing otherwise valid JSON whitespace changes that floor even when parsed fields are equal. These observations do not authorize replacing an immutable hosted release envelope or define a publisher key-rotation procedure; those are different callers and persistence policies.

The unknown cosigner case also has a narrow meaning. Every entry must pass structural checks, and at least one enrolled key must verify. Unknown keys do not become enrolled, and their signatures are not authenticated claims. An invalid signature from a key that is enrolled aborts verification. This is the current policy, not a threshold-signature protocol or a proof that every named signer approved the offer.

The engine compatibility cases retain original comparator bounds. The source's prerelease extension admits a later patch in an explicitly admitted channel without removing an authored upper bound or exact requirement. These selected cases do not implement or qualify arbitrary SemVer expressions.

## Diagnostic probe correction

The [first capture](../evidence/empack-channels-20261124T130409809158Z/disposition.json) remains intact. Its driver searched `std::error::Error` sources for a `Diagnostic`, which misses typed `anyhow` context. Production `Diagnostic::from_error` first uses `anyhow::Error::downcast_ref`; the corrected driver uses that same lookup mechanism.

All 39 original inputs, phases, acceptance decisions, messages, and floors agree after excluding the diagnostic projection. The corrected run reports 12 typed causes: eight publisher-authentication contexts missed by the original projection, plus four engine-compatibility causes already visible there. The original nulls are a harness defect, not evidence that empack loses these diagnostics. Both original producers, drivers, receipts, generated source, binaries, and streams are preserved. Repeating the cases after this correction adds no coverage count.

Floor ordering/identity checks use plain `ensure!` errors in the selected source. The fixture does not run the production classifier's fallback or final CLI rendering. A future reporting proposal must distinguish an authenticated but stale offer from a failed signature without claiming a currently observed CLI code or parsing English text as machine authority.

## Saved observation versus new offer

A new channel offer may advance a saved floor. Revalidating the envelope already recorded as that floor has a different job: it should establish that the stored pair still describes the same observation. The current `SubscriptionRecord::authenticated_channel()` reuses the new-offer validator, which permits advancement.

The [saved-record receipt](../evidence/empack-channels-20261124T133716623327Z/receipt.json) adds nine source-fragment observations using the unchanged record decoder, authentication method, and `require_selected_offer` helper. The helper and authentication method are evaluated independently in memory. Their reported conjunction is a source composition, not a complete acquisition trace; a real caller stops when its first guard fails.

| Stored input or selected basis               | Decode | Selected-floor guard | Saved authentication | Returned floor equals stored floor |
| -------------------------------------------- | ------ | -------------------- | -------------------- | ---------------------------------- |
| Consistent observed envelope and floor       | Accept | Accept               | Accept               | Yes                                |
| Signed sequence 4 envelope, sequence 3 floor | Accept | Accept               | Accept               | **No**                             |
| Older observed envelope                      | Accept | Accept               | Refuse               | No                                 |
| Same sequence, wrong payload digest in floor | Accept | Accept               | Refuse               | No                                 |
| Only one of envelope/floor present           | Refuse | Not run              | Not run              | Not run                            |
| Keys revoked                                 | Accept | Accept               | Refuse               | No                                 |
| Caller selected a different floor            | Accept | Refuse               | Accept               | Yes                                |
| Neither observation nor floor present        | Accept | Refuse               | Refuse               | No                                 |
| Floor bound to another identity              | Refuse | Not run              | Not run              | Not run                            |

The sequence 4 case preserves the input record bytes. Authentication returns a newer floor without establishing equality with the recorded sequence 3 floor. The fixture changes the sequence while retaining the same release reference; it does not demonstrate acquisition of different release content. Stable root/record reads and an expected-floor comparison do not themselves establish this pair's semantic consistency. No ordinary update, interruption, crash, or recovery path was reproduced producing the inconsistent record.

The candidate correction is narrow: after authenticating a **saved** envelope, require its returned `SequenceFloor` to equal the saved floor. Keep monotonic advancement for a **new** offer. Existing floor equality and authentication can supply this check; no new crypto system, schema, or migration framework is needed. If separate proof types help callers, distinguish an authenticated incoming offer from an exactly revalidated recorded offer without duplicating their parser or verifier.

Do not move current-key authentication into record decoding. Records with revoked keys must remain inspectable and recoverable even though they cannot authorize a release. Do not clear or lower a floor to repair inconsistency automatically. A future diagnostic should name the saved observation mismatch and offer inspection/recovery without implying that authentication or installation succeeded. This is an implementation proposal, not an applied production fix or a qualified release blocker.

## Source-only lifecycle boundaries

The strict subscription record is local data, not an authentication proof. Its observed envelope is reverified against current enrollment before release selection. Replacing or revoking keys preserves the sequence floor. An authenticated observation updates the floor and retained envelope through recoverable publication; it does not install release content.

Release fetching requires the selected floor to be durable and still equal both before and after acquisition. The resulting subscribed-release proof also captures the root and subscription bytes for later revalidation. These source inspections do not qualify actual filesystem recovery, host approval, network redirects, download integrity, or mutation behavior.

Channels have no calendar-expiry input. Current schema 2 rejects the former field instead of silently restoring an expiry policy. An unchanged offer does not need renewal; choosing an older release intentionally requires a newer offer sequence. The observed same-sequence checks are about exact payload bytes, not elapsed time. No clock-change experiment was run.

## Models and retained comparison

[Lean](Channels.lean) checks 36 laws; [Bend](Channels.bend) checks 13. They model enrolled identities, attributable signature witnesses, exact payload floors, engine admission, saved/current selection, and distinct installation state. Host-current and write-authorization premises remain explicit; the successful-commit projection is not a filesystem protocol. Installation rollback and key replacement preserve the observation floor. Authentication alone neither persists that floor nor installs content.

The [pure replay](channel_conformance.py), [Lean input adapter](ChannelsCase.lean), and [comparison receipt](../evidence/empack-channels-20261124T130523942359Z/conformance.json) match both models to 39 corrected channel observations plus nine saved-record observations. The original 39 diagnostic-projection cases are checked for agreement, not counted again. Eight malformed research inputs and an unsupported crypto witness are refused. The replay compiles the exact Lean model afresh before importing it, and records that artifact identity; a failed compile cannot fall back to an older model artifact.

Signature validity comes from a closed catalog of actual producer signatures and named invalid controls, not a nonzero-byte guess or a new Ed25519 implementation. URL normalization and the six engine requirements are selected fixture profiles. The models use opaque labels for their admitted identities, not general URL, JSON, or SemVer parsers. The decoder's negative controls validate the research adapter, not all production input bounds.

The model retains the current mismatched-record acceptance. A separate proposed saved check refuses that mismatch while preserving the consistent case and new-offer advancement. These checks do not promote the proposal to implemented behavior. No complete feature family or joined scenario is qualified.

## Compatibility and verification before implementation

Preserve exact payload identity, explicit key enrollment, signature-entry policy, authored engine bounds, nonexpiring offers, and floors independent of installed releases. Keep error causes typed through the existing diagnostic mechanism; the corrected harness supplies no reason to replace it. A CLI or SDK can distinguish offer authentication, durable observation, acquisition, and installation using the facts already present, rather than reporting a single ambiguous update-success flag.

Before adopting exact saved revalidation, inject an inconsistent pair into a disposable real engine fixture and require refusal before acquisition. Compare a correctly observed newer offer, revoked keys, an empty subscription, stale selected basis, and different release content. Exercise actual observe/publication ordering and failures: acquisition failure or cancellation must not lower a committed floor; rolling back installed content must not reset it. Recheck root association, current subscription bytes, and recovery behavior. The source-fragment result cannot replace these tests, and existing callers may reject an inconsistent root earlier.

## Evidence limits

This record establishes bounded source/model comparisons. It does not qualify a complete engine, installed CLI, publisher transaction, HTTP redirect policy, release decoding, acquisition, filesystem recovery, or consumer installation. There is no proof of crypto algorithms or dependency reproducibility. No public service, personal state, installed executable, or production source changed. Original captures and the corrected diagnostic disposition remain retained; private generated source and binaries live under ignored `work/`.
