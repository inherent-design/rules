namespace ApplicationStudy.SelectionPolicy

inductive Preference where
  | stableOnly | preferStable | any
  deriving DecidableEq, Repr

def effective (project : Preference) (root operation : Option Preference) (rootApplies : Bool) : Preference :=
  operation.getD (if rootApplies then root.getD project else project)

/-- Provider-root profile only. Other source kinds have additional admission rules. -/
def validPinPreference (pinned preferencePresent : Bool) : Bool := !(pinned && preferencePresent)

inductive Key where | a | b | c | d
  deriving DecidableEq, Repr
structure ExactRequest where
  key : Key
  version : Nat
  deriving Repr
structure Update where
  key : Key
  held : Bool
  version : Nat
  request : Option ExactRequest
  runtimeMismatch : Bool
  foreignIdentity : Bool
  evidenceMatches : Bool
  deriving Repr

/-- Bounded current-core fixture: installed A/B/C at version1, only A authored;
    A requires B with complete evidence, C unreferenced. One proposed root,
    plus unchanged B in the matching-evidence control. Not a general resolver. -/
def failure (r : Update) : Option String :=
  if r.runtimeMismatch then some "runtime-mismatch"
  else if r.foreignIdentity then some "occupied-key"
  else if r.key == .a && r.version == 1 && !r.evidenceMatches then some "retained-evidence"
  else if r.key == .d then some "not-installed"
  else if r.request.any (fun pin => pin.key != r.key || pin.key != .a || pin.version != r.version) then some "invalid-pin"
  else if r.held && r.key == .a && r.version != 1 && r.request.isNone then some "invalid-project"
  else none

def accepted (r : Update) : Bool := (failure r).isNone

def versionName (n : Nat) : String := "Version" ++ toString n

def authorPin (r : Update) : String :=
  match r.request with
  | some pin => if pin.key == .a then versionName pin.version else if r.held then "Version1" else "automatic"
  | none => if r.held then "Version1" else "automatic"

/-- set_provider_pin removes a root's automatic preference. Unrelated author
    fields and root membership are preserved in this admitted fixture profile. -/
def authorPreference (r : Update) : String :=
  if r.request.any (fun pin => pin.key == .a) || r.held then "none" else "stable-only"

def keyName : Key → String | .a => "a" | .b => "b" | .c => "c" | .d => "d"
def changed (r : Update) : List String := if r.version == 1 then [] else [keyName r.key]
def authorRoots (_r : Update) : List String := ["a"]

/-- Source-only projection of UpdateAssessment::is_complete. These facts are
    provided by the observer, not proved by this predicate. Conflict declarations
    do not change required-closure scope into complete pack compatibility. -/
inductive Joint where | notApplicable | validated | blocked | unknown | notAssessed
  deriving DecidableEq, Repr

def assessmentComplete (rowsComplete : Bool) (joint : Joint) (declarationsComplete : Bool) (_conflicts : Nat) : Bool :=
  rowsComplete && (joint == .notApplicable || (joint == .validated && declarationsComplete))

private def base : Update := ⟨.a,false,2,none,false,false,false⟩

theorem operation_preference_wins (p r : Preference) (o : Preference) (applies : Bool) :
    effective p (some r) (some o) applies = o := by rfl
theorem root_preference_wins (p r : Preference) : effective p (some r) none true = r := by rfl
theorem unrelated_key_uses_project (p r : Preference) : effective p (some r) none false = p := by rfl
theorem project_default (p : Preference) : effective p none none true = p := by rfl
theorem pin_and_preference_refused : validPinPreference true true = false := by rfl
theorem automatic_preference_admitted : validPinPreference false true = true := by rfl
theorem pin_without_preference_admitted : validPinPreference true false = true := by rfl
theorem automatic_update_does_not_mint_pin : accepted base = true ∧ authorPin base = "automatic" := by decide
theorem automatic_update_keeps_root_preference : authorPreference base = "stable-only" := by rfl
theorem held_pin_needs_explicit_change : failure {base with held := true} = some "invalid-project" := by decide
theorem reviewed_pin_is_admitted : failure {base with held := true, request := some ⟨.a,2⟩} = none := by decide
theorem reviewed_pin_replaces_preference : authorPreference {base with request := some ⟨.a,2⟩} = "none" := by rfl
theorem mismatched_exact_request_refused : failure {base with request := some ⟨.a,3⟩} = some "invalid-pin" := by decide
theorem unrequested_pin_refused : failure {base with request := some ⟨.b,1⟩} = some "invalid-pin" := by decide
theorem retained_record_cannot_acquire_author_pin : failure {base with key := .c, request := some ⟨.c,2⟩} = some "invalid-pin" := by decide
theorem retained_update_does_not_promote : accepted {base with key := .c} = true ∧ authorPin {base with key := .c} = "automatic" ∧ authorRoots {base with key := .c} = ["a"] := by decide
theorem exact_equality_does_not_override_evidence : failure {base with held := true, version := 1, request := some ⟨.a,1⟩} = some "retained-evidence" := by decide
theorem matching_same_pin_is_admitted : failure {base with held := true, version := 1, request := some ⟨.a,1⟩, evidenceMatches := true} = none := by decide
theorem matching_same_pin_changes_no_record : changed {base with version := 1, evidenceMatches := true} = [] := by rfl
theorem new_record_is_not_update : failure {base with key := .d} = some "not-installed" := by decide
theorem runtime_change_is_not_update : failure {base with runtimeMismatch := true} = some "runtime-mismatch" := by rfl
theorem identity_change_is_not_update : failure {base with foreignIdentity := true} = some "occupied-key" := by decide
theorem complete_closure_can_report_conflicts (n : Nat) : assessmentComplete true .validated true n = true := by rfl
theorem unknown_rows_are_not_complete (j : Joint) (d : Bool) (n : Nat) : assessmentComplete false j d n = false := by rfl
theorem unknown_declaration_scan_is_not_complete : assessmentComplete true .validated false 0 = false := by rfl
theorem no_provider_closure_is_not_applicable : assessmentComplete true .notApplicable false 0 = true := by rfl

end ApplicationStudy.SelectionPolicy
