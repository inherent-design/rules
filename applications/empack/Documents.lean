namespace ApplicationStudy.EmpackDocuments

/-- The two deliberately varied semantic fields, not a replacement author
    schema or general canonical encoder. Everything else is fixed by fixture. -/
structure Meaning where
  name : Nat
  seedPayload : Bool
  deriving BEq, DecidableEq, Repr

structure Basis where
  author : String
  bindings : Option String
  lock : Option String
  deriving BEq, DecidableEq, Repr

structure State where
  basis : Basis
  meaning : Meaning
  locked : Option Meaning
  valid : Bool
  deriving Repr

def lockCurrent (state : State) : Bool := state.valid && state.locked == some state.meaning

/-- Necessary document precondition, not an execution grant. Engine identity,
    root observations, resource admission and native revalidation remain outside. -/
def documentGate (prepared : Basis) (current : State) : Bool := prepared == current.basis

/-- Symbolic effect on the fixture meaning, after separately established host
    admission. Rejected work preserves the current value, including later edits. -/
def record (prepared : Basis) (current : State) (approved otherChecks : Bool)
    (writtenLock : String) : State :=
  if approved && otherChecks && current.valid && documentGate prepared current then
    {current with basis := {current.basis with lock := some writtenLock}, locked := some current.meaning}
  else current

def inspect (state : State) : String :=
  if !state.valid then "invalid" else if lockCurrent state then "current" else "stale"

theorem raw_comment_change_can_keep_lock_current (raw2 : String) :
    let meaning : Meaning := ⟨0,true⟩
    lockCurrent ⟨⟨raw2,none,some "saved-lock"⟩,meaning,some meaning,true⟩ = true := rfl

theorem absent_is_not_present_empty (raw lock : String) :
    Basis.mk raw none (some lock) ≠ Basis.mk raw (some "empty") (some lock) := by
  intro h
  have impossible := congrArg Basis.bindings h
  cases impossible

theorem semantic_match_does_not_supply_raw_write_authority :
    let meaning : Meaning := ⟨0,false⟩
    let current : State := ⟨⟨"later-comment",none,some "saved-lock"⟩,meaning,some meaning,true⟩
    lockCurrent current = true ∧ documentGate ⟨"earlier",none,some "saved-lock"⟩ current = false := by constructor <;> rfl

theorem declined_work_preserves_current (basis : Basis) (current : State) (other : Bool) (written : String) :
    record basis current false other written = current := rfl

theorem other_admission_cannot_be_inferred_from_matching_documents (basis : Basis) (current : State) (written : String) :
    record basis current true false written = current := by simp [record]

theorem stale_raw_basis_preserves_current (basis : Basis) (current : State)
    (written : String) (h : documentGate basis current = false) :
    record basis current true true written = current := by simp [record, h]

theorem recording_preserves_raw_author_inputs (basis : Basis) (current : State) (approved other : Bool) (written : String) :
    let after := record basis current approved other written
    (after.basis.author, after.basis.bindings) = (current.basis.author, current.basis.bindings) := by
  unfold record; split <;> rfl

theorem invalid_state_cannot_be_recorded (basis : Basis) (current : State)
    (written : String) (h : current.valid = false) : record basis current true true written = current := by simp [record, h]

theorem recorded_metadata_does_not_change_intent (basis : Basis) (current : State) (written : String) :
    (record basis current true true written).meaning = current.meaning := by unfold record; split <;> rfl

theorem admitted_record_sets_written_lock (basis : Basis) (current : State) (written : String)
    (hv : current.valid = true) (hg : documentGate basis current = true) :
    (record basis current true true written).basis.lock = some written := by simp [record, hv, hg]

end ApplicationStudy.EmpackDocuments
