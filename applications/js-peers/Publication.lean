namespace ApplicationStudy.JsPublication

inductive Profile | npm | pnpm | yarn deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive Loss | none | beforeAcceptance | afterAcceptance deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr
inductive HookFailure | none | beforeUpload | afterUpload deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

/-- Admitted single-package fixture. `recordPresent` is the fixture's current version
    record, not an inference from a failed HTTP request. The two loss points are
    independent server-side interventions, invisible to the publisher. -/
structure Request where
  dry : Bool := false
  recordPresent : Bool := false
  rejected : Bool := false
  loss : Loss := .none
  hooks : Bool := false
  hookFailure : HookFailure := .none
  deriving Repr

structure Facts where
  sent : Bool
  acceptedHere : Bool
  remotePresent : Bool
  acknowledged : Bool
  localHookEffects : Bool
  exitCode : Nat
  deriving BEq, DecidableEq, Repr

def precheck (p : Profile) (r : Request) : Bool :=
  !r.dry && p == .npm && r.recordPresent

def earlyHookFailure (r : Request) : Bool := r.hooks && r.hookFailure == .beforeUpload

/-- This projects the selected source/native ordering. It does not implement
    packing, HTTP, authentication, script execution, or registry persistence. -/
def publish (p : Profile) (r : Request) : Facts :=
  let early := earlyHookFailure r
  let sent := !early && !r.dry && !precheck p r
  let accepted := sent && !r.recordPresent && !r.rejected && r.loss != .beforeAcceptance
  let acknowledged := accepted && r.loss == .none
  let networkFailed := sent && !acknowledged
  let late := !early && !precheck p r && !networkFailed && r.hooks && r.hookFailure == .afterUpload
  let hookFailed := early || late
  let failed := precheck p r || networkFailed || hookFailed
  { sent := sent
    acceptedHere := accepted
    remotePresent := r.recordPresent || accepted
    acknowledged := acknowledged
    localHookEffects := r.hooks
    exitCode := if !failed then 0 else if hookFailed && p == .npm then 7 else 1 }

/-- Proposed reporting of the completed exchange, separate from present CLI
    output. Rejection describes this attempt; it does not prove version absence.
    A lost response carries no server-side acceptance witness to the client. -/
inductive Claim | notSent | alreadyPresent | requestRejected | unknown | published
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

def claim (p : Profile) (r : Request) : Claim :=
  if earlyHookFailure r || r.dry then .notSent
  else if precheck p r then .alreadyPresent
  else if r.loss != .none then .unknown
  else if r.recordPresent || r.rejected then .requestRejected
  else .published

theorem dry_does_not_upload (p : Profile) (r : Request) :
    (publish p { r with dry := true }).sent = false := by simp [publish]

theorem dry_preserves_remote_record (p : Profile) (r : Request) :
    (publish p { r with dry := true }).remotePresent = r.recordPresent := by simp [publish]

theorem dry_is_not_globally_effect_free (p : Profile) :
    (publish p { dry := true, hooks := true }).localHookEffects = true := rfl

theorem present_record_is_not_deleted (p : Profile) (r : Request) :
    (publish p { r with recordPresent := true }).remotePresent = true := by simp [publish]

theorem acknowledged_implies_remote (p : Profile) (r : Request)
    (h : (publish p r).acknowledged = true) : (publish p r).remotePresent = true := by
  simp only [publish, Bool.and_eq_true] at h
  simp [publish, h.1]

theorem before_hook_prevents_upload (p : Profile) (r : Request) :
    (publish p { r with hooks := true, hookFailure := .beforeUpload }).sent = false := by
  simp [publish, earlyHookFailure]

theorem npm_existing_precheck_does_not_put :
    (publish .npm { recordPresent := true }).sent = false := rfl

theorem pnpm_existing_still_puts :
    (publish .pnpm { recordPresent := true }).sent = true := rfl

theorem yarn_existing_still_puts :
    (publish .yarn { recordPresent := true }).sent = true := rfl

theorem rejected_request_does_not_establish_absence :
    (publish .yarn { recordPresent := true, rejected := true }).remotePresent = true ∧
    claim .yarn { recordPresent := true, rejected := true } = .requestRejected := ⟨rfl, rfl⟩

theorem loss_before_has_no_record (p : Profile) :
    (publish p { loss := .beforeAcceptance }).remotePresent = false := by cases p <;> rfl

theorem loss_after_has_record (p : Profile) :
    (publish p { loss := .afterAcceptance }).remotePresent = true := by cases p <;> rfl

theorem both_loss_points_have_same_client_claim (p : Profile) :
    claim p { loss := .beforeAcceptance } = .unknown ∧
    claim p { loss := .afterAcceptance } = .unknown := by cases p <;> exact ⟨rfl, rfl⟩

theorem both_loss_points_have_same_failure_status (p : Profile) :
    (publish p { loss := .beforeAcceptance }).exitCode = 1 ∧
    (publish p { loss := .afterAcceptance }).exitCode = 1 := by cases p <;> exact ⟨rfl, rfl⟩

theorem late_hook_failure_preserves_acceptance (p : Profile) :
    (publish p { hooks := true, hookFailure := .afterUpload }).acknowledged = true ∧
    claim p { hooks := true, hookFailure := .afterUpload } = .published := by cases p <;> exact ⟨rfl, rfl⟩

theorem failure_does_not_mean_unpublished :
    (publish .npm { hooks := true, hookFailure := .afterUpload }).exitCode = 7 ∧
    (publish .npm { hooks := true, hookFailure := .afterUpload }).remotePresent = true := ⟨rfl, rfl⟩

end ApplicationStudy.JsPublication
