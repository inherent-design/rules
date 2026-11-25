# Saved-offer consistency through the native CLI

Empack 0.8.8-beta accepts a deliberately inconsistent saved subscription through local release preview, installation, and checking. The signed envelope describes offer B at sequence 2, while the saved replay floor describes offer A at sequence 1. The installed release becomes B, but the inconsistent saved pair remains. `instance check` then reports a complete check and says the saved enrollment and observation are consistent.

This confirms the earlier [source-level concern and exact-saved proposal](../CHANNELS.md) at selected real CLI boundaries. **The record was explicitly altered by this study.** No normal publisher/update flow, crash, or remote attacker is shown creating it. It is a saved-state validation gap under that input, not evidence that ordinary installations corrupt themselves or that an untrusted publisher bypasses signatures.

## Procedure and observations

The [collector](probe.py) uses a fresh disposable recipient, state directory, and cache. It reuses only public signed offers/releases and verified staged assets from the [local signed-input join](../subscribed-flow/README.md). It neither reads private signing keys nor mutates the prior recipient or publisher. Nine native commands complete; every process group is absent. No HTTP, engine build, Java, game, or deployment runs.

After explicit enrollment and saving valid offer B, the native root binding, keys, origin, channel, and saved B envelope stay unchanged during each authored edit. Only the floor field is replaced. Every edit is captured as a separate event with exact before/after bytes. The original controls, mutations, refusals, and repair remain retained.

| Saved input | Native result | Captured recipient effect |
| --- | --- | --- |
| Envelope B / exact B floor | Local signed-B preview succeeds. | No entry changes. |
| Envelope B / older A floor | Local signed-B preview succeeds. | No entry changes during preview. |
| The same inconsistent pair, applying B | Installation succeeds. | Completed release B and its exact managed/seed bytes appear; the saved subscription remains byte-identical with floor 1 and observed sequence 2. |
| Checking that installation | Exit 0; complete; subscription finding passes. | No entry changes. The output explicitly says saved enrollment and observation are consistent. |
| Envelope B / sequence 2 with A's different payload hash | Preview refuses: `Channel changed at an already observed sequence`. | No entry changes. This separates monotonic advancement from exact same-sequence identity. |
| Restore the authored older floor, then explicitly observe valid B | Observation succeeds. | Only subscription bytes change, restoring floor 2 paired with B. A subsequent preview succeeds. |

The last step is an observed explicit recovery path for this fixture. It authenticates and accepts B through the incoming-offer operation; it does not silently lower or clear a floor. Other corruption directions, revoked keys, missing envelopes, and transport failures need their own decisions and checks.

## Why the roles differ

[Five source selections](../../sources/empack-saved-offer-selections.json) pin the current owners at `0b4462e3032b4f09230b15329722eabefb7f574c`:

- `SubscriptionRecord::decode` checks structure, paired presence, root/enrollment shape, and floor identity. It does not authenticate the saved envelope or require equality with its candidate floor.
- `SubscriptionRecord::authenticated_channel` reuses `PublisherTrust::channel`, the incoming-offer validator. That validator correctly permits a newer signed offer above the existing floor.
- Local `select_from_record` accepts that authenticated channel and selects the signed release. Its proof retains the root and hash of the current subscription bytes, which do not establish agreement between those bytes' fields.
- Instance checking calls the same saved method before printing its consistency finding.
- The actual incoming `SubscriptionRequest::Observe` validates the new offer against the old floor, then publishes the candidate floor and exact envelope together. Its advancement rule should remain unchanged.

The local signed-release CLI route does not call `require_selected_offer`; that guard belongs to the fetched-release path. The earlier source fixture evaluated the guard independently. Do not infer that the local route exercised it, or turn an in-memory conjunction into a new filesystem guard claim. A stronger fetched-path expected-floor comparison still needs exact saved-pair authentication before it uses that record's envelope.

The [recorded executable](../../evidence/empack-saved-offer-20261125T225128247208Z/setup.json) has SHA256 `99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f`. Earlier source/tag correspondence does not prove a reproducible binary build. The native captures establish this executable's behavior; selected source comparisons explain the matching validation roles.

## Reuse the existing models

This band adds no formal model modules or laws. [Channels.lean](../Channels.lean), [Channels.bend](../Channels.bend), and their existing exact-saved counterexample already describe the distinction. Their unchanged source hashes match the earlier kernel-checked dependency receipt. Replay compiles the exact Lean source afresh and runs the existing driver; it independently evaluates the same cached-current and cached-exact predicates in Bend.

Four native preview boundaries cover three distinct saved-pair profiles; the final repaired pair repeats the positive control. Both models' four **current admission** values match those native boundaries. Four **proposed exactness** values are model-only: consistent pairs remain admitted, and both mismatches are refused. The existing driver's selected-floor wrapper columns are intentionally excluded from native comparison because the local CLI route did not execute that guard. Seven changed-outcome/DTO controls protect the current behavior, paired floor input, supported schema, and signature-witness profile.

Installation, byte verification, checking, and explicit repair are separately observed and checked from their raw snapshots. The cached-admission predicate does not prove those entire operations. Signature validity is a closed witness backed by the unchanged signed inputs and earlier native/OpenSSL verification, not inferred from nonzero signature bytes.

The [receipt](../../evidence/empack-saved-offer-20261125T225128247208Z/receipt.json), [comparison](../../evidence/empack-saved-offer-20261125T225128247208Z/conformance.json), and [basis hashes](../../evidence/empack-saved-offer-20261125T225128247208Z/basis.json) identify the native and replay scope. Retained replay executes no empack, signing tool, network operation, or key read:

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/empack/saved-offer/conformance.py
```

`--public-only` excludes the current executable identity, latest private recipient image, and cached original source readbacks. It still checks the retained streams, mutation lineage, current/proposed model distinction, and public signed-input identities.

## Proposed correction and compatibility

Keep structural record decoding separate from current publisher authentication. A record must remain inspectable when its keys are revoked or its fields need repair. After authenticating a **saved** envelope, require the returned `SequenceFloor` to equal the saved floor. Continue allowing advancement for an **incoming** offer, and preserve the existing selected-floor/current-root/subscription-byte rechecks around acquisition and application.

The smallest candidate is an equality check in the existing saved helper, reused by local selection, fetched selection, and instance checking. If callers benefit from a proof type, distinguish an authenticated incoming offer from an exactly revalidated saved observation while reusing the same parser and signature verifier. No new signature format, calendar expiry, persistent field, or migration framework is needed. Consistent records retain their meaning; inconsistent records formerly accepted by these readers would now require explicit inspection or fresh authenticated observation. Do not repair them by automatically clearing keys, lowering floors, or accepting arbitrary unsigned replacements.

The current consistency message should become a failure for this input once the domain check is implemented. Changing only the string would leave selection and publication admitting the same pair. The diagnostic should identify the saved observation/floor mismatch and offer a safe next action without claiming the record was produced by a crash or that installed content is itself corrupt.

Before production adoption, exercise the patched helper through actual local and fetched callers, correct new-offer advancement, same-sequence identity, revoked/replaced keys, absent/incomplete records, stale selected/current root evidence, and interrupted publication/recovery. Reuse this native counterexample rather than rerunning another unpatched happy path. Neither the production helper nor executable was changed here; exact-saved enforcement remains a separately selected implementation decision.

## Remaining scope

This is a forensic saved-input comparison, not fault-origin reproduction, a general state-repair tool, an authenticated storage proof, or a remote exploit. HTTP selection, concurrency, actual writer failure, crash/reboot, publisher rotation, game/world behavior, and other platforms remain unqualified. All parent operation and joined-scenario statuses remain unchanged. The broader nine-application work remains active.
