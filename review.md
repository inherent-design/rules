# Reviewing a rule from intent to effect

Suppose I ask empack to update a pack, and then I edit a file while the update is downloading. I still want the update. I also want to keep my edit. Both facts can be true. The update plan has to remember what it saw when it decided that replacing the file was safe. Playground has the same problem when a mesh finishes after the world or graphics device has changed.

## What the rules operate on

| Piece | Question it answers | Example |
| --- | --- | --- |
| Intent | What outcome did the user or application request? | Update this instance. Advance this world one tick. An intent can survive a failed attempt. |
| Observation | What did a named source see, where, and when? | A file in an instance had content A. A sample at cell −1 was unavailable. A covered cell with value zero is a different observation. |
| Relation | How do identified things connect? | A release selects a file. A mesh reads a region. A subscriber follows a particular view. Several assertions may support one relationship. |
| Basis | Which observations must still hold to use this decision? | Instance root, previous content, and current authority. Or world epoch, region revisions, and device generation. Each owner advances its own revision. |
| Decision | What should happen if those inputs are accurate? | Replace, preserve, conflict, wait, or refuse. Domain policy supplies the choices. A capacity decision alone grants neither authority nor ownership. |
| Effect and observation of the outcome | Who can change the world, and how will anyone know what happened? | A filesystem adapter applies a journaled operation. A device reports completion. A receipt or later read can resolve an interrupted call. |

A rule can be an ordinary function. The general rules in this repository describe when decisions compose. Project-specific rules supply the meaning of “owned file,” “covered cell,” or “authorized grant.” A host supplies observations that the function cannot establish by examining its inputs.

## What the general proofs buy us

- **Follow relationships.** A lookup can find one target or none. A relation can connect several. A release can select several components and two components can refer to the same content. Grouping the lookups differently preserves which endpoints are reachable. Counting distinct content and counting the reasons it was selected are different queries. A child and its parent must share a perspective, and comparing two intervals requires a common frame.
- **Reuse a result.** If a result reads two sets of inputs, both sets must still be current. An unrelated change can leave it usable. A deadline can expire even when every revision stays the same. The proof assumes the declared inputs include everything the decision reads.
- **Admit and publish.** The tighter of two limits works when both measure the same charge in the same units. Memory bytes and file descriptors each need a check. A host must reserve the resources before another caller takes them. Publication checks the candidate against its expected base. Missing input or a stale base leaves the modeled published state intact.
- **Handle uncertainty and time.** For a conjunction, one known failure decides it. A missing observation with all other checks satisfied leaves the result unknown. If two stages have bounded delays and run in sequence, add the bounds. If both run independently and both must finish, take the slower bound. If either result is sufficient, take the faster guaranteed bound. An unbounded mandatory queue defeats any finite deadline for the whole chain.
- **Replace an adapter or replay work.** If a real and a simulated adapter give the same visible result after every individual step under the chosen mapping, the result extends to a finite sequence. That “if” is work to do. For example, two GPU ledgers can have equal total usage and different target usage. One admits the next target allocation and the other refuses it. No decision using total usage alone can reproduce both answers.

The common Bend laws check how nested yes/no checks guard a candidate. Lean checks the more general relationships above, and the conditions for reusing the capacity check in empack, Playground, and Moment. [General proofs and examples](common/README.md)

## Walkthrough 1. Updating one empack file

1. **Decode the request.** The user selects an instance and asks for an update. A provider name or version range expresses a choice. Resolution binds an exact selection in a lock. At the file boundary, a portable path still needs a host-checked root, and received bytes still need their expected identity verified.
2. **Make a decision.** Suppose the installed record says empack owns A and the incoming managed file is B. If disk still holds A, the planner can propose replacement. If disk holds a third value C, it reports a conflict. If there is no ownership record and disk already contains B, it still reports an unowned destination. A seed file has different policy because the user is expected to keep or edit it.
3. **Apply under current conditions.** The host owns resource permits, verifies the live destination against the plan, and journals publication. In the model, a file edited between planning and publication remains intact. A trusted channel can advance its highest observed release sequence even when installation fails. “Release seen” and “release installed” therefore belong in different fields.
4. **Recover and report.** If a write might have succeeded, read the journal and destination first. On the modeled file, seeing the target content makes replay a no-op. Seeing a third party's content gives a conflict. The recovery proof assumes the journal's before/after identities and disk observation are trustworthy.

**Evidence.** The Rust planner and Lean agree on 245 cases covering normalized file identities, policies, path kinds, and their decisions. This comparison exercises the exact write identity and conflict class. The resource model also proves all-or-nothing charging across job slots, memory, scratch space, and open files. A request that exceeds the configured ceiling cannot succeed by waiting. One that fits the ceiling but encounters current pressure can wait. The recovery proof is about a single journal entry. Filesystem confinement, multi-file crash durability, publisher authentication, and granting permission to change files have other owners. [empack model](empack/README.md)

**Another adapter for the same decision.** A captured terminal observation and a synthetic one can both drive the color/Unicode rule. A redirected stream can select truecolor under “always” and still use ASCII. The local capture samples stderr. Current empack probes stdout separately, so a piped result stream and an interactive diagnostics stream need separate observations. A future web interface could share file decisions without emulating terminal process groups. [Current terminal adapter](../empack/crates/empack-lib/src/terminal/capabilities.rs)

## Walkthrough 2. Advancing a Playground world

1. **Capture the inputs.** The host identifies the world, epoch, tick, requested region, and neighboring cells the kernel needs. All workers read one immutable input. In the two-region example, the old values are 1 and 9 and the exterior neighbors are known zeros.
2. **Prepare and publish.** The example rule copies the larger neighboring value into each cell. It produces 9 and 1. If the second worker read the first worker's newly written 9, it could produce 9 and 9 instead. An absent required neighbor, a refused reservation, or an obsolete base preserves the old root. The partition proof separately covers a kernel reading each cell and both neighbors. Prepared writes to distinct addresses commute. Competing writes require an ordering or a domain conflict policy.
3. **Update dependent products.** A tint change invalidates the modeled mesh while collision remains usable. A device reset invalidates the graphics buffer while the CPU mesh can remain usable. A tick may already be published when a device refuses its product. Report those outcomes independently. For a deterministic restart of the modeled scheduler, preserve pending intents along with cells and tick.
4. **Encode a subscriber view.** A delta carries its epoch, baseline, interest, sequence, and source revision. The replica can apply the next delta only against that basis. A client following a different region needs an appropriate baseline even if the numeric payload looks plausible. The host chooses how to resynchronize.

**Evidence.** The C++ probe exercises the real resource ledger. Splitting a six-byte reservation into four and two retains a six-byte charge, then releasing owners frees their shares. The region, schedule, product, and replica rules are executable models of design contracts. They give examples and proofs for those kernels. Native solver behavior, GPU completion, and a working network session require separate observations. [Playground model](playground/README.md)

## Where Bend and Lean run

| Project | During development or release | In the running application |
| --- | --- | --- |
| Moment | Bend compiles decisions to JavaScript. Build checks verify the identities of the sources and emitted module. Proof qualification checks Bend laws, Lean claims, and comparisons with native consumers. | The JS adapter checks the build manifest and loads the emitted module. For example, it encodes native true/false/unknown observations, calls the policy function, and decodes permit/deny/indeterminate. Native code loads the current grants and records and owns the transaction or provider call. [Runtime adapter](../moment/runtime/semantic-core.mjs) · [Qualification and coverage](../moment/docs/reference/semantics.md) |
| re:desktop | The build emits the Bend access state machine as JavaScript. The separate Lean-backed kernel checks its 13 Bend laws. The local Lean comparison in this repository is an additional check. | The coordinator calls the emitted code for scheduling, pause, and renewal. The host supplies caller identity, time, and connection events. Immediate Pause clears the grant. Pause after lets the current holder continue, including renewal, closes new queue admission while pending, and enters Pause when the grant ends. [Runtime import](../re-desktop/src/core.mjs) · [Mode comparison](re-desktop/README.md) |
| lootr-styled | Bend models resource-source precedence. Build tooling emits and evaluates 32 input combinations. Java tests feed those cases to the actual resource compiler. Lean separately checks bounds and stale publication. A deliberately broken precedence branch must fail qualification. | The mod selects resources in Java. The checked vectors are test resources. The shipped mod needs no Bend or Lean runtime. [Java conformance test](../lootr-styled/core/src/test/java/design/inherent/lootr_styled/resources/PolicyConformanceTest.java) · [Build boundary](../lootr-styled/docs/dependencies.md) |
| empack and Playground models here | Lean runs the examples and checks the proofs. Rust and C++ probes exercise selected native decisions. | These files are a local comparison suite. In the reviewed paths the file planner runs in Rust and the resource ledger runs in C++. [Planner comparison](scripts/compare-empack) · [Ledger probe](playground/LedgerProbe.cpp) |

There are two separate decisions for a project owner. One is whether to express a law and check it during development. The other is whether the application should execute code generated from the rule. Lootr-styled demonstrates keeping the native implementation and checking agreement. Moment and re:desktop demonstrate shipping a generated decision while keeping I/O and effects in the host. Neither approach requires proving a theorem on each user request.

## Questions for the later migration review

These are design choices for a future coordinated Moment intent. The intent in each example above is the end user's requested outcome.

| Boundary | What empack and Playground would need to settle |
| --- | --- |
| User → API or hook | Decode one typed request with its target and basis. Decide which requests are interchangeable across CLI, GUI, and automation. Define whether a hook observes a proposed change, may veto it, or may submit a new request under its own authority. |
| Host → decision | Choose the owner of each fact and its units. For empack, which facts distinguish a local edit from managed content? For Playground, which world and device generations did the job read? Include unknown, missing, and expired observations. |
| Decision → durable or external effect | Name the owner that can apply it and the last moment to recheck its basis. Give refusals stable reasons and define retry, conflict, cancellation, and unknown outcomes. A change notification alone cannot establish that bytes reached disk or a device finished. |
| Outcome → listener or subscription | Encode only the authorized view. Include identities, revision or cursor, and the event that caused the change where needed. Decide what a late subscriber receives, how to handle a duplicate, and when a gap requires a new snapshot. |
| Wire or saved representation → next owner | For a lossless field, test that encoding then decoding preserves the domain value, including large counters and absent values. For an intentionally filtered view, state what was dropped and test the decisions it can still support. Check invalid versions, wrong owners, stale baselines, and interrupted publication against the real consumer. |

Two examples of the representation choices a migration would have to make:

- **empack conflict.** A hook that receives only “update failed” can show a generic error. It cannot safely offer “replace my local version” because it has lost the path, the ownership conflict, and the identity of the file the user reviewed. A structured result could preserve that evidence for an authorized reader. If the user chooses replacement, send a new command bound to that observation. A second intervening edit should bring the user back to review.
- **Playground missing coverage.** Encoding an unread neighbor as zero makes an empty cell and an unloaded cell indistinguishable. The example kernel can use a known zero, while it must defer a dependent update for missing coverage. Preserve that distinction on disk and in the subscriber format wherever downstream consumers make this decision. A visualization that deliberately shows both the same way can remain a display-only view.

For either candidate, a useful migration trial would run the existing native decision and the proposed rule on the same decoded inputs, compare the reason and the selected effect, and keep a counterexample when they disagree. Then exercise the normal caller through a real host boundary and a controlled host that can introduce a late edit, missing data, or lost acknowledgement. That tests the codec and the caller as well as the isolated decision. Which implementation owns the production decision can be settled on that evidence.

A release **selects** content, an observation **supports** a decision, an effect **was caused by** a request, and a subscriber **can see** a view. Keeping those relations distinct lets a listener explain why something happened without acquiring the right to repeat it. For a first migration decision, compare two concrete candidates: empack's file-conflict decision already has a native oracle, while Playground's reservation has a native owner and its tick barrier is still a design contract. That difference determines what a passing comparison could establish today.

## Evidence from the reviewed checkouts

| Checkout | Check run on November 23, 2026 | Result |
| --- | --- | --- |
| Local rules | `scripts/check` | Lean models, common Bend laws, and the terminal replay passed. |
| empack `0b4462e3` | `scripts/compare-empack` from rules | All 245 normalized decisions matched Rust. |
| Playground `d7a1c99` | `c++ -std=c++23 -I../playground/include playground/LedgerProbe.cpp -o .build/ledger-review && .build/ledger-review` from rules | The native ledger passed the pressure, split, and release checks. |
| Moment `158de0b` | `node scripts/build-core.mjs check` and `node --test test/semantic-core.test.mjs` | The emitted-module identity check and nine runtime adapter tests passed. This review did not rerun Moment's full proof suite. |
| re:desktop `a67cb1d` | `scripts/compare-desktop` from rules and `node scripts/bend.mjs PROOF.bend --verdict` from re:desktop | The three renewal cases, three pause observations, and upstream kernel check passed. The coordinator ran in a local fixture with a controlled clock. |
| lootr-styled `f067a90` | `python3 tools/check_proofs.py`, `node tools/proof_vectors.mjs`, and `./gradlew --offline --configure-on-demand :core:test --tests '*PolicyConformanceTest'` | Proofs and the deliberate refusal control passed. The vectors matched their checked-in expectations and the Java conformance test passed. |

**Source drift.** The aggregate `scripts/check-sources` gate stops at `moment/docs/reference/model.md`. Comparing the full manifest against the working checkouts shows 11 changed Moment files and seven changed empack files relative to the historical pins. All pinned Playground, Simulacrum, and refreshed re:desktop files match. The individual checks above establish their stated results on today's sources. Other historical claims remain attributable to the [recorded source snapshots](sources.json).
