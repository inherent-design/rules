# Copy identity and destination verification

This band studies restic 0.20.0 copying selected snapshots between three new local repositories. It separates source snapshot identity, persistent copy origin, compared metadata, retained file content, and encrypted destination objects. It does not qualify remote backends, interrupted copy, concurrent writers, cryptography, or the whole copy feature.

## Source rules

The [pinned sources](../sources/restic-copy-selections.json) identify the inspected code and documentation at `9c88ff768f10c192dc6a87619a65a16374080e33`. `collectAllSnapshots` considers a source's `Original`, falling back to its current ID. Destination lookup includes both nonzero `Original` and current IDs. A lookup match skips copying only when `similarSnapshots` also accepts the metadata.

That comparison checks time, tree, host, user, UID/GID, path/tag lengths and membership, and ordered exclusions. It ignores `Parent` and `Original`, but also omits `ProgramVersion` and `Summary`. Its comment's broader wording is therefore not an exact field contract. The membership test with equal lengths is not multiset equality: duplicate-bearing tag inputs can make the predicate directional. The models retain that source behavior. This fixture does not establish that ordinary CLI operations can produce the duplicate counterexample, nor that the omitted fields cause a user-visible failure.

Copying preserves an existing `Original`; a first copy records the source ID. It clears `Parent`. File and tree blobs are copied before snapshot publication. The source's read lock and destination's append lock have separate roles. The existing destination index/listing drives the skip decision; these models do not establish a general transactional batch or concurrent-copy deduplication guarantee.

Snapshot object IDs are not semantic content IDs. `SaveJSONUnpacked` delegates to the repository, whose `saveUnpacked` hashes newly encrypted, nonce-bearing bytes for non-config objects. The nearby snapshot field's “plaintext ID” comment must not override that implementation. Copy origin, plaintext tree/blob identity, encrypted snapshot ID, and repository identity remain distinct.

## Executed local fixture

The [collector](copy_probe.py) reuses the already verified Darwin arm64 binary. The [capture](../evidence/restic-copy-20261124T231054816138Z/receipt.json) contains three generated repositories with distinct passwords and configuration IDs, two tiny text files, 47 initial commands, and seven readback completion commands. Repository B uses A's chunker parameters; C uses independently generated parameters. The measured generated work occupies 1,156 KiB, excluding the reused binary. Passwords, encrypted repositories, and raw account-bearing output remain ignored/private.

| Copy request                                | New destination snapshots | Other observed effect                                          |
| ------------------------------------------- | ------------------------: | -------------------------------------------------------------- |
| Select the first source snapshot explicitly |                         1 | Only that snapshot is copied.                                  |
| Copy both source snapshots                  |                         1 | The existing first copy is skipped.                            |
| Repeat the same source copy                 |                         0 | Destination repository files are unchanged.                    |
| Copy B into C                               |                         2 | Original identities survive; encrypted snapshot IDs differ.    |
| Tag B's first copy, then copy A again       |                         1 | The tagged variant remains alongside a restored baseline copy. |
| Copy the three B variants into C            |                         1 | Existing equivalent copies are skipped.                        |
| Select a nonexistent tag                    |                         0 | Destination repository files are unchanged.                    |
| Use the wrong source password               |                         0 | Exit 12; destination repository files are unchanged.           |

All eight copy commands preserve the measured source repository files. A full destination `check --read-data` succeeds. Fresh destination listings and three dumps establish that the two first-image variants contain the original file bytes and the second-image snapshot contains the changed bytes. Every owned command group was absent after completion. There is no existing user backup or global installation in this procedure.

The initial final dump failed because the harness used the source selection path as an inner archive path. The failed command and streams remain intact. The [bounded completion](../evidence/restic-copy-20261124T231054816138Z/finish.py) obtains a fresh listing, finds `/mutable.txt`, and completes only readback/configuration checks. It repeats no backup or copy. `Snapshot.Paths` describes the source selection; it is not automatically the path accepted by `dump`. The maintained producer now discovers that path from `ls`.

Verbose copy output describes skipped sources and destination snapshot IDs, even with the root `--json` flag selected. That output was plain prose in this fixture. The global flag is not treated here as a promise that every command form emits a structured document. Native observations, rather than the presence of the flag or a printed ID alone, establish the resulting snapshot set.

## Models and comparison

[Lean](Copy.lean) models persistent origin, source-compatible metadata comparison, skip admission, and normalized copied metadata. [Bend](Copy.bend) implements the same projection. Fourteen Lean and seven Bend laws preserve origin across copies, drop lineage without dropping selected metadata, reject unrelated origins, keep metadata variants distinct, and retain the directional duplicate counterexample. Destination IDs are externally admitted results, not numbers computed from plaintext by these models.

The [pure comparison](copy_conformance.py) derives selected-source requests from the retained cases. It compares decisions with fresh destination additions and, only for actual new snapshots, compares normalized metadata with the independently listed destination. A copy-needed decision does not establish publication. Skip and refusal rows therefore compare only the decision, not an invented copy receipt. Source filtering is a captured input to this projection, not a modeled filter implementation.

Both models match 13 selected-source decisions across the eight copy commands. Seven malformed research inputs refuse, and four changed expected fields are detected. These controls exercise the research decoder/comparison rather than native failure injection.

The comparison validates raw/public stream correspondence, frozen producer/completion identities, original failure preservation, and actual dump bytes. Scalar time/tree/host/user tuples receive opaque labels from the owner-local original records. Public account fields were redacted, so public readers cannot reconstruct those particular labels from the redacted streams alone. The conformance receipt retains projected inputs and measured outputs with this limitation; it does not silently promote redacted data into missing original evidence.

## Decisions and follow-up

Preserve metadata-sensitive skip behavior, explicit source/destination roles, key separation, source content identities, and persistent copy origin. Equal tree data alone should not collapse deliberately tagged variants. A copy origin is provenance used by this operation, not publisher authentication or authority over another repository.

A focused internal improvement would name the compared metadata projection explicitly and keep snapshot IDs, copy-origin IDs, tree/blob IDs, and destination publication receipts distinct at the relevant boundaries. Correcting the helper comment and adding tests for omitted fields may be sufficient; a new serialized schema or general migration framework is not justified by these observations. If stronger similarity is proposed, first investigate whether summary/program-version differences should cause another copy, whether duplicate paths/tags are admitted, and whether existing repositories depend on the current skip policy. Preserve a keep-current alternative when the comparison is deliberate.

An optional structured copy receipt could expose selected, skipped, saved, failed, and unknown outcomes with source ID, persistent origin, and confirmed destination ID. It should reuse the current facts and preserve verbose human output rather than announce a completed copy from a selection decision. Review existing output consumers before adding a format. A follow-up reader can still inspect snapshots with today's interface, though that adds calls and concurrency ambiguity.

For empack's proposed project transport, this supports keeping project/image identity separate from encrypted or host-specific storage identity. It does not justify adopting restic's `Original` as a project ownership token or replacing empack's source assertions with copied provenance. General retry, partial publication, remote acknowledgement, destination corruption, hostile metadata, and cross-platform qualification remain open. No production change is selected.
