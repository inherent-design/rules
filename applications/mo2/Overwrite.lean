namespace ApplicationStudy.Mo2Overwrite

/-- Origin 0 is the fixture overwrite entry; -1 is the UI's don't-sync choice.
    Other labels are not priority ranks. Eligibility/order is supplied by the
    surrounding virtual directory, not implemented here. -/
def options (metadata known : Bool) (primary : Int) (alternatives : List Int) : Option (List Int) :=
  if metadata then none
  else if !known then some [-1]
  else some ([-1] ++ (primary :: alternatives).filter (· != 0))

def defaultChoice (values : Option (List Int)) : Option Int := values.bind List.getLast?

def selected (values : Option (List Int)) (choice : Option Int) : Option Int :=
  match values with
  | none => none
  | some values => if let some choice := choice then
      if values.contains choice then some choice else none
    else values.getLast?

/-- Backing labels distinguish regular payloads from moved symlink objects in
    the replay. The model never dereferences them or decodes filesystem paths. -/
structure Files where
  source : Option Nat
  destination : Option Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Failure | none | remove | move
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
structure Outcome where
  files : Files
  failure : Failure
  retainedPrior : Option Nat
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

/-- Primitive outcomes are source/host witnesses. `removeOk` includes the
    destination effect; `moveOk` includes the moved backing and source removal.
    This is not a permission simulator or a Qt rename implementation. -/
def applyCurrent (files : Files) (choice : Option Int) (removeOk moveOk : Bool) : Outcome :=
  if choice.isNone || choice == some (-1) then ⟨files,.none,none⟩
  else if !removeOk then ⟨files,.remove,none⟩
  else if !moveOk then ⟨{files with destination := none},.move,none⟩
  else ⟨⟨none,files.source⟩,.none,none⟩

/-- Design comparison only: a verified retained old backing exists before the
    destructive step. This supplies no native backup/storage implementation. -/
def withRetainedPrior (files : Files) (choice : Option Int) (removeOk moveOk : Bool) : Outcome :=
  let out := applyCurrent files choice removeOk moveOk
  if out.failure == .move then {out with retainedPrior := files.destination} else out

def priorRecoverable (before : Files) (out : Outcome) : Prop :=
  before.destination = none ∨ out.files.destination = before.destination ∨ out.retainedPrior = before.destination

def original : Files := ⟨some 1,some 2⟩

theorem metadata_is_not_offered (known : Bool) (p : Int) (alts : List Int) :
    options true known p alts = none := rfl

theorem unknown_file_defaults_to_no_sync (p : Int) (alts : List Int) :
    options false false p alts = some [-1] := rfl

theorem overwrite_is_not_destination : options false true 0 [0] = some [-1] := by decide

theorem supplied_last_alternative_is_default : defaultChoice (options false true 0 [1,2]) = some 2 := by decide

theorem invalid_choice_is_not_admitted : selected (options false true 0 [1]) (some 2) = none := by decide

theorem no_widget_does_not_move (files : Files) (remove move : Bool) :
    applyCurrent files none remove move = ⟨files,.none,none⟩ := by simp [applyCurrent]

theorem do_not_sync_preserves_files (files : Files) (remove move : Bool) :
    applyCurrent files (some (-1)) remove move = ⟨files,.none,none⟩ := by simp [applyCurrent]

theorem failed_remove_preserves_backings :
    (applyCurrent original (some 1) false true).files = original := by decide

theorem failed_move_after_remove_loses_current_destination :
    (applyCurrent original (some 1) true false).files = ⟨some 1,none⟩ := by decide

theorem current_move_failure_does_not_retain_old_backing :
    ¬ priorRecoverable original (applyCurrent original (some 1) true false) := by
  simp [priorRecoverable,original,applyCurrent]

theorem source_missing_does_not_prevent_destination_remove :
    (applyCurrent ⟨none,some 2⟩ (some 1) true false).files = ⟨none,none⟩ := by decide

theorem confirmed_move_changes_backing_role :
    (applyCurrent original (some 1) true true).files = ⟨none,some 1⟩ := by decide

theorem proposed_retention_keeps_old_failure_backing :
    priorRecoverable original (withRetainedPrior original (some 1) true false) := by
  simp [priorRecoverable,original,withRetainedPrior,applyCurrent]

theorem proposed_retention_preserves_current_file_outcome (files : Files) (choice : Option Int) (r m : Bool) :
    (withRetainedPrior files choice r m).files = (applyCurrent files choice r m).files := by
  simp only [withRetainedPrior]; split <;> rfl

theorem proposed_move_failure_retains_actual_prior_label (files : Files) (choice : Option Int) (r m : Bool)
    (h : (applyCurrent files choice r m).failure = .move) :
    (withRetainedPrior files choice r m).retainedPrior = files.destination := by
  simp [withRetainedPrior,h]

end ApplicationStudy.Mo2Overwrite
