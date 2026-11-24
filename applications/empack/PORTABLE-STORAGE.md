# Portable draft storage feasibility

This band implements a research-only browser host adapter. It imports real FileList inputs, retains their bytes in OPFS, saves an incomplete draft in IndexedDB, reopens it, and downloads a study backup. Restoring those selected inputs through the installed native CLI produces a Prism archive. **It does not implement empack's portable engine, production project format, browser distribution exporter, or complete required joined scenario.** The scoped models compare the captured save and recovery boundaries; the complete portable-engine join remains pending.

## Scope and provenance

The [browser collector](portable_study_probe.mjs) executes the [study adapter](portable-study/store.mjs), [worker](portable-study/worker.mjs), and [page](portable-study/page.mjs). It uses Playwright 1.64.1 with cached Chromium 156.0.8078.4 and WebKit 27.2 on this Mac. No browser or SDK download occurs. Each engine has a private persistent profile and the same owned loopback origin across its close/relaunch boundary. There is no account, external service, game, live project, or shared operation-store access.

The [browser receipt](../evidence/empack-portable-storage-20261124T222835992Z/receipt.json) retains executed source, tool identities, capabilities, 14 events per engine, two completed downloads per engine, and actual close results. FileList injection exercises real File and worker structured-clone APIs, not the OS picker UI or drag/drop permissions. Profiles and generated native work occupy approximately 2.5 MiB of allocated space under the capture; this excludes reused tools and is not process-wide cache accounting.

The source JAR is a 318-byte owned ZIP with a manifest and text payload. It is opaque transport input, not a working mod. Configuration includes Unicode. The study changes a configuration's virtual path and retains its original name independently. A separate explicit control supplies a previously missing path; there is no prior provider assertion to verify. That manual placement must not be confused with restricted-download verification by filename.

## Storage and image identity

An opaque UUID names an OPFS file. Its observed SHA-256 and length are separate fields. The adapter writes and closes bytes, then reads them back before publishing an available reference. A save retains its raw author-document bytes and verifies available file references before committing project metadata. Missing references and invalid author text remain saveable.

The semantic image projection contains the workspace label, original raw-author content identity, virtual placements, source labels/evidence, and explicit missing paths. It excludes physical opaque storage handles. Re-saving unchanged content advances the storage revision and can use another backing handle while preserving that image identity. Neither a digest nor a display label grants native ownership or source authenticity.

A shared Web Lock coordinates cooperating saves and asset retention. IndexedDB checks the expected revision and confirms transaction completion before returning a save receipt. An old tab cannot overwrite a newer root. The adapter's domain is one owned study project per origin; it supplies no multi-principal authorization or complete project/asset registry.

The prototype assumes fresh random names and cooperating storage writers. It does not qualify collision handling, general immutable-object publication, eviction, quota exhaustion, or collection. It never deletes assets. Current, historical, pending, and prepared-export retention policies still need a complete implementation and evidence; leaving every file present is not a qualified collector.

## Browser observations

| Boundary                                                            | Observed result in both engines                                                                                                                              |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Import and edit                                                     | Local JAR/config bytes are retained; placement changes preserve content identity and original name.                                                          |
| Save invalid author text with missing input                         | Revision 1 is committed; raw invalid text and the missing path survive the downloaded backup.                                                                |
| Save unchanged content again                                        | Revision advances to 2; semantic image is unchanged while raw-author backing handle differs.                                                                 |
| Stale second tab                                                    | Save refuses with `STALE_REVISION`; the existing revision 2 remains.                                                                                         |
| Worker termination requested after private file creation            | UI reports an unknown save result; metadata stays at revision 2. An empty private orphan remains. A fresh retry succeeds at revision 3 under another handle. |
| Worker termination requested after asset retention                  | Bytes may remain unreferenced; metadata stays at revision 3. Explicit reopen returns that saved draft.                                                       |
| Worker termination requested after metadata commit but before reply | UI still has revision 3 and an unknown outcome; fresh storage inspection observes revision 4. Explicit reopen reconciles to it.                              |
| Repair author text and explicitly supply missing config             | Revision 5 is saved with all three selected content files.                                                                                                   |
| Close and relaunch the browser profile                              | Revision 5, its image, and retained bytes reopen at the same origin.                                                                                         |
| Download                                                            | The runner waits for actual download completion, saves the file, and independently hashes it. A page's “download requested” status is not that receipt.      |
| Explicitly corrupt a retained JAR                                   | Reopen and a new save reject the digest mismatch. The revision-5 record remains available for inspection; no revision 6 is claimed.                          |

The test requests Worker termination; it does not obtain an OS process-tree retirement receipt from the Worker API. Successful later operations and source-controlled phase boundaries support the observed coordination results. Browser-context closure is recorded separately. This is not reboot, power-loss, or permanent durability evidence.

A workspace-label input containing HTML-like text does not create an image element at the measured point. The page uses input values and `textContent`, and serves a restrictive local CSP. This is a bounded observation and source choice, not a complete XSS or browser-security audit.

## Independent storage and native checks

The [raw storage inspector](portable_storage_inspect.mjs) reopens each owned profile and reads IndexedDB/OPFS directly, without importing the study adapter. Its [receipt](../evidence/empack-portable-storage-20261124T222835992Z/backend-inspection.json) observes 12 stored assets per engine: four referenced by the final record and eight unreferenced. Exactly one empty orphan matches the file-creation termination target. The sole referenced digest mismatch is the JAR explicitly corrupted by the test. It performs no repair or reclamation.

The [independent decoder/native adapter](portable_study_native.py) checks strict study fields, path shape, duplicate keys, reference closure, observed lengths/digests, and semantic image identity. Six mutated version/path/closure/digest/image inputs refuse. The [native receipt](../evidence/empack-portable-storage-20261124T222835992Z/native.json) records six installed `0.8.8-beta` CLI commands on fresh private roots. Invalid author text fails native sync with exit 2. Each completed backup then syncs and builds a standalone bundled Prism snapshot successfully.

Both native ZIPs contain the same paths, bytes, and mode values: the JAR, renamed configuration, explicitly supplied configuration, `instance.cfg`, and `mmc-pack.json`. This proves that the selected source inventories survived both browser storage paths and the study transport into the same native exporter. It does not prove browser recipe/rendering parity, an offline Minecraft installation, a working mod, or actual Prism launch.

The [reviewed final images](../evidence/empack-portable-storage-20261124T222835992Z/image-review.json) also expose a prototype limitation: the general digest error does not mark the affected row, and “No missing inputs recorded” describes author declarations rather than current backing validity. A future interface should keep those facts separate, identify the asset needing attention, preserve the draft, and offer an explicit verified-copy repair path. No such repair implementation is qualified here.

The study backup includes only its selected raw-author document and file subtree. It is not a lossless backup of arbitrary native empack projects: lock state, arbitrary document slots, templates, profiles, external references, permissions, evidence policies, and unresolved decisions need the real project format. The format label is deliberately separate from empack's production schemas.

## Scoped formal comparison

The [Lean model](PortableStore.lean), [Bend model](PortableStore.bend), and [bounded research decoder](PortableStoreCase.lean) reuse the [authoring laws](AUTHORING.md). They distinguish available-byte coverage from authoring validity, semantic image from backing handle, backend commit from UI acknowledgement, and failed verification from deletion of saved metadata. Their 19 Lean and six Bend laws are conditional design statements, not proofs of browser storage or production empack.

The [pure replay](portable_store_conformance.py) compares both models with 30 captured boundaries: 28 browser events and the two separately recorded completed backup downloads. Its [receipt](../evidence/empack-portable-storage-20261124T222835992Z/conformance.json) retains the inputs, observed expected fields, model results, and source hashes. Eleven malformed research inputs refuse; seven changed expected fields are detected. Those controls test the decoder and comparison, not browser fault handling.

Inputs follow the known prior editor, explicit producer edits, verified downloads, and independent storage inspection. Hashing, JSON decoding, byte verification, and semantic image labels remain external witnesses. Backup rows compare only storage and delivery because they have no immediate editor snapshot. The final multi-line fill generated more DOM input events than the three editing actions; its unrecorded pre-save epoch is excluded. The corruption row composes ordinary reopen and save because only their combined final snapshot exists. These exclusions preserve the original observations rather than invent intermediate states.

A pure decoder control also found that Python equality admitted boolean and floating-point nested schema values as integer version 1. The research decoder now requires an exact integer. The [before/after control](../evidence/empack-portable-storage-20261124T222835992Z/decoder-scalar-controls.json) preserves the executed decoder identity and corrected source identity. This changes only the study decoder; it does not reattribute the original native run or claim a production schema defect.

## Remaining qualification

The required browser local-JAR/configuration-to-Prism scenario remains open because there is no shared portable engine or browser consumer codec. Do not fill that gap with an independent JavaScript interpretation of Prism or a local companion and call it browser parity. The next implementation decision must preserve shared interpretation and verification while supplying real host capabilities.

Further obligations include complete draft serialization, authority and incarnation checks, undo/plan/pending retention, safe collection, wrong input association, bounded streaming/backpressure, concurrent publication, quota/private-mode/permission failures, crash and ambiguous finalization recovery, and other platforms. The study's small whole-file buffers, limited path checks, and fixed project namespace are not proposed production APIs. No product implementation is selected here.
