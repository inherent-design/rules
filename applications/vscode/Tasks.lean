namespace ApplicationStudy.VscodeTasks

/-- A projection of the taskExecutions API, not an OS process table. Task IDs
    are fixture-local identities retained across callbacks. -/
structure Event where
  kind : Nat
  task : Nat
  deriving Repr, BEq

/-- 1: returned handle, 2: task start, 3: process start, 4: stop request,
    5: process end, 6: task end, 0: other observation. A background dependency
    can start without a caller executeTask-returned event. -/
def step (active : List Nat) (event : Event) : List Nat :=
  if event.kind == 1 || event.kind == 2 then
    if active.contains event.task then active else active ++ [event.task]
  else if event.kind == 6 then active.filter (· != event.task)
  else active

def trace (active : List Nat) : List Event → List (List Nat)
  | [] => []
  | event :: rest =>
    let next := step active event
    next :: trace next rest

/-- Source-selected admission only: kind 0 absent, 1 ProcessExecution,
    2 ShellExecution, 3 CustomExecution. A Node extension host may resolve a
    preserved task handle without an attached execution. Worker hosts cannot.
    Other validity/DTO/workspace/capability checks are separate premises. -/
def admits (workerHost : Bool) (kind : Nat) (preservedHandle : Bool) : Bool :=
  if workerHost then kind == 3 else kind != 0 || preservedHandle

/-- The fixture has one admitted task definition and supported, trusted task
    system. This projects the autoDetect/provider gate, not all discovery. -/
def discover (enabled registered : Bool) (count : Nat) : Nat :=
  if enabled && registered then count else 0

/-- Source watching-background dependency gate. Inactivity can satisfy a
    dependency before producer exit; this does not assert process retirement. -/
def dependencyReady (background watching inactive exitedSuccessfully : Bool) : Bool :=
  (background && watching && inactive) || exitedSuccessfully

/-- Proposed consumer safety guard, not an assertion about VS Code's own
    termination implementation. A positive PID also needs an independent
    ownership binding; virtual PID -1 can never authorize an OS signal. -/
def maySignal (pid : Int) (ownedBinding : Bool) : Bool := pid > 0 && ownedBinding

def idsText (ids : List Nat) : String := String.intercalate "," (ids.map toString)
def traceText (events : List Event) : String :=
  String.intercalate ";" ((trace [] events).map fun ids => "[" ++ idsText ids ++ "]")

theorem returned_handle_is_visible : step [] ⟨1, 1⟩ = [1] := by decide
theorem repeated_start_keeps_identity : step [1] ⟨2, 1⟩ = [1] := by decide
theorem dependency_start_adds_identity : step [1] ⟨2, 2⟩ = [1, 2] := by decide
theorem stop_request_does_not_remove (active : List Nat) (id : Nat) :
    step active ⟨4, id⟩ = active := rfl
theorem process_end_is_not_task_end (active : List Nat) (id : Nat) :
    step active ⟨5, id⟩ = active := rfl
theorem task_end_removes_only_target : step [1, 2, 3] ⟨6, 2⟩ = [1, 3] := by decide
theorem disabled_discovery_is_empty (registered : Bool) (n : Nat) :
    discover false registered n = 0 := rfl
theorem disposed_provider_is_not_discoverable (enabled : Bool) (n : Nat) :
    discover enabled false n = 0 := by simp [discover]
theorem node_preserved_handle_can_resolve : admits false 0 true = true := rfl
theorem worker_requires_custom_even_with_handle : admits true 0 true = false := rfl
theorem worker_rejects_process : admits true 1 false = false := rfl
theorem background_inactivity_is_not_exit : dependencyReady true true true false = true := rfl
theorem ordinary_inactivity_does_not_satisfy : dependencyReady false true true false = false := rfl
theorem virtual_pid_never_authorizes_signal (bound : Bool) : maySignal (-1) bound = false := rfl
theorem unbound_pid_never_authorizes_signal (pid : Int) : maySignal pid false = false := by simp [maySignal]

end ApplicationStudy.VscodeTasks
