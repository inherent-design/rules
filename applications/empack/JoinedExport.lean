import applications.empack.Authoring

namespace ApplicationStudy.EmpackJoinedExport
open EmpackAuthoring

/-- Study phases: absent, writing, awaiting verification, verified artifact.
    Neither a phase nor an input boolean supplies native/storage authority. -/
structure State where
  phase : Nat
  basis : Nat
  deriving BEq, DecidableEq, Repr
structure Result where
  state : State
  current : Nat
  ok : Bool
  readable : Bool := false
  mayHaveCopied : Bool := false
  removed : Bool := false
  deriving Repr

/-- Action 0 begins; 1 supplies an input; 2 verifies; 3 reads; 4 cancels.
    Admission, input completion, and captured identity are independently
    checked adapter witnesses. This does not model hashing, ZIP, or a sink. -/
def step (s : State) (current action capture : Nat) (admitted finished : Bool) : Result :=
  match action with
  | 0 => if admitted then ⟨⟨if finished then 2 else 1,capture⟩,current,true,false,false,false⟩
         else ⟨s,current,false,false,false,false⟩
  | 1 => if s.phase == 1 || s.phase == 2 then
           if admitted then ⟨⟨if finished then 2 else 1,s.basis⟩,current,true,false,false,false⟩
           else ⟨⟨0,0⟩,current,false,false,false,false⟩
         else ⟨s,current,false,false,false,false⟩
  | 2 => if s.phase == 1 || s.phase == 2 then
           if s.phase == 2 && admitted then ⟨⟨3,s.basis⟩,current,true,false,false,false⟩
           else ⟨⟨0,0⟩,current,false,false,false,false⟩
         else ⟨s,current,false,false,false,false⟩
  | 3 => ⟨s,current,s.phase == 3 && admitted,s.phase == 3 && admitted,false,false⟩
  | 4 => ⟨⟨0,0⟩,current,true,false,s.phase == 3,s.phase != 0⟩
  | _ => ⟨s,current,false,false,false,false⟩

theorem missing_selected_obligation_blocks (p : ExportPlan) (held : List Nat)
    (h : canExport p held = false) (current : Nat) :
    (step ⟨0,0⟩ current 0 p.image (canExport p held) false).ok = false := by
  simp [step,h]
theorem input_complete_is_not_verified (basis current : Nat) :
    (step ⟨1,basis⟩ current 1 0 true true).state = ⟨2,basis⟩ := by simp [step]
theorem unverified_output_is_unreadable (basis current : Nat) :
    (step ⟨2,basis⟩ current 3 0 true false).readable = false := by simp [step]
theorem failed_verification_retires_private_output (basis current : Nat) :
    (step ⟨2,basis⟩ current 2 0 false false).state = ⟨0,0⟩ := by simp [step]
theorem verification_names_captured_image (basis current : Nat) :
    (step ⟨2,basis⟩ current 2 0 true false).state = ⟨3,basis⟩ := by simp [step]
theorem read_preserves_captured_image (basis current : Nat) :
    (step ⟨3,basis⟩ current 3 0 true false).state.basis = basis := rfl
theorem cancel_does_not_claim_ready_bytes_were_never_copied (basis current : Nat) :
    (step ⟨3,basis⟩ current 4 0 true false).mayHaveCopied = true := by simp [step]
theorem cancel_before_verification_does_not_report_copy (basis current : Nat) :
    (step ⟨1,basis⟩ current 4 0 true false).mayHaveCopied = false := by simp [step]
theorem cancel_retires_logical_operation (s : State) (current : Nat) :
    (step s current 4 0 true false).state = ⟨0,0⟩ := rfl
theorem operation_preserves_current_editor (s : State) (current action capture : Nat)
    (admitted finished : Bool) :
    (step s current action capture admitted finished).current = current := by
  unfold step
  split <;> repeat' first | split | rfl

end ApplicationStudy.EmpackJoinedExport
