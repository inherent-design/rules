namespace ApplicationStudy.AuthorAdmission

inductive Phase where | existingAdopt | initialAdopt | validateTarget
  deriving DecidableEq, Repr
structure Request where
  phase : Phase
  held : Bool
  version : Nat
  requestPinned : Bool
  missingRoot : Bool
  runtimeMatches : Bool
  deriving Repr

/-- Fixed, well-formed fictional A→B fixture; complete identical required evidence.
    These decisions do not identify bytes or check provider runtime eligibility. -/
def failure (r : Request) : Option String :=
  if !r.runtimeMatches then
    some (if r.phase == .existingAdopt then "runtime-mismatch" else "invalid-project")
  else if (r.phase == .initialAdopt && r.missingRoot) || (r.held && r.version != 1) then
    some "invalid-project"
  else none
def accepted (r : Request) : Bool := (failure r).isNone
def authorPin (r : Request) : Option String := if r.held then some "Version1" else none
def locked (r : Request) : List String :=
  if r.phase == .initialAdopt then ["a", "b"] else ["a", "b", "c"]
def changed (r : Request) : Option (List String) :=
  if !accepted r || r.phase == .validateTarget then none
  else some (if r.phase == .initialAdopt then ["a", "b"] else if r.version == 1 then [] else ["a"])
def bindings (r : Request) : Option (List String) :=
  if !accepted r || r.phase == .validateTarget then none else some ["a", "b"]
def runtime (r : Request) : String := if r.phase == .validateTarget then "1.21.2" else "1.21.1"
private def base : Request := ⟨.existingAdopt, false, 2, false, false, true⟩

theorem automatic_adoption_admitted : accepted base = true := by decide
theorem incoming_pin_does_not_mint_author_pin : authorPin {base with requestPinned := true} = none := by rfl
theorem incoming_pin_does_not_change_admission (r : Request) (p : Bool) :
    failure {r with requestPinned := p} = failure r := by rfl
theorem held_changed_selection_refused : failure {base with held := true} = some "invalid-project" := by decide
theorem matching_pin_admitted : accepted {base with held := true, version := 1} = true := by decide
theorem matching_pin_remains_authored : authorPin {base with held := true, version := 1} = some "Version1" := by rfl
theorem existing_runtime_mismatch_has_own_failure :
    failure {base with runtimeMatches := false, held := true} = some "runtime-mismatch" := by decide
theorem initial_automatic_admitted : accepted {base with phase := .initialAdopt, requestPinned := true} = true := by decide
theorem initial_authored_pin_not_replaced : failure {base with phase := .initialAdopt, held := true} = some "invalid-project" := by decide
theorem unresolved_authored_root_refused : failure {base with phase := .initialAdopt, missingRoot := true} = some "invalid-project" := by decide
theorem old_runtime_cannot_bind_target : failure {base with phase := .validateTarget, runtimeMatches := false} = some "invalid-project" := by decide
theorem retagged_carrier_is_core_admissible : accepted {base with phase := .validateTarget, version := 1} = true := by decide
theorem retagged_held_carrier_is_core_admissible : accepted {base with phase := .validateTarget, held := true, version := 1} = true := by decide
theorem changed_pin_still_refused_on_target : failure {base with phase := .validateTarget, held := true} = some "invalid-project" := by decide
theorem initial_candidate_has_no_unlisted_old_record : locked {base with phase := .initialAdopt} = ["a", "b"] := by rfl
theorem existing_candidate_retains_unlisted_record : locked base = ["a", "b", "c"] := by rfl
theorem identical_existing_selection_changes_no_record : changed {base with version := 1} = some [] := by decide
theorem initial_plan_records_group : changed {base with phase := .initialAdopt} = some ["a", "b"] := by decide
theorem validation_has_no_adoption_plan : changed {base with phase := .validateTarget} = none ∧ bindings {base with phase := .validateTarget} = none := by decide

end ApplicationStudy.AuthorAdmission
