# Saved offers, installation, and rollback

The released empack 0.8.8-beta CLI now has one local signed-input workflow connecting publisher key setup, immutable staging, explicit enrollment, offer preview/save, first installation, an installation refusal, a later installation, old-consumer preparation, and rollback. Eighteen empack commands and six OpenSSL commands are recorded; fifteen of the empack calls operate on the recipient. One deliberate player-side edit is a separate transition. Neither a hosted channel nor a game ran.

This extends the [source-only channel study](../CHANNELS.md), [native ownership study](../OWNERSHIP.md), and [author-to-snapshot-recipient join](../update-flow/README.md). It reuses two exact historical native exports rather than generating another author happy path. Those exports share a pack ID and the human version `A`, but have different payload digests and managed content. Their originals remain unchanged. [Seven source selections](../../sources/empack-subscribed-flow-selections.json) pin the inspected CLI, subscription, instance, signing, trust, and diagnostic owners at `0b4462e3032b4f09230b15329722eabefb7f574c`.

The executable has SHA256 `99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f`. Source/tag correspondence is recorded separately in the earlier join; this is not a reproducible build or dependency qualification. All 24 recorded process groups were absent at completion.

## The local fixture

A fresh private publisher and recipient use explicit own state/cache directories. `release init` creates a random disposable Ed25519 key in a private directory outside the publisher and export roots. `release stage` signs the exact two native payloads and stages their assets. Public keys and signatures are retained; raw seed/DER private bytes and their hashes never enter a capture, project, or receipt. The private fixture remains protected.

The channel offers are **authored test inputs**, signed and independently verified with the installed OpenSSL 4.1.0, using that same disposable key. They name the reserved `https://publisher.invalid` origin. The native subscriber then verifies those inputs against explicit enrollment. This does not execute `release channel create`, verify hosted assets, deploy a pointer, or qualify HTTPS transfer. Every selected offer and release is supplied locally, and release assets are available beside the staged envelopes. A selected missing local association deliberately fails before publication. The replay executes neither empack nor OpenSSL and never reads key bytes.

| Action | Durable offer | Completed release / payload | Observed effect |
| --- | --- | --- | --- |
| Subscribe | None | None | Enrollment records public trust; no content is installed. |
| Preview offer A | None | None | Offer-only preview changes no captured recipient entry. |
| Save offer A | Sequence 1 / channel payload A | None | Only the subscription file changes. |
| Apply signed release A | Sequence 1 / channel payload A | Release A / managed A | First subscribed installation succeeds. |
| Edit own seed and add own note | Unchanged | Unchanged | A deliberate test edit, outside the native commands. |
| Preview offer B | Sequence 1 / channel payload A | Release A / managed A | New-offer preview neither saves the new floor nor installs content. |
| Save offer B | Sequence 2 / channel payload B | Release A / managed A | Only subscription bytes advance. |
| Preview local signed B | Sequence 2 / channel payload B | Release A / managed A | With the offer already saved, a full installation preview is possible; it changes no captured recipient entry. |
| Apply B with a missing explicit input | Sequence 2 / channel payload B | Release A / managed A | Exit 1; the entire captured recipient image remains identical. |
| Apply signed B | Sequence 2 / channel payload B | Release B / managed B | Managed content and completed metadata change. Player seed and unowned note stay byte-, mode-, and modification-time identical. |
| Ensure using old consumer A | Sequence 2 / channel payload B | Release B / managed B | No captured entry changes. `ensure` retains the completed release instead of reverting to the snapshot supplied by an older consumer. |
| Explicit rollback A | Sequence 2 / channel payload B | Release A / managed A | Two entries change: completed instance metadata and managed payload. The newer replay floor survives. |
| Present stale offer A | Sequence 2 / channel payload B | Release A / managed A | Exit 1; valid older signature does not bypass the replay floor. |
| Present forged signature over offer B | Sequence 2 / channel payload B | Release A / managed A | Exit 1; unchanged payload and sequence do not bypass publisher authentication. |

`instance check` after B and after rollback reports a complete check, one verified managed file, one recorded seed/world entry, and no accepted overrides. This is consistent with the [earlier zero-count example](../update-flow/README.md): an unowned note is preserved but is not a recorded seed/world entry. These checks do not validate a Java runtime, game startup, HTTP availability, or actual world contents.

The channel floor's payload hash addresses the exact **channel document bytes**. A completed release ID addresses the exact **release payload bytes**. Neither is the signature envelope hash or human version. The observer checks these relations independently. Rollback changes the installed release without changing what publisher sequence the recipient has already accepted.

## Model composition and checks

[SubscribedFlow.lean](SubscribedFlow.lean) composes the existing [Channels model](../Channels.lean) with installed content, seed ownership, an unowned note, previews, a failed local input, old-consumer ensure, and explicit rollback. The existing model supplies enrollment, signature-witness, exact-floor admission, and successful offer persistence. The new model does not invent another signature verifier, floor-order policy, or writer. [Bend](SubscribedFlow.bend) independently reuses the existing channel admission model.

Twenty-one new Lean laws and sixteen new Bend laws describe the admitted fixture. The focused gate checks three Lean modules and two Bend files, including the reused channel dependencies; only two Lean modules and one Bend file are new. The proof receipt binds every source and tool. It is not a full-repository gate rerun.

Sixteen transition rows compare 128 scalar observations against both models. Fifteen rows are native recipient calls and one is the explicit player edit. Each row reports enrolled-key presence, saved sequence, saved channel-payload identity, completed release, physical managed-payload identity, seed state, note presence, and exit status. Native after-values are decoded by [observations.py](observations.py), not supplied as expected model inputs. The two identity-label sets happen to use `1` and `2`; their actual channel and release hashes remain separate.

The [retained replay](conformance.py) verifies original streams, command arguments, original exports, signed payload/address relations, native root binding, captured file effects, latest owner-local recipient state, source pins, and stat-only private-key permissions. Twelve changed-outcome controls, five unsupported DTO/sequence controls, and three raw-observer controls cover false offer publication, lost floors, unintended installs, seed/note loss, stale/forged acceptance, and wrong native root. It preserves the original records and accepts no arbitrary “nonzero signature” witness.

The [capture](../../evidence/empack-subscribed-flow-20261125T222928929810Z/receipt.json), [proof gate](../../evidence/empack-subscribed-flow-20261125T222928929810Z/proof-gate.json), [comparison](../../evidence/empack-subscribed-flow-20261125T222928929810Z/conformance.json), and [basis](../../evidence/empack-subscribed-flow-20261125T222928929810Z/basis.json) retain the executed scope. Compile the exact Lean models into `.build/empack-subscribed-formal` with the pinned toolchain, then run:

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/empack/subscribed-flow/conformance.py
```

`--public-only` excludes owner-local executable identities, latest recipient state, private-key permission observations, and cached original source files even if their paths exist. It does not reacquire or recreate missing native evidence.

## Keep current and improve the result contract

Keep preview, accepted offer, selected release, verified inputs, installed content, and rollback separate. The native join supports that separation. Do not clear the replay floor after failed installation or rollback, or make old snapshot preparation implicitly revert completed content. Preserve edited seeds and unowned content, and require valid current publisher trust before accepting an offer. The same display version on A and B is legitimate; exact addresses determine selection.

The missing-input failure is concrete: after a saved B offer, an explicit `--file KEY=<owned absent path>` yields only `Error: No such file or directory (os error 2)`. It omits the affected release-file key, destination, selected input role, and safe next step. The refusal itself is correct and preserves the captured recipient state. The existing `DiagnosticCode::AcquisitionFailed`, `DiagnosticPhase::Acquisition`, `object`, and recovery fields are suitable starting points. Attach context where `InstancePlan::acquire_one` still knows the selected file and whether it is an explicit local input or adjacent asset. Preserve the native error kind; do not classify failure by matching the rendered English message or introduce a second filesystem reader merely to format it.

A candidate result should report the observation and installation outcomes separately: an offer may already be saved even when installation fails. “Not published” can describe that installation attempt only if its preparation boundary establishes it; it must not imply that an earlier accepted offer was undone. A UI can say “Offer 2 is saved; the previous release is still installed,” name the missing local input, and show an exact supplied-file retry after checking current state. A single command success/failure field cannot carry all those facts. Prefer deriving this from existing operation receipts and current records rather than adding a new persistent status file.

This resembles the distinction between accepted registry publication and a failed later hook in the [JavaScript publication study](../../js-peers/PUBLICATION.md), or a saved partial snapshot and nonzero result in [restic backup](../../restic/BACKUP.md). Their authority and rollback policies remain product-specific. The shared lesson is to describe each committed effect and unresolved stage, not infer unchanged state from an exit code.

Before implementing the diagnostic proposal, qualify digest mismatch, unreadable or linked explicit inputs, retained overrides, multiple files, and a failure after publication begins. Reuse existing structured fields and terminal escaping; keep raw secret/locator data out of diagnostic envelopes. A combined `instance update --channel-file --apply` failure also needs stage-aware reporting because offer acceptance and release acquisition occur within that one command. This fixture deliberately supplies them separately, so it does not claim to have executed that transport-failure case. The deferred UX implementation remains unstarted.

## Remaining

No hosted channel creation, HTTP redirect/availability/bounds, release fetch, public deployment, trust rotation/revocation, inconsistent saved observation, malformed envelope matrix, stale approval, failed writer, cancellation/crash/recovery, worlds, Prism/server runtime, bootstrap lifetime, other platform, or game is qualified here. The earlier proposed exact saved-observation check remains source-modeled; these consistent native pairs neither reproduce nor dismiss its inconsistent-pair concern. All parent feature operations and joined-scenario statuses remain unchanged.
