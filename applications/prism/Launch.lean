namespace ApplicationStudy.PrismLaunch

/-- Controlled step behaviors from the headless Qt fixture, not all Prism
    LaunchStep implementations or native process behavior. -/
inductive Kind
  | success | failure | ready | progress | disabled | refuse | synchronous | queued
  deriving BEq, DecidableEq, Repr

inductive Phase | notStarted | running | waiting | failed | aborted | finished
  deriving BEq, DecidableEq, Repr
inductive Outcome | inactive | running | succeeded | failed | abortedByUser
  deriving BEq, DecidableEq, Repr

structure Work where
  phase : Phase := .notStarted
  outcome : Outcome := .inactive
  current : Option Nat := none
  kind : Option Kind := none
  rest : List Kind := []
  started : List Nat := []
  finalized : List Nat := []
  events : List String := []
  instanceRunning : Bool := true
  instanceCrashed : Bool := false
  reason : String := ""
  pendingAbort : Bool := false
  deriving Repr

def event (name : String) (id : Nat) : String := name ++ ":" ++ toString id

/-- Calls to finalize are observed, not proof that arbitrary resources retired.
    The controller does not update its own phase on this nonempty path. -/
def finish (successful : Bool) (reason : String) (work : Work) : Work :=
  { work with
    outcome := if successful then .succeeded else .failed
    instanceRunning := false
    instanceCrashed := !successful
    reason := reason
    finalized := work.started.reverse
    events := work.events ++ (work.started.reverse.map (event "finalize")) ++
      [(if successful then "task-succeeded" else "task-failed"), "task-finished"] }

def drive (steps : List Kind) (id : Nat) (work : Work) : Work :=
  match steps with
  | [] => finish true "" work
  | kind :: rest =>
    let next := { work with
      current := some id
      kind := some kind
      rest := rest
      started := work.started ++ [id]
      events := work.events ++ [event "start" id] }
    match kind with
    | .success => drive rest (id + 1) next
    | .failure => finish false "fixture failure" next
    | .ready => { next with phase := .waiting, events := next.events ++ ["ready-request"] }
    | .progress => { next with phase := .waiting, events := next.events ++ ["progress-request"] }
    | _ => next

def start (steps : List Kind) : Work :=
  let initial : Work := { outcome := .running, events := ["task-started"] }
  if steps.isEmpty then
    { initial with
      phase := .finished
      outcome := .succeeded
      instanceRunning := false
      events := initial.events ++ ["task-succeeded", "task-finished"] }
  else drive steps 0 { initial with phase := .running }

/-- Scope: the fixture proceeds once from its ready/progress step. It does not
    model an arbitrary external repeated call on a completed task. -/
def proceed (work : Work) : Work :=
  if work.phase == .waiting then
    match work.current with
    | none => work
    | some id => drive work.rest (id + 1) { work with events := work.events ++ [event "proceed" id] }
  else work

def requestQueued (work : Work) : Work :=
  { work with phase := .aborted, pendingAbort := true }

def requestSynchronous (work : Work) : Work :=
  { finish false "Aborted" work with phase := .aborted }

/-- Admission premise: a running controlled hold step. Other wrapper phases
    and production LaunchStep abort implementations remain outside this model. -/
def abort (work : Work) : Bool × Work :=
  match work.current, work.kind with
  | some id, some kind =>
    let called := { work with events := work.events ++ [event "abort-call" id] }
    match kind with
    | .refuse => (false, called)
    | .synchronous => (true, requestSynchronous called)
    | .queued => (true, requestQueued called)
    | _ => (false, work)
  | _, _ => (false, work)

def drain (work : Work) : Work :=
  if work.pendingAbort then
    let delivered := { work with
      pendingAbort := false
      events := work.events ++ [event "abort-delivery" (work.current.getD 0)] }
    finish false "Aborted" delivered
  else work

def canAbort (work : Work) : Bool :=
  match work.phase with
  | .notStarted => true
  | .failed | .aborted | .finished => false
  | _ => match work.kind with
    | some .refuse | some .synchronous | some .queued => true
    | _ => false

def phaseCode : Phase → Nat
  | .notStarted => 0 | .running => 1 | .waiting => 2
  | .failed => 3 | .aborted => 4 | .finished => 5
def outcomeCode : Outcome → Nat
  | .inactive => 0 | .running => 1 | .succeeded => 2 | .failed => 3 | .abortedByUser => 4

theorem finalization_reverses_started (successful : Bool) (reason : String) (work : Work) :
    (finish successful reason work).finalized = work.started.reverse := rfl

theorem finalization_visits_started_count (successful : Bool) (reason : String) (work : Work) :
    (finish successful reason work).finalized.length = work.started.length := by simp [finish]

theorem completion_does_not_update_controller_phase (successful : Bool) (reason : String) (work : Work) :
    (finish successful reason work).phase = work.phase := rfl

theorem completion_clears_instance_flag (successful : Bool) (reason : String) (work : Work) :
    (finish successful reason work).instanceRunning = false := rfl

theorem queued_acceptance_does_not_change_base_outcome (work : Work) :
    (requestQueued work).outcome = work.outcome := rfl

theorem queued_delivery_reports_failure (work : Work) :
    (drain (requestQueued work)).outcome = .failed := rfl

theorem synchronous_abort_reports_failure (work : Work) :
    (requestSynchronous work).outcome = .failed := rfl

theorem accepted_queued_abort_can_remain_active :
    (abort (start [.queued])).1 = true ∧
    (abort (start [.queued])).2.phase = .aborted ∧
    (abort (start [.queued])).2.outcome = .running := ⟨rfl, rfl, rfl⟩

theorem nonempty_success_can_keep_running_phase :
    (start [.success]).phase = .running ∧ (start [.success]).outcome = .succeeded := ⟨rfl, rfl⟩

theorem failure_does_not_start_future_step :
    (start [.success, .failure, .success]).started = [0, 1] := rfl

theorem empty_sequence_starts_no_step : (start []).started = [] := rfl

end ApplicationStudy.PrismLaunch
