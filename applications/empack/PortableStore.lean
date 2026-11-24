import applications.empack.Authoring

namespace ApplicationStudy.EmpackPortableStore
open EmpackAuthoring

/-- Semantic image labels are externally checked witnesses, not opaque backing
    handles, native capabilities, hashes computed by this model, or validity. -/
structure Stored where
  revision : Nat
  image : Option ImageId
  deriving BEq, DecidableEq, Repr
structure Result where
  stored : Stored
  editor : Editor
  status : Nat -- observed/confirmed/unknown/conflict/unavailable/reopened/backup
  deriving Repr

def observe (s : Stored) (e : Editor) : Result := ⟨s,e,0⟩
/-- Boundary 0 is after private allocation but before verification, 1 after
    verification but before metadata, 2 after commit without reply, 3 replied.
    These are host observations; public flags cannot manufacture receipts. -/
def save (s : Stored) (e : Editor) (expected : Nat) (image : DraftImage)
    (verified : List Nat) (boundary : Nat) : Result :=
  if boundary == 0 then ⟨s,e,2⟩ else
  if !canSave image verified then ⟨s,e,4⟩ else
  if boundary == 1 then ⟨s,e,2⟩ else
  if expected != s.revision then ⟨s,e,3⟩ else
  let stored := Stored.mk (s.revision + 1) (some image.id)
  if boundary == 2 then ⟨stored,e,2⟩
  else ⟨stored,saveCompleted e stored.revision image.id,1⟩
def reopen (s : Stored) (e : Editor) (verified : Bool) : Result :=
  match s.image with
  | none => ⟨s,e,4⟩
  | some image => if !verified then ⟨s,e,4⟩ else
      ⟨s,⟨e.epoch + 1,image,some image,s.revision⟩,5⟩
/-- Backup delivery admission is about available-byte coverage and actual sink
    completion, not authoring validity or distribution-execution capability. -/
def backup (s : Stored) (e : Editor) (verified finalized : Bool) : Result :=
  ⟨s,e,if s.image.isSome && verified && finalized then 6 else 4⟩
/-- The fault experiment requests ordinary reopen, then ordinary save. Its only
    captured UI snapshot is after both calls; do not invent an intermediate one. -/
def reopenThenSave (s : Stored) (e : Editor) (verifiedBacking : Bool)
    (image : DraftImage) (verified : List Nat) (boundary : Nat) : Result :=
  let opened := reopen s e verifiedBacking
  save opened.stored opened.editor opened.editor.savedRevision
    {image with id := opened.editor.current} verified boundary

structure Asset where
  handle : Nat
  digest : Nat
  bytes : Nat
  deriving BEq, DecidableEq, Repr
def semanticAsset (a : Asset) := (a.digest,a.bytes)
def verifiedAsset (expected actual : Asset) (readable : Bool) : Bool :=
  readable && expected.handle == actual.handle && expected.digest == actual.digest && expected.bytes == actual.bytes

theorem handle_is_not_content (a : Asset) (handle : Nat) :
    semanticAsset {a with handle := handle} = semanticAsset a := rfl
theorem same_digest_does_not_grant_another_handle :
    verifiedAsset ⟨1,5,8⟩ ⟨2,5,8⟩ true = false := by decide
theorem corrupt_referenced_bytes_are_not_verified :
    verifiedAsset ⟨1,5,8⟩ ⟨1,6,8⟩ true = false := by decide
theorem unreadable_is_not_verified (a : Asset) : verifiedAsset a a false = false := by simp [verifiedAsset]
theorem created_file_is_not_saved_metadata (s : Stored) (e : Editor) (n : Nat)
    (d : DraftImage) (held : List Nat) :
    (save s e n d held 0).stored = s ∧ (save s e n d held 0).editor = e ∧ (save s e n d held 0).status = 2 := by
  simp [save]
theorem missing_available_claim_cannot_commit (s : Stored) (e : Editor) (n : Nat)
    (d : DraftImage) (held : List Nat) (h : canSave d held = false) :
    (save s e n d held 3).stored = s ∧ (save s e n d held 3).status = 4 := by simp [save,h]
theorem retained_bytes_without_metadata_keep_old_root (s : Stored) (e : Editor) (n : Nat)
    (d : DraftImage) (held : List Nat) (h : canSave d held = true) :
    (save s e n d held 1).stored = s ∧ (save s e n d held 1).editor = e := by simp [save,h]
theorem stale_request_keeps_root (s : Stored) (e : Editor) (n : Nat)
    (d : DraftImage) (held : List Nat) (h : canSave d held = true) (stale : n != s.revision) :
    (save s e n d held 3).stored = s ∧ (save s e n d held 3).status = 3 := by simp [save,h,stale]
theorem committed_without_reply_keeps_UI_basis (s : Stored) (e : Editor)
    (d : DraftImage) (held : List Nat) (h : canSave d held = true) :
    (save s e s.revision d held 2).stored = ⟨s.revision+1,some d.id⟩ ∧
    (save s e s.revision d held 2).editor = e ∧
    (save s e s.revision d held 2).status = 2 := by simp [save,h]
theorem confirmed_save_names_captured_image (s : Stored) (e : Editor)
    (d : DraftImage) (held : List Nat) (h : canSave d held = true) :
    (save s e s.revision d held 3).stored.image = some d.id := by simp [save,h]
theorem confirmation_does_not_replace_current_edits (s : Stored) (e : Editor)
    (d : DraftImage) (held : List Nat) (h : canSave d held = true) :
    (save s e s.revision d held 3).editor.current = e.current := by simp [save,h,saveCompleted]; split <;> rfl
theorem confirmation_does_not_rewind_epoch (s : Stored) (e : Editor)
    (d : DraftImage) (held : List Nat) (h : canSave d held = true) :
    (save s e s.revision d held 3).editor.epoch = e.epoch := by simp [save,h,saveCompleted]; split <;> rfl
theorem invalid_authoring_and_missing_refs_are_saveable :
    (save ⟨0,none⟩ ⟨1,10,none,0⟩ 0 ⟨10,false,[1,2],[3]⟩ [1,2] 3).status = 1 := by decide
theorem same_image_can_have_a_later_storage_revision :
    (save ⟨1,some 10⟩ ⟨1,10,some 10,1⟩ 1 ⟨10,false,[1],[]⟩ [1] 3).stored = ⟨2,some 10⟩ := by decide
theorem reopen_uses_fresh_storage_revision :
    (reopen ⟨4,some 20⟩ ⟨8,30,some 10,3⟩ true).editor = ⟨9,20,some 20,4⟩ := by decide
theorem failed_reopen_then_unverified_save_keeps_record (s : Stored) (e : Editor)
    (d : DraftImage) (held : List Nat)
    (h : canSave {d with id := e.current} held = false) :
    (reopenThenSave s e false d held 3).stored = s ∧
    (reopenThenSave s e false d held 3).editor = e := by
  cases hi : s.image <;> simp [reopenThenSave,reopen,hi,save,h]
theorem failed_reopen_preserves_unsaved_draft (s : Stored) (e : Editor) :
    (reopen s e false).editor = e := by cases h : s.image <;> simp [reopen,h]
theorem download_request_is_not_delivery (s : Stored) (e : Editor) (v : Bool) :
    (backup s e v false).status = 4 := by simp [backup]
theorem backup_cannot_replace_current_editor (s : Stored) (e : Editor) (v f : Bool) :
    (backup s e v f).editor = e := rfl

end ApplicationStudy.EmpackPortableStore
