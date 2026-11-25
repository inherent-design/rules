# Archive names, metadata, and import publication

The current rules distinguish a raw ZIP directory, an opaque archive name, a portable destination, and verified member content. The experiments support keeping those boundaries. Unsafe outer entries were refused before author publication, including entries the importer would not use. A valid opaque JAR was retained without rewriting its internal resources. The selected encoding control was decoded correctly, and two differently encoded names for one destination were refused. No new archive correctness defect was established in this band.

## Three evidence profiles

| Profile | Actual execution | What it establishes |
| --- | --- | --- |
| [Core path APIs](../evidence/empack-archives-20261125T135102774049Z/paths.stdout) | 34 calls to each of the real `ArchiveMemberName::parse` and `PortableRelPath::parse` APIs, using the retained current-core library | Selected acceptance/rejection and preservation of accepted spelling. No native I/O authority or arbitrary-input proof. |
| [Raw metadata helper](../evidence/empack-archives-20261125T135102774049Z/observed.json) | 26 calls to unchanged `preflight_zip`, with its actual `ArchiveLimits` definition and explicitly new error/context, cancellation-check, and traced-Cursor adapters | Raw directory guards, ordering, per-entry check counts, and selected refusal paths. This is not the full engine, anyhow error-chain behavior, native cancellation, or a ZIP payload decoder. |
| [Installed imports](../evidence/empack-archive-import-20261125T135422292082Z/receipt.json), plus [encoding controls](../evidence/empack-archive-encoding-20261125T142823826296Z/receipt.json) | Twelve disposable local mrpack imports: three accepted and nine refused | Selected full import outcomes, preserved bytes, typed exit codes, and scoped author-directory effects. No game, remote selections, publisher authentication, or general solver qualification. |

The core and source snippets are pinned to `0b4462e3032b4f09230b15329722eabefb7f574c`. The installed empack 0.8.8-beta binary is identified separately by SHA-256. This study does not establish reproducible source-to-installed-binary correspondence. The [source selections](../sources/empack-archives-selections.json) distinguish executed and inspected-only code.

The retained core library and Rust 1.92 compiler were reused after source-tree and artifact checks. The parser harness compiled only its small source adapter. Cargo and the full engine were not built. Private compiler/driver/import processes are terminal; all twelve native import groups were absent after completion. The source process review found no matching driver/compiler/import process. No Java, game, installer, desktop, live project, or host empack upgrade was involved.

## Names are not interchangeable

`ArchiveMemberName` is an exact Unicode name inside an opaque archive. It rejects absolute/drive-prefixed names, traversal, empty components, backslashes, and controls. It retains reserved native names and punctuation. `PortableRelPath` additionally rejects nonportable punctuation, reserved devices, and trailing dots/spaces. Both preserve accepted spelling; neither supplies filesystem access or file integrity.

For example, `CON`, `resource:name`, and `a/C:resource` are accepted opaque names and refused portable destinations. `C:relative` is refused in both roles. Japanese names and both selected composed/decomposed accented spellings are individually accepted. Collision checks remain separate from lexical acceptance.

The opaque index still enforces hierarchical consistency and exact-name uniqueness. Its selected source tests intentionally reject a file named `same` beside `same/child`. Portable indexing additionally applies NFD/casefold/NFD collision keys. Do not replace these profiles with one lowercase filename map, or relax the opaque hierarchy rule merely because a flat ZIP reader can look up arbitrary resource keys. No ZIP-filesystem or modloader compatibility experiment was selected to justify that change.

The successful JAR import retains reserved names, punctuation, and case-distinct resources inside the original JAR bytes. It does **not** establish that `inspect_opaque` ran: the plain import override path copies those bytes, while direct content-kind validation calls that separate inspector. The core API calls and source inspection retain their own scope.

## Raw metadata is an earlier gate

The raw helper checks the end record, disk fields, ZIP64 shape, entry count, metadata allowance, checked directory ranges, central records, declared UTF-8 validity, exact raw-name uniqueness, and final directory count before the ZIP library builds its name index. The fixed metadata allowance bounds central-directory bytes plus ZIP64 extensible data to 16 MiB. Compressed-byte admission alone does not bound that metadata.

The corpus includes valid ZIP32/ZIP64 empty directories, ordinary entries, exact duplicates, a custom small entry cap, missing/trailing end records, disk/range/count/signature errors, bad declared UTF-8, and ZIP64 arithmetic/metadata failures. It does not execute every rejection branch: ZIP64-shape rejection and member-span rejection remain source-modeled only. Forged large declarations remain tiny inputs; no large expansion was attempted.

Raw preflight deliberately admits some inputs that a later stage must reject: traversal, reserved destination names, case/Unicode aliases, and an undeclared high byte do not by themselves fail this metadata gate. Passing preflight grants neither extraction nor integrity. The full importer refuses the selected unsafe outer members, including unused ones, and rejects a selected override with an invalid CRC. The closed import model checks the manifest and selected override payloads; it does not impose CRC verification of unrelated unused payloads.

The encoding supplement distinguishes raw-name uniqueness from decoded destination uniqueness. A flag-clear CP437 byte `0x82` becomes `é` in the successful control. Adding the same decoded path under UTF-8 produces different raw name bytes, so raw duplicate detection alone is insufficient. The full importer correctly refuses that decoded collision. This is evidence for these selected encodings, not every ZIP encoding or extra-field convention.

Cancellation in the source harness is a controlled callback. An empty directory invokes no per-entry callback and succeeds even when the configured first callback would refuse. Nonempty cases stop at the selected entry check. This does not qualify the engine's cancellation, cleanup, or terminal supervision.

## Source trust, extraction, and output verification

Selected source, not fresh execution, establishes these further distinctions:

- `ZipContentSource` checks every member's metadata and attributes, including members not selected for extraction. Linked/encrypted entries are unsupported. It then verifies selected payloads through the decoder, size, source assertions, and private content storage.
- Read/verification work shares an allowance. `read_member` updates its charged counter before propagating the verification error; failed decoder work must not become a free retry. This accounting path was inspected, not executed by the raw preflight harness.
- `ArchiveEvidence` and `MemberEvidence` bind a private extraction observation to the exact verified source archive and member. A known member SHA or cache address is not that private witness. Original archive assertions remain attached to the archive; they must not be fabricated as publisher declarations for every member.
- `VerifiedArchive` checks a generated distribution against the planned inventory. Its byte/member limits are not a universal process-memory ceiling. The selected 7z output verifier explicitly does not configure the decoder's separate allocation limit; it is not the untrusted-import policy.

Keep those guarantees when extracting shared implementation for a browser or desktop authoring engine. Raw input bytes may be retained in an incomplete draft without promoting them into validated members, portable placements, or trusted source assertions. A single string path or Boolean “archive valid” would erase necessary distinctions.

## Models and retained comparison

[Lean](Archives.lean) has twelve laws, and [Bend](Archives.bend) six. They model lexical role admission, ordered metadata guards and entry-check counts, and author publication in the closed local-import profile. The import premise is stored, unencrypted payloads, a valid fixed manifest, no remote files, a fresh destination, and explicit approval. This is not a replacement importer or codec selector.

[Input interpretation](archive_facts.py) reads original bytes and names independently of the observed failure messages. Optional predicate/number fields preserve unreached or unavailable facts. A known earlier rejection may ignore later unknowns; a needed unknown is refused as a study input. `cancelAfter: null` has a different meaning: it selects the known no-injected-cancellation control. Record-witness counts must agree with declarations once those checks are reached.

The [observer](archive_conformance.py) compares 132 scalar values with both models: 68 path admissions, 52 raw-helper stage/count values, and twelve native publication outcomes. The metadata stage tags are study labels, not empack exit codes. The models project decisions and source callback counts; they do not reproduce parser allocations, I/O timing, or scheduler work. Mapping a bare EOF to a directory-read stage is specific to this corpus; it is not a new stable diagnostic API. Python normalization checks cover the selected collision corpus, not arbitrary equivalence with every Rust Unicode table.

Three schema/unknown/witness-count controls, six changed-observation controls, a changed-input digest, and a missing native-metadata fact are refused. The controls pass altered raw path rows and decoded helper observations through the same comparison, rather than merely changing a model constant. [Conformance](../evidence/empack-archives-20261125T135102774049Z/conformance.json) and [basis hashes](../evidence/empack-archives-20261125T135102774049Z/basis.json) record the actual scope.

Compile the two Lean modules into `.build/empack-archives-formal` using the pinned tools, then run:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/archive_conformance.py
```

The comparison reads retained evidence and runs pure models. It does not compile Rust, invoke empack, extract archives, or repeat imports. `archive_probe.py`, `archive_import_probe.py`, and `archive_encoding_probe.py` are separate owner-run collectors, not ordinary CI application collection. Those collectors and their driver are for generated small fixtures, not general untrusted-file tools. The original import collector incorrectly expected general exit 1 for a typed path error that returned 2. Its original three outcomes and producer remain retained; a guarded continuation verified the unchanged fixture before the remaining cases. That expectation failure is not an empack defect.

## Preserve and improve

Keep the current namespace separation, validation of unused metadata, decoded collision checks, and private extraction evidence. The native cases establish no reason to weaken them. Current-source typed path errors correctly produce exit 2; other selected archive faults produce exit 1.

The actionable UX finding is missing entry context in some refusals. Traversal/reserved-name messages report the useful rule but omit the failing entry; CRC refusal says `Invalid checksum`. Existing collision messages already identify a path. Reuse the engine's existing contextual error pattern at archive-entry boundaries, preserving the original typed cause and exit classification. Quote or escape untrusted names; use an entry index/byte context when a name cannot be decoded. Do not introduce a second parser or a new error taxonomy merely to add context.

Any implementation must preserve debit-before-error propagation. Attaching context must not add an early `?` that skips failed-read accounting. The keep-current alternative remains safe refusal with a terse message; it is less actionable for an author diagnosing a large pack. This is a reporting proposal, not a production patch or activation of deferred UX work.

For a later portable extraction, move a cohesive parser/policy boundary only when its callers need it. Reuse the current lexical types, namespace-specific collision rules, limits, and source witnesses. Keep host staging, retention, grants, and native filesystem capabilities explicit. Avoid a crate per predicate and avoid a shadow JavaScript implementation of these rules. A browser quota or worker policy must supply its own admitted budget; native defaults are not its storage or memory contract.

## Dependency changes and remaining evidence

The selected lock declares `zip` 9.8.1, `tar` 0.4.46, `flate2` 1.1.11, `sevenz-rust2` 0.25.0, `unicode-normalization` 0.1.26, and `caseless` 0.2.2, with registry checksums in the source ledger. These are current-source pins, not independently proven dependencies of the installed binary. No local dependency patch was introduced by this band.

When updating these libraries, compile the actual candidate callers and rerun decoder-backed boundaries against that candidate: raw and decoded name aliases, declared encodings, ZIP64/range/count guards, attributes, CRC/size failures, repeated-read allowance, and exact planned output inventories. Preserve weaker original assertions and private container/member binding. Replaying this dependency-free preflight adapter cannot qualify a newly linked ZIP, TAR, or 7z decoder. Changes to Unicode libraries also need fresh native collision checks; identical source code does not establish identical tables.

Unqualified work includes general format sniffing, TAR/7z input and decoder memory limits, all ZIP encodings/extras, encrypted archives, native allowance/witness APIs, strong publisher evidence, actual filesystem extraction races, crash recovery, browser quota/worker behavior, and other hosts/consumers. The full application study remains active and incomplete.
