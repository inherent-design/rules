import terminal.Empack
namespace TerminalStudy.Candidate

inductive Mode | inspect | preview | apply deriving DecidableEq, Repr
inductive Decision | inspect | plan | apply | requireApproval | refresh | refuse deriving DecidableEq, Repr
structure Request where
  mode : Mode
  preparedRevision : Nat
  currentRevision : Nat
  approvedRevision : Option Nat
  evidenceComplete : Bool

/-- Proposed shared CLI boundary. Approval is about an exact target, not TTY presence. -/
def decide (r : Request) : Decision :=
  match r.mode with
  | .inspect => .inspect
  | .preview => .plan
  | .apply =>
    if r.preparedRevision ≠ r.currentRevision then .refresh
    else if !r.evidenceComplete then .refuse
    else if r.approvedRevision = some r.preparedRevision then .apply
    else .requireApproval

theorem inspect_never_applies (r : Request) :
    decide { r with mode := .inspect } = .inspect := rfl
theorem preview_never_applies (r : Request) :
    decide { r with mode := .preview } = .plan := rfl
theorem stale_approval_never_applies (r : Request)
    (h : r.preparedRevision ≠ r.currentRevision) :
    decide { r with mode := .apply } = .refresh := by simp [decide, h]
theorem incomplete_evidence_never_applies (r : Request)
    (h : r.evidenceComplete = false) :
    decide { r with mode := .apply } ≠ .apply := by
  by_cases hs : r.preparedRevision = r.currentRevision <;> simp [decide, hs, h]
theorem apply_requires_exact_approval (r : Request) (h : decide r = .apply) :
    r.approvedRevision = some r.preparedRevision := by
  cases hm : r.mode <;> simp [decide, hm] at h
  split at h <;> simp_all
  split at h <;> simp_all

/-- Unknown effects are never rewritten as no-change merely because work failed. -/
def finish (cancelRequested : Bool) (actual : Report) : Report := Empack.finalize cancelRequested actual
theorem failure_keeps_unknown_effects :
    (finish true statusOnlyFailure).effects.project = .unknown := rfl

example : decide ⟨.apply, 12, 13, some 12, true⟩ = .refresh := rfl
example : decide ⟨.apply, 12, 12, none, true⟩ = .requireApproval := rfl
example : decide ⟨.apply, 12, 12, some 12, false⟩ = .refuse := rfl
example : decide ⟨.apply, 12, 12, some 12, true⟩ = .apply := rfl

end TerminalStudy.Candidate
