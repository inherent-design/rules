namespace Host.Minecraft.ResourceCache

/- Selected non-reentrant authored callbacks. Entries are this cache's owners,
   not all references or physical allocations. Identity labels belong to one case. -/
inductive Value where
  | absent
  | text (identity : Nat)
  deriving BEq, DecidableEq, Repr

inductive Projection where
  | returned (value : Value)
  | failed
  deriving BEq, DecidableEq, Repr

structure Entry where
  identity : Nat
  cells : List (Nat × Value) := []
  deriving BEq, DecidableEq, Repr

structure Callback where
  event : Nat
  failures : Nat := 0
  deriving BEq, DecidableEq, Repr

structure State where
  capacity : Nat
  entries : List Entry := []
  callbacks : List Callback := []
  events : List Nat := []
  deriving BEq, DecidableEq, Repr

structure Step where
  state : State
  error : Nat := 0
  value : Option Value := none
  deriving BEq, DecidableEq, Repr

def create (capacity : Int) : Option State :=
  if capacity < 1 then none else some ⟨capacity.toNat, [], [], []⟩

def cell (entries : List Entry) (identity kind : Nat) : Option Value := do
  let entry ← entries.find? (fun e => e.identity == identity)
  let found ← entry.cells.find? (fun kv => kv.1 == kind)
  return found.2

def admit (state : State) (identity : Nat) : State :=
  if state.entries.any (fun e => e.identity == identity) then state
  else
    let retained := if state.entries.length == state.capacity then state.entries.drop 1 else state.entries
    { state with entries := retained ++ [⟨identity, []⟩] }

def store (entries : List Entry) (identity kind : Nat) (value : Value) : List Entry :=
  entries.map fun entry =>
    if entry.identity == identity then
      { entry with cells := entry.cells.filter (fun kv => kv.1 != kind) ++ [(kind, value)] }
    else entry

def project (state : State) (identity kind event : Nat) (projection : Projection) : Step :=
  if identity == 0 then ⟨state, 0, some .absent⟩
  else match cell state.entries identity kind with
    | some value => ⟨state, 0, some value⟩
    | none =>
      let admitted := admit state identity
      let called := { admitted with events := admitted.events ++ [event] }
      match projection with
      | .failed => ⟨called, 1, none⟩
      | .returned value => ⟨{ called with entries := store called.entries identity kind value }, 0, some value⟩

def onClear (state : State) (callback : Callback) : Step :=
  ⟨{ state with callbacks := state.callbacks ++ [callback] }, 0, none⟩

structure CallbackRun where
  callbacks : List Callback
  events : List Nat
  failed : Bool
  deriving BEq, DecidableEq, Repr

def invoke : List Callback → CallbackRun
  | [] => ⟨[], [], false⟩
  | callback :: rest =>
    if callback.failures == 0 then
      let later := invoke rest
      ⟨callback :: later.callbacks, callback.event :: later.events, later.failed⟩
    else
      ⟨{ callback with failures := callback.failures - 1 } :: rest, [callback.event], true⟩

def clear (state : State) : Step :=
  let called := invoke state.callbacks
  ⟨{ state with entries := [], callbacks := called.callbacks, events := state.events ++ called.events },
    if called.failed then 2 else 0, none⟩

theorem zero_capacity_refuses : create 0 = none := rfl

theorem negative_capacity_refuses (capacity : Int) (h : capacity < 1) :
    create capacity = none := by simp [create, h]

theorem null_bypasses_projection (state : State) (kind event : Nat) (projection : Projection) :
    project state 0 kind event projection = ⟨state, 0, some .absent⟩ := by
  simp [project]

theorem hit_preserves_all_state (state : State) (identity kind event : Nat) (projection : Projection)
    (nonnull : identity ≠ 0) (hit : cell state.entries identity kind = some value) :
    project state identity kind event projection = ⟨state, 0, some value⟩ := by
  simp [project, nonnull, hit]

theorem negative_hit_is_not_missing (state : State) (identity kind event : Nat) (projection : Projection)
    (nonnull : identity ≠ 0) (hit : cell state.entries identity kind = some .absent) :
    project state identity kind event projection = ⟨state, 0, some .absent⟩ := by
  simp [project, nonnull, hit]

theorem hit_does_not_promote_fifo (state : State) (identity kind event : Nat) (projection : Projection)
    (nonnull : identity ≠ 0) (hit : cell state.entries identity kind = some value) :
    (project state identity kind event projection).state.entries = state.entries := by
  simp [hit_preserves_all_state state identity kind event projection nonnull hit]

theorem projection_failure_retains_admission (state : State) (identity kind event : Nat)
    (nonnull : identity ≠ 0) (miss : cell state.entries identity kind = none) :
    (project state identity kind event .failed).state.entries = (admit state identity).entries := by
  simp [project, nonnull, miss]

theorem projection_failure_retains_call_event (state : State) (identity kind event : Nat)
    (nonnull : identity ≠ 0) (miss : cell state.entries identity kind = none) :
    (project state identity kind event .failed).state.events = (admit state identity).events ++ [event] := by
  simp [project, nonnull, miss]

theorem projection_failure_has_no_value (state : State) (identity kind event : Nat)
    (nonnull : identity ≠ 0) (miss : cell state.entries identity kind = none) :
    (project state identity kind event .failed).value = none := by
  simp [project, nonnull, miss]

theorem registration_does_not_run_callback (state : State) (callback : Callback) :
    (onClear state callback).state.events = state.events := rfl

theorem registration_preserves_entries (state : State) (callback : Callback) :
    (onClear state callback).state.entries = state.entries := rfl

theorem clear_empties_only_cache_entries (state : State) :
    (clear state).state.entries = [] := rfl

theorem clear_preserves_capacity (state : State) :
    (clear state).state.capacity = state.capacity := rfl

theorem failing_callback_stops_suffix (callback : Callback) (rest : List Callback)
    (fails : callback.failures ≠ 0) :
    (invoke (callback :: rest)).events = [callback.event] := by
  simp [invoke, fails]

theorem failing_callback_keeps_uninvoked_suffix (callback : Callback) (rest : List Callback)
    (fails : callback.failures ≠ 0) :
    (invoke (callback :: rest)).callbacks = {callback with failures := callback.failures - 1} :: rest := by
  simp [invoke, fails]

theorem callback_registration_count_is_retained (callbacks : List Callback) :
    (invoke callbacks).callbacks.length = callbacks.length := by
  induction callbacks with
  | nil => rfl
  | cons head tail ih =>
    simp only [invoke]
    split <;> simp_all

theorem clear_keeps_registration_count (state : State) :
    (clear state).state.callbacks.length = state.callbacks.length := by
  exact callback_registration_count_is_retained state.callbacks

end Host.Minecraft.ResourceCache
