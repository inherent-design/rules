namespace ApplicationStudy.EmpackOperations

/-- Selected running-operation view. Workers are owned monitor obligations,
    not OS descendants. Tags: phase 1 running,2 retiring,3 terminal;
    result 0 absent,1 completed,2 cancelled,3 panicked. -/
structure Entry where
  phase : Nat := 1
  workers : Nat := 0
  cancelled : Bool := false
  terminal : Nat := 0
  deriving Repr, DecidableEq

/-- Current supervisor precedence: a returned driver error wins even if
    retirement also reports an error. This projects only the observed error
    kinds; it is not an endorsement of discarding secondary diagnostics. -/
def outcome (driver : Nat) (retirementFault : Bool) : Nat :=
  if driver == 1 then 2 else if driver == 2 || retirementFault then 3 else 1

def dropObserver (s : Entry) : Entry := s
def dropStarter (s : Entry) : Entry := { s with cancelled := true }
def beginRetirement (s : Entry) : Entry := { s with phase := 2 }
def retireWorker (s : Entry) : Entry := { s with workers := s.workers - 1 }
/-- Corresponds to the supervisor's awaited close_and_retire barrier. The
    worker-count witness is supplied by the selected owner/source adapter. -/
def finish (s : Entry) (driver : Nat) (fault : Bool) : Entry :=
  if s.phase == 2 && s.workers == 0 then
    { s with phase := 3, terminal := outcome driver fault }
  else s

def step (s : Entry) (action driver : Nat) (fault : Bool) : Entry :=
  match action with
  | 0 => dropObserver s
  | 1 => dropStarter s
  | 2 => beginRetirement s
  | 3 => retireWorker s
  | 4 => finish s driver fault
  | _ => s

def run (s : Entry) (actions : List Nat) (driver : Nat) (fault : Bool) : Entry :=
  actions.foldl (fun s a => step s a driver fault) s

def admission (admissionOpen : Bool) (used maximum : Nat) : Nat :=
  if !admissionOpen then 1 else if used >= maximum then 2 else 0

def mayRelease (terminal : Bool) : Bool := terminal
/-- The result Arc can outlive registry membership. The receipt/reference
    witness is held independently; releasing an entry does not invalidate it. -/
def retainedAfterRelease (hasReference : Bool) : Bool := hasReference

structure Acceptance where
  accepting : Bool
  cancelled : Bool
  sameOperation : Bool
  sameOwner : Bool
  sameAttempt : Bool
  deriving Repr

def ordinary (a : Acceptance) : Bool :=
  a.accepting && !a.cancelled && a.sameOperation && a.sameOwner && a.sameAttempt
/-- Owner-only publication/retirement receipt collection. These admitted source
    calls do NOT establish durable publication or runtime retirement themselves. -/
def receipt (a : Acceptance) : Bool := a.sameOperation && a.sameOwner

structure Progress where
  terminal : Bool
  observation : Nat
  deriving Repr, DecidableEq
/-- Current source: a separate latest-observation cell, with no phase fence or
    status-watch notification. The terminal result is not changed. -/
def writeProgress (s : Progress) (value : Nat) : Progress := { s with observation := value }
/-- Proposed consumer policy; not an implemented runtime change. -/
def presentProgress (s : Progress) : Option Nat := if s.terminal then none else some s.observation

def childCancelled (parent child : Bool) : Bool := parent || child

/-- Proposed richer result carrier preserves two failure facts while retaining
    the existing headline policy. No selected public API or wire codec yet. -/
structure FinalEvidence where
  reported : Nat
  driver : Nat
  retirementFault : Bool
  deriving Repr

def proposedEvidence (driver : Nat) (fault : Bool) : FinalEvidence :=
  ⟨outcome driver fault, driver, fault⟩

def entryText (s : Entry) : String := String.intercalate "|"
  [toString s.phase, toString s.workers, if s.cancelled then "1" else "0", toString s.terminal]

theorem observer_drop_does_not_cancel (s : Entry) : dropObserver s = s := rfl
theorem starter_drop_requests_cancel (s : Entry) : (dropStarter s).cancelled = true := rfl
theorem stop_request_does_not_complete (s : Entry) : (dropStarter s).terminal = s.terminal := rfl
theorem retirement_keeps_workers (s : Entry) : (beginRetirement s).workers = s.workers := rfl
theorem pending_worker_prevents_completion (s : Entry) (d : Nat) (f : Bool)
    (h : s.workers ≠ 0) : finish s d f = s := by simp [finish, h]
theorem retired_worker_allows_terminal : (finish ⟨2,0,true,0⟩ 1 false).terminal = 2 := rfl
theorem cancellation_does_not_replace_driver_success : outcome 0 false = 1 := rfl
theorem retirement_fault_overrides_driver_success : outcome 0 true = 3 := rfl
theorem driver_cancellation_hides_secondary_fault : outcome 1 true = 2 := rfl
theorem closed_admission_wins (used maximum : Nat) : admission false used maximum = 1 := rfl
theorem active_result_cannot_be_released : mayRelease false = false := rfl
theorem receipt_survives_cancel_and_supersession : receipt ⟨false,true,true,true,false⟩ = true := rfl
theorem ordinary_result_refused_after_cancel : ordinary ⟨true,true,true,true,true⟩ = false := rfl
theorem foreign_owner_receipt_refused : receipt ⟨true,false,true,false,true⟩ = false := rfl
theorem late_progress_preserves_terminal (s : Progress) (n : Nat) :
    (writeProgress s n).terminal = s.terminal := rfl
theorem terminal_progress_is_not_presented (n : Nat) : presentProgress ⟨true,n⟩ = none := rfl
theorem child_cancellation_does_not_require_parent : childCancelled false true = true := rfl
theorem proposed_evidence_keeps_fault (d : Nat) : (proposedEvidence d true).retirementFault = true := rfl

end ApplicationStudy.EmpackOperations
