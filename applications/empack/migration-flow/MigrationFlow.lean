namespace ApplicationStudy.MigrationFlow

/-- Captured two-project profile. IDs: 0automatic/absent,1wmIZ4wP4,2sOzRw3CG;
    game1=1.21.1,game2=1.21. Target metadata admits selection1,not2.
    Eligibility is a sampled fixture premise, not a verified catalog algorithm. -/
structure State where
  pin : Nat
  selected : Nat := 0
  game : Nat := 1
  payload : Nat := 0
  deriving DecidableEq, Repr
inductive Op where | sync | prefixPreview | preview | apply | unpin | check
  deriving DecidableEq, Repr
def canonical (proposed : Bool) (op : Op) : Op :=
  if proposed && op == .prefixPreview then .preview else op
def eligible (s : State) : Bool := s.pin != 2
def code (s : State) (op : Op) (proposed : Bool := false) : Nat :=
  match canonical proposed op with
  | .prefixPreview => 2
  | .preview | .apply => if eligible s then 0 else 4
  | _ => 0
def step (s : State) (op : Op) : State :=
  match op with
  | .sync => {s with selected := s.pin}
  | .unpin => {s with pin := 0}
  | .apply => if eligible s then {s with selected := 1, game := 2} else s
  | _ => s
def projectChanges (s : State) (op : Op) : List String :=
  match op with
  | .sync => if s.selected == 0 then ["empack.lock"] else []
  | .unpin => if s.pin != 0 then ["empack.lock", "empack.yml"] else []
  | .apply => if eligible s && s.game != 2 then ["empack.lock", "empack.yml"] else []
  | _ => []
def stateChanged (s : State) (op : Op) : Bool := !(projectChanges s op).isEmpty
def facet (s : State) (op : Op) (proposed : Bool := false) : List Nat :=
  match canonical proposed op with
  | .preview => if eligible s then [1,1,2,0] else []
  | .check => [1,0,1]
  | _ => []
/-- Proposed post-parse JSON mode guard, not a patched parser. -/
def jsonModeAllowed (preview : Bool) : Bool := preview

theorem unpin_retains_exact_selection (s : State) : (step s .unpin).selected = s.selected := by rfl
theorem unpin_is_not_runtime_change (s : State) : (step s .unpin).game = s.game := by rfl
theorem unpin_does_not_materialize (s : State) : (step s .unpin).payload = s.payload := by rfl
theorem preview_retains_state (s : State) : step s .preview = s := by rfl
theorem incompatible_pin_blocks_application : step ⟨2,2,1,0⟩ .apply = ⟨2,2,1,0⟩ ∧ code ⟨2,2,1,0⟩ .apply = 4 := by decide
theorem incompatible_pin_has_no_project_effect : projectChanges ⟨2,2,1,0⟩ .apply = [] := by decide
theorem compatible_pin_survives_application : step ⟨1,1,1,0⟩ .apply = ⟨1,1,2,0⟩ := by decide
theorem automatic_application_does_not_mint_pin : step ⟨0,2,1,0⟩ .apply = ⟨0,1,2,0⟩ := by decide
theorem first_sync_records_reference : step ⟨1,0,1,0⟩ .sync = ⟨1,1,1,0⟩ := by rfl
theorem successful_application_changes_two_documents : projectChanges ⟨1,1,1,0⟩ .apply = ["empack.lock", "empack.yml"] := by decide
theorem check_is_not_materialization (s : State) : step s .check = s := by rfl
theorem recorded_reference_can_be_complete : facet ⟨1,1,2,0⟩ .check = [1,0,1] := by rfl
theorem current_prefix_refuses_without_changes (s : State) : code s .prefixPreview = 2 ∧ projectChanges s .prefixPreview = [] := by constructor <;> rfl
theorem suffix_preview_is_ready_without_publication : facet ⟨1,1,1,0⟩ .preview = [1,1,2,0] := by decide
theorem proposed_prefix_has_same_code_as_suffix (s : State) : code s .prefixPreview true = code s .preview := by rfl
theorem proposed_prefix_has_same_facet_as_suffix (s : State) : facet s .prefixPreview true = facet s .preview := by rfl
theorem proposed_mode_guard_still_requires_preview : jsonModeAllowed false = false := by rfl

end ApplicationStudy.MigrationFlow
