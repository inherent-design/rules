# empack: removal, retained content, and re-adoption

An author request, an exact locked selection, and a verified native file are different things. Removing one does not imply permission to remove the others. This study follows that distinction through the current core's removal and exact-request merge APIs. It does not implement the deferred removal/re-adoption UX intent.

## Executed boundary

The [caller](removal_oracle.rs) executes unchanged `RemovalPlan`, `AdditionGroup`, and `AdditionPlan` APIs from empack source `0b4462e3032b4f09230b15329722eabefb7f574c`. The [collector](removal_probe.py) reuses the attributed core artifact from the [projection capture](../evidence/empack-projection-20261124T063515339963Z/receipt.json), checking source, library, and compiler identities first. It builds one small caller, not the engine.

The [receipt](../evidence/empack-removal-20261124T152228425387Z/receipt.json) and [25 records](../evidence/empack-removal-20261124T152228425387Z/observed.stdout) contain nineteen removal proposals and six subsequent request merges. The base has explicit root A, required A→B, and unlisted C. All three have fictional Modrinth identities, identical-version fixture pins, one asserted mod file each, and complete dependency coverage unless a case changes it. Two cases add B→A. Re-addition requests contain A→B, with identical records; C is excluded from the request but retained in the project.

Semantic revision tokens are supplied equality labels. Digests and provider IDs are fictional. No codec, provider lookup, file capture, download, approval, native publication, or installed CLI is executed. Core constructors validate each input and resulting project. Native file deletion authority is not supplied by a successful core proposal.

## Removal results

| Request                                                    | Observed core result                                                                        |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Remove A's content                                         | A leaves author intent and lock; B and C remain, including the now-unrequested B.           |
| Forget A                                                   | A leaves author intent; all exact records, graph evidence, and content assertions remain.   |
| Forget B, or forget A and B together                       | Refused because B is not an explicit root. No partial candidate is returned.                |
| Remove B while retained A requires it                      | Refused, including with acknowledged unknown evidence.                                      |
| Remove A while unrelated C has partial or unknown coverage | Refused by default. A missing known edge from C is not evidence that C cannot require A.    |
| Remove A with acknowledged partial C                       | Accepted; C remains, and the plan retains C's uncertainty.                                  |
| Forget A with partial C                                    | Accepted without deletion or a retained-uncertainty list.                                   |
| Remove A whose own coverage is partial                     | Accepted when the retained records are complete and do not require A.                       |
| Known dependent A plus unrelated unknown C                 | The known-dependent error takes precedence over incomplete evidence.                        |
| Remove part of A↔B                                         | Refused because the retained member requires the selected member.                           |
| Explicitly select all of A↔B                               | Accepted; unrequested C remains.                                                            |
| Duplicate or unknown raw core key                          | Refused; a batch with a valid earlier key still yields no partial candidate.                |
| Explicitly remove unlisted C                               | Accepted; A's author request and A→B remain.                                                |
| Explicitly remove all records with unknown coverage        | Accepted because no uncertain dependent remains. Native file safeguards are still required. |

Removal does not perform orphan collection. The whole-cycle case needs no transitive search: every incoming required edge from a retained record is checked directly. Unknown coverage and known edges are separate facts; acknowledging the former cannot override the latter.

The [source ledger](../sources/empack-removal-selections.json) also pins the engine selector and native preparation paths. Those source-only checks have different responsibilities. Exact keys and explicit provider identities occupy separate selector namespaces; titles do not select content. The engine selector deduplicates matches, so the raw core duplicate-key case is not a demonstrated ordinary CLI failure. Native preparation verifies selected placements and original content assertions, refuses inappropriate file shapes, retains needed acquisition sources, stages a file plan, and requires separate publication. None of those safeguards is qualified by these pure core calls.

## Re-adoption is not one operation

The six merge cases first complete the core's forget-A or remove-A proposal, then submit the identical resolved A→B request. The request snapshots are retained alongside the prior state.

| Prior action       | Merge API               | New author root A           | Exact A record changes | Existing requested installation reported |
| ------------------ | ----------------------- | --------------------------- | ---------------------- | ---------------------------------------- |
| Forget A           | Add                     | Yes                         | No                     | A                                        |
| Forget A           | Adopt observed content  | No                          | No                     | A                                        |
| Forget A           | Update selected content | No                          | No                     | A                                        |
| Remove A's content | Add                     | Yes                         | A is added             | None                                     |
| Remove A's content | Adopt observed content  | Yes                         | A is added             | None                                     |
| Remove A's content | Update selected content | Refused: A is not installed | No candidate           | No candidate                             |

The adoption API preserves existing author constraints and does not promote retained transitive or unlisted records. The update API preserves author intent and requires the requested identity to be installed. The add API can restore an explicit author request without changing any exact record. Those are deliberate semantic differences, not equivalent aliases.

The engine's inspected `RejectExisting` condition asks whether any **requested installation already exists in the lock**. It does not ask whether its author root exists or whether the exact record changed. The driver reports that condition separately as `rejectExistingWouldAllow`; it is a source interpretation, not an executed engine admission result. It is false for each forgotten-A merge. Actual call sites can select different policies, and materialization or publication can fail independently.

Consequently, “no changed selections” can coexist with a meaningful author-intent change. A generic “already exists” message loses that distinction. Conversely, interpreting a forgotten author root as absent installed content could bypass necessary existing-selection authorization. Keep the current protective checks while exposing the actual state.

## Models and verification

[Lean](Removal.lean) checks twenty laws and compares full projected values: first selection error, known-dependent priority, uncertainty, selected/removed keys, retained exact record text, coverage and edge-map presence, author roots, and the bounded identical-request merge. [Bend](Removal.bend) checks nine local laws and independently computes admission/error priority for nineteen removals and root-promotion policy for six merges. Bend does not implement the full record/graph rewrite; that comparison belongs to Lean.

The [replay](removal_conformance.py) matches all [25 retained results](../evidence/empack-removal-20261124T152228425387Z/conformance.json) and refuses eight unsupported research inputs. The decoder restricts ordered keys, graph closure, coverage variants, and the identical A→B re-addition profile. Unsupported research input is not a statement that empack rejects that feature. Opaque debug record text is an equality witness, not a public schema or a source of filesystem authority.

The [first capture](../evidence/empack-removal-20261124T152143364201Z/disposition.json) omitted the resolved request snapshots from merge rows. The revised driver adds them. Its [projection review](../evidence/empack-removal-20261124T152228425387Z/projection-review.json) verifies all 25 prior outcomes and before snapshots unchanged. Both original and revised source, compiler output, and streams are retained. This was an observation improvement, not a product correction.

Each caller capture occupies about 2.4 MiB, reuses the core artifact, and has retired. Ordinary rules CI runs models and retained rules, not the collector or the application. Full owner-local replay requires the ignored library, source, and private caller binaries. A public checkout cannot independently reproduce those artifact checks without obtaining their attributed inputs.

## Design and UX direction

Report the affected author request separately from retained content: root present or absent, exact selection present or absent, known dependents, uncertainty, and the proposed logical/file effects. Explain that forgetting A leaves its content tracked. When a prerequisite was never an explicit root, name the requesting root rather than telling the user to forget that prerequisite.

An identical retained selection can still need the author request restored. Prefer a narrow path through the existing addition plan and explicit existing-selection policy; do not build a second resolver or silently treat adoption as promotion. Decide whether a future CLI should offer that action directly or explain the existing safe path. Qualify author constraints, canonical alias matching, native content checks, captured revision, and approval before choosing an implementation. Do not weaken known-dependency or file-ownership checks to simplify the message.

For the current/0.9 internal model, preserve authored roots, canonical provider identity, exact records, graph/coverage evidence, content availability, and physical installation as separate values. A displayed “retained” state should not imply reachable-from-root, filesystem verified, or selected for deletion. A logical plan, approved publication, completed file change, and verified installation are separate evidence.

Further work must join real selector resolution, author edits, nonempty native files, stale approval, acquisition-source retention, and publication/recovery. Addition with changed pins, conflicting metadata, aliases, local/URL content, optional or negative relationships, larger graphs, and arbitrary physical interruptions remain unqualified. This band selects no production change, general migration mechanism, or completed feature family.
