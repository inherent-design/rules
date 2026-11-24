import common.Lifecycle

namespace ApplicationStudy.EmpackAuthoring

/-- IDs stand for admitted immutable project images, not filenames, UI captions,
    native inodes, or a specified wire hash. -/
abbrev ImageId := Nat

structure Editor where
  epoch : Nat
  current : ImageId
  saved : Option ImageId
  savedRevision : Nat
  deriving DecidableEq, Repr

def dirty (s : Editor) : Bool := s.saved != some s.current

/-- Includes undo/redo: revisiting an old image still advances the operation epoch. -/
def editTo (s : Editor) (image : ImageId) : Editor :=
  { s with epoch := s.epoch + 1, current := image }

/-- Receipt revision is a host-admitted serialized save revision, not completion
    arrival order. Unknown/unfinalized saves must not call this transition. -/
def saveCompleted (s : Editor) (revision : Nat) (image : ImageId) : Editor :=
  if revision > s.savedRevision then
    { s with saved := some image, savedRevision := revision }
  else s

structure Context where
  project : Nat
  incarnation : Nat
  editor : Editor
  deriving Repr

/-- Candidate input projection after host evidence admission. `confirmed` is
    not a public caller-controlled substitute for a commit capability. -/
structure SaveReceipt where
  project : Nat
  incarnation : Nat
  revision : Nat
  image : ImageId
  confirmed : Bool
  deriving Repr

def acceptSave (context : Context) (receipt : SaveReceipt) : Context :=
  if receipt.confirmed && receipt.project == context.project && receipt.incarnation == context.incarnation then
    { context with editor := saveCompleted context.editor receipt.revision receipt.image }
  else context

def acceptsBackground (s : Editor) (epoch : Nat) (image : ImageId) : Bool :=
  s.epoch == epoch && s.current == image

structure DraftImage where
  id : ImageId
  validAuthoring : Bool
  available : List Nat
  missing : List Nat
  deriving Repr

/-- Incomplete/invalid raw drafts remain saveable. Every available-byte claim
    must be retained first. Missing references remain explicit project data. -/
def canSave (image : DraftImage) (stored : List Nat) : Bool :=
  image.available.all stored.contains

structure ExportPlan where
  image : ImageId
  validAuthoring : Bool
  discoveryComplete : Bool
  capable : Bool
  required : List Nat
  deriving Repr

/-- Selected-recipe obligations only. An excluded or admissible remote reference
    is not automatically a required local payload. No actual codec is modeled. -/
def canExport (plan : ExportPlan) (held : List Nat) : Bool :=
  plan.validAuthoring && plan.discoveryComplete && plan.capable && plan.required.all held.contains

structure Retention where
  saved : List Nat
  current : List Nat
  history : List Nat
  plans : List Nat
  pending : List Nat
  deriving Repr

def roots (r : Retention) := r.saved ++ r.current ++ r.history ++ r.plans ++ r.pending

theorem edit_advances_epoch (s : Editor) (image : ImageId) :
    (editTo s image).epoch = s.epoch + 1 := rfl

theorem undo_to_saved_image_is_clean (s : Editor) (image : ImageId)
    (h : s.saved = some image) : dirty (editTo s image) = false := by
  simp [dirty, editTo, h]

theorem late_save_preserves_current (s : Editor) (revision image : Nat) :
    (saveCompleted s revision image).current = s.current := by
  unfold saveCompleted
  split <;> rfl

theorem older_receipt_ignored (s : Editor) (revision image : Nat)
    (h : revision ≤ s.savedRevision) : saveCompleted s revision image = s := by
  simp [saveCompleted, Nat.not_lt.mpr h]

theorem unconfirmed_save_does_not_change_state (context : Context) (receipt : SaveReceipt) :
    acceptSave context {receipt with confirmed := false} = context := by
  simp [acceptSave]

theorem foreign_project_receipt_rejected (context : Context) (receipt : SaveReceipt)
    (h : receipt.project ≠ context.project) : acceptSave context receipt = context := by
  simp [acceptSave, h]

theorem old_incarnation_receipt_rejected (context : Context) (receipt : SaveReceipt)
    (h : receipt.incarnation ≠ context.incarnation) : acceptSave context receipt = context := by
  simp [acceptSave, h]

theorem changed_epoch_rejects_background (s : Editor) (image : ImageId) :
    acceptsBackground (editTo s image) s.epoch image = false := by
  simp [acceptsBackground, editTo]

theorem authoring_validity_does_not_control_save (image : DraftImage) (stored : List Nat) :
    canSave {image with validAuthoring := false} stored = canSave image stored := rfl

theorem invalid_authoring_blocks_export (plan : ExportPlan) (stored : List Nat) :
    canExport {plan with validAuthoring := false} stored = false := by
  simp [canExport]

theorem incomplete_discovery_blocks_export (plan : ExportPlan) (stored : List Nat) :
    canExport {plan with discoveryComplete := false} stored = false := by
  simp [canExport]

theorem planned_asset_survives_collection (r : Retention) (stored : List Nat) (asset : Nat)
    (held : asset ∈ r.plans) (present : asset ∈ stored) :
    asset ∈ Lifecycle.gc (roots r) stored := by
  apply Lifecycle.retained_survives _ _ _ _ present
  simp [roots, held]

theorem historical_asset_survives_collection (r : Retention) (stored : List Nat) (asset : Nat)
    (held : asset ∈ r.history) (present : asset ∈ stored) :
    asset ∈ Lifecycle.gc (roots r) stored := by
  apply Lifecycle.retained_survives _ _ _ _ present
  simp [roots, held]

end ApplicationStudy.EmpackAuthoring
