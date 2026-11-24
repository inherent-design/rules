# Observation demand: user destinations and distribution sources

An installation policy and a source-integrity obligation answer different questions. Existing seed data belongs to the user; a publisher's seed source still needs verified bytes when the distribution carries it. The current implementation preserves that ownership distinction, but installation preparation snapshots ordinary selected seed files before deciding to preserve them.

This band records a current observation-footprint limitation and a proposed API simplification. It changes no implementation or resource limit. It demonstrates neither data loss nor a release-blocking defect.

## Current behavior and native evidence

The pinned `instance::plan` captures the union of prior and incoming file targets, then obtains content observations and calls the pure file planner. `ProjectReadRoot::capture` visits regular files and `observe_file` checks their length before hashing them. The normal application factory supplies default snapshot limits, including an 8 GiB per-file limit. World groups have an earlier protection pass that can exclude all their members before this capture; ordinary seed files do not receive that group-level exclusion.

`instance check` follows a different path: it classifies seed/world entries as player-owned and captures content only for managed entries. Its report says those user-owned bytes were not compared. This difference is source-confirmed in the [selected implementation ranges](../sources/empack-selections.json).

The [private fixture](../evidence/empack-seed-footprint-20261124T040524972293Z/receipt.json) installed an unmodified native release produced by the earlier ownership flow. It then extended its own seed file to 8,589,934,593 logical bytes with a sparse tail. Allocated storage was 4,096 bytes before and after the tested operations.

| Operation | Observed result |
| --- | --- |
| Initial local snapshot installation | Succeeded. |
| `instance check --json` with the sparse seed | Succeeded; one player-owned entry and one verified managed file. |
| Installation preview of the same release | Failed with `Snapshot exceeds byte limit`. |
| Check after restoring the fixture's small seed | Succeeded. |

The seed's size and modification time did not change during the check and preview. The collector then restored only that owned fixture file. No large payload was allocated, no game was launched, and the original ownership fixture remained unchanged. No filesystem/network tracing or normal-size performance benchmark was collected. The input is a metadata stress case, not a realistic game configuration.

The refusal is consistent with the current snapshot limit. The interesting point is that the core seed-preservation decision does not need those existing bytes. A proposed narrower observation could avoid the unnecessary byte dependency while retaining the limit for work that actually consumes content. This does not mean every part of the current installation operation is proved ready by a shape observation.

## Proposed facts and roles

The [Lean](ObservationDemand.lean) and [Bend](ObservationDemand.bend) models distinguish unavailable observation, witnessed absence, directory shape, a regular file without byte facts, and a regular file with byte facts. They also distinguish an installed destination from a distribution source. These are admitted semantic observations; a project document or caller Boolean cannot mint the corresponding native proof.

| Context | Required next step in the candidate |
| --- | --- |
| Ordinary existing seed destination, no explicit change | Preserve it without claiming byte equality. |
| Managed destination or explicit change, bytes unknown | Obtain byte facts before an exact content-bound plan. |
| Missing destination | Prepare against witnessed absence and existing ownership rules; this is not permission to create. |
| Missing distribution source | Report the missing source; do not reinterpret it as a fresh installation. |
| Seed distribution source, bytes unknown | Obtain verified source bytes or satisfy an explicitly supported reference recipe. |
| Directory at a selected file target | Reject the shape. |
| Unavailable observation | Retain the uncertainty; never infer absence. |

The candidate is conservative outside ordinary seed preservation. Its distribution-source role concerns a selected materialized/local file; admissible remote reference obligations need their existing separate recipe proof. Some other refusal-only decisions may also need fewer facts; those are not modeled as optimized here. World-group initialization and consumer-specific requirements remain separate preconditions.

Nine Lean laws and four Bend laws check these distinctions. The current large numeric byte-limit predicate is replayed in Lean against the native outcome. Bend checks eleven qualitative role/evidence cases; it does not evaluate the multi-gigabyte numeric input. The proposed classifications are design examples, not execution of a new native implementation.

## Implementation boundary to investigate

1. Introduce a narrow native shape/absence observation with root, ancestor, and no-follow evidence. Keep it distinct from observed content and immutable retained source bytes.
2. Preserve ordinary seed destinations through a no-file-write disposition. Do not create a dummy `FileContent` or content ID to satisfy the existing enum; that would fabricate byte evidence.
3. Keep untouched user paths outside verified publisher-byte postconditions. Prove the admitted mutation footprint does not overlap them or their protected roots. Relevant root/shape/absence revalidation, coordination, collision rules, and reserved metadata paths still apply.
4. Re-prepare actual byte-bound changes after an explicit decision. Preserve, replace, merge, and local-override acceptance retain their own exact observation/grant requirements. A shape-only preview is not a reusable write grant.
5. Keep distribution verification unchanged: source assets, required integration, portable attributes, and final artifact/sink completion still require their actual evidence. Seed ownership never excuses missing publisher input bytes.

The current `FilePlan` combines observed-file expectations with desired changes, so this is more than skipping a read in one caller. Its publisher/verification consumers need explicit untouched-path handling and tests. Native and portable hosts must not invent different meanings for these facts during extraction.

The keep-current alternative is safe refusal under the existing bounds and full read set. It retains unnecessary I/O and can produce an opaque preparation error for a file that will be preserved. Raising the limit addresses this one size example but retains the byte dependency. A broad “skip verification” flag would be an inappropriate substitute: managed content, explicit changes, and source acquisition still need verification.

## Reporting and validation

The native error names neither the selected file nor the limit and observed size. A structured observation failure should carry the operation, path, demanded fact, available evidence, and actual bound. Presentation can explain which work could not be prepared without suggesting that a seed was overwritten or that the user should delete their data. Useful partial checks remain visible.

Preserved user data should be described as player-owned and unverified against publisher content, matching the existing `instance check` state. A green “verified” label would claim too much. The [scoped change-summary proposal](OWNERSHIP.md#preservation-and-improvement-candidate) can carry that disposition alongside game-file and metadata effects.

Before adopting the candidate, test readable/unreadable ordinary seeds, large and concurrently edited seeds, absence-to-file races, directory/link/reparse substitution, explicit conflict decisions, and consumer constraints. Retain all managed-content, override, source-assertion, and publication fault controls. A missing raw custom source must remain saveable as a draft reference but cannot become a verified bundled export merely because its eventual installation policy is seed.

The [replay adapter](seed_footprint_conformance.py) verifies native command/output identities and the current gate, then compares the proposed classes with both models. It freezes the input basis and never runs empack:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/seed_footprint_conformance.py applications/evidence/empack-seed-footprint-20261124T040524972293Z
```

Compile `ObservationDemand.lean` to `.build/applications/empack/ObservationDemand.olean` first, with the ownership module available. The native collector is separate owner-run work outside ordinary CI.
