namespace ApplicationStudy.UpdateFlow

/-- One successful, one-root, snapshot-only fixture. Numbers are equality labels:
    0 absent/automatic, 1 sampled old selection, 2 sampled target. Not SemVer. -/
structure State where
  pin : Nat := 1
  selected : Nat := 0
  payload : Nat := 0
  recipient : Bool := false
  deriving DecidableEq, Repr

inductive Op where
  | syncOld | inspect | held | unpin | automaticPreview | exactPreview | applyExact
  | checkRecorded | materialize | checkOnline | bundled | references | ensure | checkRecipient
  deriving DecidableEq, Repr

/-- Admitted success path only. Source/API/byte assertions and root authority
    are checked by the observer, not inferred from these finite transitions. -/
def step (s : State) : Op → State
  | .syncOld => {s with selected := s.pin, payload := s.pin}
  | .unpin => {s with pin := 0}
  | .applyExact => {s with pin := 2, selected := 2, payload := 0}
  | .materialize => {s with payload := s.selected}
  | .ensure => {s with recipient := true}
  | _ => s

def authorView (s : State) : List Nat := [s.pin,s.selected,s.payload]

/-- Facets have operation-specific meanings, documented in README.md. A
    reference is permitted in recorded checking; it is not a startup proof. -/
def facets (s : State) : Op → List Nat
  | .held => [1,s.selected]
  | .automaticPreview | .exactPreview => [2,1]
  | .checkRecorded | .checkOnline => [1,if s.payload == s.selected then 1 else 0,
      if s.payload == s.selected then 0 else 1]
  | .bundled => [1,0,0]
  | .references => [0,1,0]
  | .ensure => [if s.recipient then 2 else 0,1]
  | .checkRecipient => [1,if s.recipient then 1 else 0,0,1]
  | _ => []

def output (s : State) (op : Op) : List Nat :=
  (if op == .ensure || op == .checkRecipient then [] else authorView s) ++ facets s op

def trace (s : State) : List Op → List (List Nat)
  | [] => []
  | op :: ops => let next := step s op; output next op :: trace next ops

theorem unpin_keeps_selection (s : State) : (step s .unpin).selected = s.selected := by rfl
theorem unpin_keeps_payload (s : State) : (step s .unpin).payload = s.payload := by rfl
theorem automatic_preview_keeps_state (s : State) : step s .automaticPreview = s := by rfl
theorem exact_preview_keeps_state (s : State) : step s .exactPreview = s := by rfl
theorem apply_saves_exact_pin (s : State) : (step s .applyExact).pin = 2 := by rfl
theorem apply_selects_target (s : State) : (step s .applyExact).selected = 2 := by rfl
theorem apply_can_leave_reference (s : State) : (step s .applyExact).payload = 0 := by rfl
theorem materialize_keeps_selection (s : State) : (step s .materialize).selected = s.selected := by rfl
theorem materialize_keeps_pin (s : State) : (step s .materialize).pin = s.pin := by rfl
theorem materialize_binds_selected (s : State) : (step s .materialize).payload = s.selected := by rfl
theorem recorded_reference_complete : facets ⟨2,2,0,false⟩ .checkRecorded = [1,0,1] := by decide
theorem online_materialized_complete : facets ⟨2,2,2,false⟩ .checkOnline = [1,1,0] := by decide
theorem checks_do_not_materialize (s : State) : step s .checkOnline = s ∧ step s .checkRecorded = s := by constructor <;> rfl
theorem bundled_mod_without_bootstrap : facets ⟨2,2,2,false⟩ .bundled = [1,0,0] := by rfl
theorem reference_tool_without_mod_or_subscription : facets ⟨2,2,2,false⟩ .references = [0,1,0] := by rfl
theorem ensure_idempotent (s : State) : step (step s .ensure) .ensure = step s .ensure := by rfl
theorem recipient_does_not_edit_author (s : State) : authorView (step s .ensure) = authorView s := by rfl
theorem recipient_zero_recorded_seeds_keeps_unowned : facets ⟨2,2,2,true⟩ .checkRecipient = [1,1,0,1] := by rfl

end ApplicationStudy.UpdateFlow
