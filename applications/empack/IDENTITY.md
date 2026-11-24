# Native identity, retained evidence, and recovery authority

This is a bounded source/native/model band for checkout `0b4462e3032b4f09230b15329722eabefb7f574c`. It executes selected unchanged identity, binding, and fingerprint code on macOS. Lean and Bend compare the retained source-function results. It does not run a reboot, an installed-CLI recovery, or the complete engine, and it qualifies no complete native state or recovery workflow.

## Executed boundary

The [collector](identity_probe.py) compiles a small [caller](identity_oracle.rs) against existing attributed Rust dependencies. It includes the actual `ObjectIdentity` type/getter, macOS persistent-identity provider, journal-binding module, root-key and association predicates, portable-path module, and snapshot fingerprint function. The [ledger](../sources/empack-identity-selections.json) separates compiled selections from inspected callers and tests. No Cargo or full engine build occurs.

The [receipt](../evidence/empack-identity-20261124T193525996513Z/receipt.json) records exact source, compiler, dependency, generated-input, and binary identities. The 58 retained results comprise 12 identity pairs, nine optional journal comparisons, 12 journal-binding codec inputs, 12 fingerprint pairs, five association-predicate cases, and eight injected error classifications. Real filesystem operations use six small private files and three fixture directories. The native executable is approximately 1.9 MB. No project, production journal, operation store, launcher, or game is accessed.

Snapshot entries are assembled by the fixture from native observations. Their unused capture-group marker supplies no real scope, filter, capture, or revalidation behavior. The association predicate receives a binding-only root adapter and a valid typed schema-1 association; discovery, bounded record reads, locks, and root authority are excluded. Source tests and complete recovery callers were inspected, not executed by this band.

## Distinct meanings

**Live identity remains strict.** The actual derived equality includes the current volume/device value, object number, creation evidence, and persistent token. Renaming an open file or reopening its new path retains equality here. A newly created same-byte file at the old path and a copied file are different objects. Neither filename nor content equality adopts an object.

**Durable comparison has a different purpose.** The macOS provider derives its token from filesystem UUID, object number, and creation evidence. A controlled change to the supplied device field preserves that token while changing live equality. This models the intended boot-local difference; it is not an observed reboot or an operating-system identifier change. Synthetic object-number and creation-field changes produce different tokens in these cases. Token outputs remain opaque evidence; this is not a proof of hash collision resistance or every filesystem provider.

**Object identity is not content identity.** Content edits and permission changes retain the same object/token in the fixture. The snapshot fingerprint still changes with observed content, mode, read-only state, placement, membership, or a new occupant. Same-byte replacement also changes the fingerprint because its object evidence differs. A matching journal object token does not verify those other facts by itself.

**Missing evidence is not absence.** `matches_optional(None, None)` matches a declared absent-before/absent-now pair. An existing observed object without a durable token does not match a saved binding. Capturing an unavailable binding fails. The strict journal-binding codec accepts only its expected 32-byte field; legacy live-identity fields, duplicates, missing fields, and invalid bytes are rejected. This is an inner binding codec, not validation of a complete recovery journal or a migration path.

**The retained state key need not equal a newly computed key.** The source key includes the original live device value. The controlled device-change case produces a different current key while the original association predicate still matches persistent identity. The predicate rejects a moved/misnamed state record and cannot verify an association when durable evidence is unavailable. These are predicate observations; the actual state-directory scan, its entry limit, and coordination are not exercised. A valid historical original key must not be labeled stale merely because its spelling differs from a current key.

**Availability retains a capability boundary.** Injected unsupported/permission errno values return unavailable evidence, while the tested unrelated errors remain errors. These are calls to the unchanged classifier, not reproduced permission incidents. Unavailability does not silently become durable identity or grant recovery authority.

The [observation checker](identity_observations.py) verifies source/artifact/stream identities, six post-run files, and independently reconstructs the snapshot encoding with Python. Twenty-two valid fingerprint sides match byte-for-byte; two sides report missing durable evidence without a fallback digest. The [summary](identity-observations.json) separates native observations, synthetic fields, supplied wire inputs, and assembled snapshots. It runs no native program or state operation. The [formal comparison](../evidence/empack-identity-20261124T193525996513Z/conformance.json) separately checks all 58 results against [Lean](Identity.lean) and [Bend](Identity.bend).

## API and interface direction

Preserve the existing distinction between `ObjectIdentity`, `JournalBinding`, `Binding`, `FileObservation`, and `NativeSnapshot`. Their fields can share machine representations without sharing authority. A durable native comparison is also host-specific evidence, not a portable pack/content revision or a reconstructed read capability. The source revalidation path retains fresh native checks independently of persisted fingerprints; those callers still require joined qualification.

One possible reporting improvement is retaining why durable evidence is unavailable. The current classifier deliberately collapses unsupported capability and selected permission failures into `None`, which lets live observations continue. A caller that needs persistence must still refuse. Review existing diagnostics before choosing an additional typed reason or companion report; do not weaken that refusal or introduce another identity fallback merely to improve wording. The injected cases do not establish a current host permission problem.

## Models and replay

The models distinguish strict live equality, durable token comparison, optional absence, inner binding shape, structural fingerprint inputs, association naming, and selected availability classes. Lean provides 23 laws, and Bend provides 12. The [research decoder](IdentityCase.lean) rejects 14 unsupported inputs, including repeated or unordered paths, inconsistent node payloads, invalid equality labels, and unknown profiles. These are research refusals, not additional production validation.

The [replay](identity_conformance.py) derives inputs from raw recorded values and compares both models with all 58 retained outcomes. Per-field injective labels preserve equality without treating large inode numbers or hashes as arithmetic. Duplicate-preserving JSON parsing keeps repeated members visible. Numeric atom magnitudes saturate at 256 because this shape predicate distinguishes only sign and byte range; successful decoded bytes are checked separately. The models do not parse JSON text or implement SHA-256. Python independently reconstructs 22 valid hash-input encodings and checks the two unavailable sides.

Association names are recomputed from the original raw binding and the fixture's wrong-name request. The native wrapper stored its pre-call record/name arguments alongside its outcome; the replay verifies those arguments rather than feeding the returned match or error into a model. Snapshot comparisons retain canonical path and directory-member order as an explicit premise. Structural equality predicts the observed digest comparisons only for these inputs; it supplies no cryptographic injectivity proof or execution permission.

Run retained-data comparison without starting empack or rustc:

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/empack/identity_conformance.py
```

The subsequent [discovery band](ROOT-STATE.md) executes selected actual root checks, association reads, and lookup through native directory capabilities. It also retains a separate initialization-lock prefix. Lean and Bend compare its admission and selected-key results; the complete writer/recovery lifecycle remains pending.

## Remaining qualification

Continue caller-bound state lookup, read-only recovery planning, operation/revision approval, restoration direction, retained-image verification, and interrupted publication/creation. The separate discovery band does not yet qualify those complete lifecycles. Use isolated fixtures and preserve the distinction between source methods, current checkout, and installed release behavior. Linux/Windows providers, actual reboot behavior, root capture/revalidation, outer record admission, and complete recovery remain pending. Live user recovery state remains outside this study.
