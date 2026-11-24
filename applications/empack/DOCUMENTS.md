# empack document meaning and prepared writes

A lock can remain semantically current after a comment changes. That does not authorize a previously prepared write against the changed file. Empack's current source and the installed 0.8.8 CLI preserve this distinction. The application proposal should keep separate semantic identity, raw document revisions, and native execution authority.

## Native workflow

The [collector](documents_probe.py) copied five generated fixture files from the earlier [ownership study](../evidence/empack-native-ownership-20261124T031930881554Z/receipt.json) into a new private project. The author, bindings, and lock were copied along with two tiny source files; state/cache/config/home and the project directory were new. No existing author root, instance, game, channel, or runtime was selected. The source files' bytes, inode, and mtime were checked unchanged afterward.

The [receipt](../evidence/empack-documents-20261124T092737840481Z/receipt.json), [28 commands](../evidence/empack-documents-20261124T092737840481Z/commands.json), and [explicit edits](../evidence/empack-documents-20261124T092737840481Z/edits.json) retain the observed order and file images. The installed binary's hash is recorded. Its Git-tree correspondence with the separately inspected source is not proved.

| Controlled change | Observed behavior |
| --- | --- |
| Author-file comment | `manifest diff --json` reports the lock current; `sync` preserves author and bindings bytes. |
| Bindings-file comment | The lock remains current, and synchronization preserves those comments. |
| Remove a binding that assigns seed ownership to the payload | The lock becomes stale, while the fixed runtime remains satisfied. Synchronization records the changed policy. |
| Create a present, empty bindings file after absence | The lock stays current. Synchronization retains the file rather than treating its presence as absent. |
| Change the pack display name | The lock becomes stale. Fresh synchronization records the metadata and restores lock currency. |
| Unsupported author schema 999 | Inspection exits 2 with an explicit schema diagnostic. The invalid input is unchanged. Restoring the valid bytes makes inspection current again. |

This is a no-dependency author root with a fixed Vanilla runtime. It exercises metadata/policy publication, not retention of a nonempty resolved dependency graph. “Current” is the CLI's metadata/lock relation; it is not provider freshness, verified payload, runtime launch, or gameplay evidence.

`manifest diff` successfully reports both current and stale valid documents with exit 0. Its status describes successful inspection, while `lock_status` carries the finding. Unsupported input instead prevents inspection and returns exit 2. Preserve the distinction between producing a report and passing a validation gate.

### Edits while approval is waiting

For each race, the fixture first changes the display name so synchronization has a pending lock update. It starts `sync` in its own controlling PTY, observes the actual `Apply this synchronization plan?` prompt while the child is live, makes one explicit edit, and sends `y`.

| Edit after the prompt | Result |
| --- | --- |
| Append an author comment | Exit 1; identifies `empack.yml` as changed. |
| Append a lock comment | Exit 1; identifies `empack.lock` as changed. |
| Create an empty bindings file where none existed | Exit 1; identifies `empack.bindings.yml` as changed. |

Every refusal preserves the already edited three-document image, including bytes, mode, inode, and mtime. The old lock remains stale. A fresh synchronization then succeeds and inspection reports current. These were pending metadata writes, not merely no-op previews. The experiment does not establish wrong-plan, wrong-engine, replacement-root, or arbitrary resource/host admission behavior.

Stdout and stderr share the private PTY for those three commands and are recorded as a merged stream. The other commands retain separate streams. The fixture does not use or change the user's terminal. All owned children were reaped; its private work occupies about 40 KiB. Cache/log/state effects outside the three compared project documents are not covered by the refusal-preservation claim.

The [first attempt](../evidence/empack-documents-20261124T092559275751Z/disposition.json) is excluded from completed-fixture qualification. Its last negative assertion expected general exit 1, but unsupported input is correctly classified as usage exit 2. It stopped after 27 commands, with the invalid fixture input preserved. The original streams and source are retained. The corrected collector expects 2 and records the final valid-input restoration in a fresh run; this is a fixture correction, not a product defect or weakened rejection.

## Source contracts and model scope

The [source ledger](../sources/empack-documents-selections.json) pins `0b4462e3032b4f09230b15329722eabefb7f574c`:

- `DecodedIntent` keeps the parsed valid intent, canonical semantic revision, raw author revision, original bytes, and optional original bindings separately.
- `DecodedLock::bind` checks exact selections against current semantic intent. A readable old lock can be inspected after author changes without becoming a coherent resolved project.
- `replace_intent` preserves original author/bindings bytes for a no-op and carries their expected raw revisions. Bindings absence remains a distinct precondition.
- Captured project revisions also include native root identity and the optional raw lock revision. Preparation, exact plan grants, owning-engine checks, and execution revalidation remain separate boundaries.
- The host prepares synchronization before requesting approval. Positive `y` authorizes the captured plan; it does not refresh its source observations.

[Lean](Documents.lean) models only the fixture's varied display-name and payload-policy meaning, raw three-document basis, semantic lock currency, and the necessary document gate. Ten laws distinguish raw changes from meaning, preserve current edits after refusal, and keep other host checks explicit. A raw state marked invalid is not a constructed engine `DecodedIntent`.

The [comparison](documents_conformance.py) reconstructs controlled semantic labels from the frozen fixture edits and compares 28 command outcomes and document-state relations against Lean. The written lock identity is supplied symbolically from the observed result; this is not a generic YAML parser, lock encoder, or canonical-fingerprint oracle. Authored inputs remain unchanged by synchronization while the recorded lock can change. [Bend](Documents.bend) independently compares 27 metadata-currency/document-gate decisions and checks four laws. The unsupported-schema exit classification is checked separately; a false Boolean does not identify an error category. Three invalid research decoder inputs are refused.

The models do not make document-hash equality sufficient for publication. Root identity, captured file observations, valid prepared ownership, resource limits, grants, recovery coordination, and final persistence retain their real host obligations. No engine API constructor is replaced by a UI flag or a research label.

## Design, UX, and compatibility

Keep the existing revision split. It lets harmless formatting changes retain useful resolution evidence while preventing an old approved writer from erasing a later comment or newly created bindings file. Use “lock current” for semantic coherence, and explain which author change needs synchronization. The current stale-input refusal already identifies the affected file and requires fresh preparation; preserve that behavior.

For 0.9 editing, one universal “revision” is insufficient. Editable raw documents, semantic interpretation, retained exact selections, and a prepared host write can have different bases. A semantically reusable result may remain useful after a comment, but an old raw-bound write must be prepared again. Saved or invalid drafts remain distinct from valid native intent, and a browser project cannot supply native root identity or mint a publication grant.

This does not select a new cache or automatic rebasing subsystem. Before introducing semantic-result reuse, define the exact consumed inputs and test stale results, absent/present bindings, syntax-only edits, metadata changes, and invalid drafts against the same captured basis. Preserve the current native checks while choosing portable identities for portable work. Keep-current behavior remains the implementation baseline.

Broader codec editing, commented collection restrictions, nonempty dependency updates, granted replacement footprints, cross-engine requests, root/object substitution, crash/recovery, and actual browser save/export joins remain separate work. No complete document, synchronization, authorization, or portable-authoring family is qualified by this band.
