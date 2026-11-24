# Proposed authoring lifecycle

The [target model](README.md) needs separate answers to three questions: what the user is editing, what image is saved, and which captured inputs an operation owns. [Lean](Authoring.lean) and [Bend](Authoring.bend) model those distinctions. This is proposed protocol behavior. No empack 0.9 implementation, browser project store, or real Prism export is executed by these examples.

## State and premises

An editor has a monotonically advancing edit epoch, a current immutable image identity, an optional saved-image identity, and the last admitted storage revision. Undo and redo select images while advancing the epoch. The saved-image comparison answers whether this image is known to be saved; an absent saved image should be presented as “Not saved yet,” rather than implying an existing file was modified.

Images stand for the complete saveable project projection, not just normalized valid intent. Original raw documents, absent versus empty bindings, virtual sources, authored settings, and unresolved work participate. This model assumes truthful, immutable image identities; it implements no image hashing, raw-document codec, or wire format. Native paths, captions, and provider names do not construct these IDs.

A save receipt concerns a project and session incarnation, identifies the saved image, and carries a host-admitted storage revision. The UI accepts only confirmed receipts for that context. A later-arriving older receipt cannot roll back the known saved basis. A valid newer receipt may describe an older editor image; it updates the saved basis without replacing the current draft. Reopening a project establishes a new context from fresh store observations rather than reusing an old callback.

Storage revision order and confirmed finalization are premises. The actual store must serialize commits or use the agreed expected-revision protocol, handle failures and unknown outcomes, and provide authentic receipts. A public client cannot obtain that authority by sending `confirmed: true`. Logical counters are unbounded naturals in the model; bounded production representations must refuse overflow, not wrap into a previously valid basis.

Background results bind both image and epoch. Returning through undo to the same image does not revive an old operation attempt. The application can retain that old evidence as history, but it cannot silently overwrite the current interpretation. Resource incarnation, capabilities, provider observations, and other operation-specific read sets remain additional bindings outside this small projection.

## Save and export admission

`DraftImage` carries separate available and missing asset references plus authoring validity. Saving requires backing for every available-byte claim; invalid raw authoring and explicitly missing inputs remain saveable. The project format must preserve the original documents and missing references. This readiness predicate does not implement that serialization or prove it lossless.

`ExportPlan` describes one selected recipe's requirements, validated authoring, sufficient source discovery, and required capability admission. It requires the retained inputs that recipe actually consumes. Missing unselected content does not automatically block a narrow export. A remote reference is admissible only under the existing consumer/source-evidence contract; this model does not decide whether an arbitrary missing file qualifies as one.

A complete source-discovery claim and retained-byte coverage are different facts. Discovery completeness is scoped to the selected operation. An unobserved layer or source that could affect the recipe cannot be labeled complete merely because the known assets are present. Conversely, the planner should not read or block on unrelated content without a semantic or safety dependency.

Prepared work retains immutable inputs independently of later edits. A captured export may finish for its image while the editor moves forward. That receipt names the captured image and does not mean the current image was exported or saved. Retention and final verification must remain valid through writer finalization. This model establishes neither those storage leases nor actual output bytes; the native publisher and browser sink have their own completion contracts.

## Proposed joined example

The [fixture](fixtures/authoring.json) uses symbolic image and asset IDs. Its [expected outcomes](fixtures/expected.json) are manually specified design expectations, not translated native observations. The fixture action format is harness input, not a proposed public command or SDK schema.

| Transition | Expected result |
| --- | --- |
| Edit saved image 10 into image 20 | Epoch advances; the new image is unsaved. |
| Old background result arrives | Its epoch/image basis is rejected. |
| Image 20 save is confirmed | Image 20 becomes the saved basis. |
| Edit into image 30, then an older save reply arrives | Current image 30 remains; older storage revision is ignored. |
| A newer confirmed receipt names captured image 20 | Saved basis updates, while image 30 remains unsaved. |
| Undo into saved image 20 | Image is saved again despite a larger edit epoch. |
| Background result from the previous image-20 attempt arrives | Same image is insufficient; the old epoch is rejected. |
| Foreign-project, old-incarnation, or unconfirmed save arrives | Editor state remains unchanged. |

Seven readiness examples cover malformed authoring, a missing required local file, an unretained available-byte claim, missing unselected content, incomplete discovery, an unavailable capability, and a complete local-JAR/configuration pair. They establish intended admission decisions only. They are not an import, preview, project container round-trip, or actual consumer artifact.

The collection example composes saved, current, undo/redo, prepared-plan, and pending-operation roots. Each category has a uniquely retained asset; one unrelated stored asset is collectible. It reuses `Lifecycle.gc` and proves plan/history membership preservation. The host protocol must supply complete roots and coordinate publication and collection. Pure filtering alone does not qualify concurrent storage cleanup. Provenance/history edges that do not retain bytes must not be mistaken for retaining edges.

## Laws and comparisons

Thirteen Lean laws cover epoch progression, return to saved image, late and out-of-order receipts, project/incarnation/finalization admission, stale background rejection, save/export separation, and plan/history retention. Four Bend laws cover epoch progression, return to saved image, invalid-export refusal, and the natural-number equality helper used in that proof. The Bend executable projection also compares the receipt, background, and readiness examples.

[Replay](authoring_conformance.py) compares twelve editor states and seven readiness cases with both models, checks the shared Lean retention example, and refuses an unsupported action. It does not compare a future implementation with a model. Its report explicitly says “proposed protocol examples.” Compile `Authoring.lean` to `.build/applications/empack/Authoring.olean` first, with shared modules available under `.build/formal`, then run:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/authoring_conformance.py
```

The native VS Code undo observation supplies a counterexample to using an event clock as save-state identity. The vscode.dev reload observation shows why restored visible text is not file-save evidence. Its handle-registry fragments show why a name-based alias and in-memory success cannot supply immutable identity or persisted registration. The restic and Cargo bands keep retention, selections, built outputs, and external effects distinct. These comparisons motivate the design; none proves native or browser empack conformance.

## Required implementation evidence

Implement the actual local JAR/configuration flow: capture inputs, edit metadata and placement, preview, save an incomplete project, supply missing content, save/reopen, prepare a Prism snapshot, verify output, and finish delivery. Compare native and browser semantic inventories and portable attributes, and qualify the supported consumer interpretation separately. Bind every step to the actual project image and retained inputs.

Interrupt bytes-before-metadata save boundaries and export finalization. Exercise quota/full-disk failures, concurrent tabs, stale grants, wrong project/incarnation receipts, worker loss, permissions, missing retained backing, and history/plan/pending retention during cleanup. Unknown completion must remain inspectable without discarding newer edits or recovery data. Actual browser storage and download behavior remains required evidence; these pure examples cannot substitute for it.

The later [storage feasibility band](PORTABLE-STORAGE.md) executes actual browser import, incomplete save/reopen, study-backup download, and separate native export comparisons. It remains a research-only host prototype with formal comparison pending; it implements neither the portable engine nor the production project format, so the complete joined scenario above stays open.
