namespace ApplicationStudy.EmpackRecovery

/-- One admitted regular-file change with distinct present before/after images.
    Native shape, capability, hashing, and complete inventory checks are premises. -/
structure View where
  supported : Bool
  rootMatches : Bool
  committed : Bool
  restoring : Bool
  position : Nat -- before=0, after=1, other/absent=2
  beforeObject : Bool
  candidateValid : Bool
  beforeValid : Bool
  deriving BEq, DecidableEq, Repr
structure Request where
  mode : Nat -- inspect=0, preview=1, execute=2
  restore : Bool
  accepted : Bool
  operationMatches : Bool
  sameJournal : Bool
  sameVisible : Bool
  prepared : View
  observed : View
  deriving BEq, DecidableEq, Repr
structure Outcome where
  success : Bool
  planned : Option Nat
  position : Nat
  committed : Bool
  restoring : Bool
  scratchCreated : Bool := false
  deriving BEq, DecidableEq, Repr
def supported (v : View) : Bool := v.supported && v.rootMatches
def inverseNeeded (v : View) (restore : Bool) : Bool := restore && !v.restoring
def targetAdmitted (v : View) : Bool := v.position == 1 || (v.position == 0 && v.beforeObject)
def candidateNeeded (v : View) (restore : Bool) : Bool :=
  !inverseNeeded v restore && v.position != 1
/-- Current preflight checks needed forward candidates. It does not read original
    before-image bytes while planning a new restoration. -/
def preflight (v : View) (restore : Bool) : Bool :=
  targetAdmitted v && (!candidateNeeded v restore || v.candidateValid)
def beforeCopyNeeded (v : View) (restore : Bool) : Bool := inverseNeeded v restore && v.position != 0
def changes (v : View) (restore : Bool) : Nat :=
  if v.position == (if inverseNeeded v restore then 0 else 1) then 0 else 1
def unchanged (r : Request) (ok : Bool) (planned : Option Nat := none) : Outcome :=
  ⟨ok,planned,r.observed.position,r.observed.committed,r.observed.restoring,false⟩
def evaluate (r : Request) : Outcome :=
  if !supported r.prepared then unchanged r false else
  if !r.operationMatches then unchanged r false else
  if r.mode == 0 then unchanged r true else
  if r.prepared.committed || !preflight r.prepared r.restore then unchanged r false else
  let planned := some (changes r.prepared r.restore)
  if r.mode == 1 || !r.accepted then unchanged r true planned else
  if !r.sameJournal || !r.sameVisible || !supported r.observed ||
      !preflight r.observed r.restore then unchanged r false planned else
  if beforeCopyNeeded r.observed r.restore && !r.observed.beforeValid then
    {unchanged r false planned with scratchCreated := true}
  else
    ⟨true,planned,(if inverseNeeded r.observed r.restore then 0 else 1),true,
      r.observed.restoring || r.restore,beforeCopyNeeded r.observed r.restore⟩
/-- PROPOSED: verify a before-image during preparation iff restoration will copy
    it. Execution must still revalidate; this grants no new recovery authority. -/
def proposedPrepare (v : View) (restore : Bool) : Bool :=
  supported v && !v.committed && preflight v restore &&
  (!beforeCopyNeeded v restore || v.beforeValid)
private def before : View := ⟨true,true,false,false,0,true,true,true⟩
private def after : View := {before with position := 1}
private def request (v : View) (restore : Bool := false) : Request :=
  ⟨2,restore,true,true,true,true,v,v⟩
theorem forward_needs_after_image : candidateNeeded before false = true := by decide
theorem new_restore_does_not_need_forward_candidate : candidateNeeded after true = false := by decide
theorem already_after_finish_does_not_read_missing_candidate :
    (evaluate (request {after with candidateValid := false})).success = true := by decide
theorem missing_candidate_before_refuses_preparation :
    (evaluate (request {before with candidateValid := false})).planned = none := by decide
theorem original_restore_chooses_before : (evaluate (request after true)).position = 0 := by decide
theorem finish_restoring_follows_persisted_after :
    (evaluate (request {before with restoring := true})).position = 1 := by decide
theorem restore_restoring_does_not_invert_again :
    (evaluate (request {before with restoring := true} true)).position = 1 := by decide
theorem corrupt_before_can_be_prepared :
    (evaluate {(request {after with beforeValid := false} true) with mode := 1}).planned = some 1 := by decide
theorem corrupt_before_refuses_execution_but_can_create_scratch :
    let o := evaluate (request {after with beforeValid := false} true)
    o.success = false ∧ o.position = 1 ∧ o.committed = false ∧ o.scratchCreated = true := by decide
theorem already_before_restore_does_not_need_corrupt_before_image :
    (evaluate (request {before with beforeValid := false} true)).success = true ∧
    (evaluate (request {before with beforeValid := false} true)).scratchCreated = false := by decide
theorem same_bytes_do_not_adopt_replacement :
    (evaluate (request {before with beforeObject := false})).planned = none := by decide
theorem another_operation_cannot_inherit_the_request :
    (evaluate {(request before) with operationMatches := false}).planned = none := by decide
theorem changed_journal_cannot_inherit_approval :
    (evaluate {(request before) with sameJournal := false}).success = false := by decide
theorem changed_visible_object_cannot_inherit_approval :
    (evaluate {(request before) with sameVisible := false}).success = false := by decide
theorem changed_retained_candidate_is_rechecked :
    (evaluate {(request before) with observed := {before with candidateValid := false}}).success = false := by decide
theorem declined_plan_preserves_journal :
    (evaluate {(request before) with accepted := false}).committed = false := by decide
theorem inspect_committed_record_is_successful_inspection :
    (evaluate {(request {after with committed := true}) with mode := 0}).success = true := by decide
theorem explicit_recovery_of_committed_record_refuses :
    (evaluate (request {after with committed := true})).success = false := by decide
theorem foreign_root_is_not_recovery_authority :
    (evaluate (request {before with rootMatches := false})).planned = none := by decide
theorem unsupported_schema_is_not_absence :
    (evaluate {(request {before with supported := false}) with mode := 0}).success = false := by decide
theorem proposed_validation_rejects_needed_corrupt_before :
    proposedPrepare {after with beforeValid := false} true = false := by decide
theorem proposed_validation_preserves_already_before_noop :
    proposedPrepare {before with beforeValid := false} true = true := by decide
theorem proposed_validation_preserves_unused_corrupt_candidate :
    proposedPrepare {after with candidateValid := false} true = true := by decide
theorem preview_preserves_observed_state (r : Request) (h : r.mode = 1) :
    (evaluate r).position = r.observed.position ∧
    (evaluate r).committed = r.observed.committed ∧
    (evaluate r).restoring = r.observed.restoring ∧
    (evaluate r).scratchCreated = false := by
  simp only [evaluate,h]
  split <;> simp_all [unchanged]
  split <;> simp_all
  split <;> exact ⟨rfl,rfl,rfl,rfl⟩
end ApplicationStudy.EmpackRecovery
