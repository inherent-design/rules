namespace ApplicationStudy.Mo2Plugins

/-- Canonical catalog IDs, not filenames, persistent IDs, or filesystem identity. -/
structure Plugin where
  id : Nat
  enabled : Bool
  loaded : Bool
  forced : Bool
  disabled : Bool
  priority : Int
  loadOrder : Int
  masters : List Nat := []
  missing : List Nat := []
  indexed : Bool := true
  deriving Repr, DecidableEq
structure Event where
  kind : Nat -- 0 write request, 1 state notification
  ids : List Nat := []
  active : Bool := false
  deriving Repr, DecidableEq
structure State where
  plugins : List Plugin
  byPriority : List Nat
  writeRequests : Nat := 0
  indexCalls : Nat := 0
  events : List Event := []
  errors : Nat := 0
  warnings : Nat := 0
  deriving Repr, DecidableEq

def normalized (requested loaded forced disabled : Bool) : Bool :=
  (requested && !disabled) || loaded || forced
def special (p : Plugin) : Bool := p.loaded || p.forced || p.disabled
def find (id : Nat) (s : State) : Option Plugin := s.plugins.find? fun p => p.id == id && p.indexed
def setEnabled (id : Nat) (enabled : Bool) (s : State) : State :=
  { s with plugins := s.plugins.map fun p => if p.id == id then { p with enabled } else p }
def notify (ids : List Nat) (active : Bool) (s : State) : State :=
  if ids.isEmpty then s else { s with events := s.events ++ [⟨1, ids, active⟩] }
def writeRequest (s : State) : State :=
  { s with writeRequests := s.writeRequests + 1, events := s.events ++ [⟨0, [], false⟩] }
def setState (helper : Bool) (id : Nat) (active : Bool) (s : State) : State :=
  match find id s with
  | none => if helper then { s with errors := s.errors + 1 } else { s with warnings := s.warnings + 1 }
  | some p =>
    let value := normalized active p.loaded p.forced p.disabled
    let changed := setEnabled id value s
    if !helper then changed
    else
      let requested := writeRequest changed
      if value == p.enabled then requested else notify [id] value requested
def setAll (active : Bool) (s : State) : State :=
  let dirty := s.plugins.filter fun p => !special p && p.enabled != active
  let changed := { s with plugins := s.plugins.map fun p => if special p then p else { p with enabled := active } }
  if dirty.isEmpty then changed else notify (dirty.map (·.id)) active (writeRequest changed)

def sync (s : State) : State :=
  (s.byPriority.foldl (fun (acc : State × Nat) id =>
    let p := acc.1.plugins.find? fun p => p.id == id
    match p with
    | none => acc -- Decoder refuses invalid input indices; not source missing-index behavior.
    | some p =>
      let order : Int := if p.enabled then Int.ofNat acc.2 else -1
      let next := { acc.1 with plugins := acc.1.plugins.map fun p => if p.id == id then { p with loadOrder := order } else p }
      (next, acc.2 + if p.enabled then 1 else 0)) (s, 0)).1
def checkMasters (s : State) : State :=
  let enabled := (s.plugins.filter (·.enabled)).map (·.id)
  { s with plugins := s.plugins.map fun p =>
    { p with missing := if p.enabled then p.masters.filter (fun id => !enabled.contains id) else [] } }

def setAt (list : List Nat) (position value : Nat) : List Nat :=
  list.zipIdx |>.map fun (old, index) => if index == position then value else old
def reindex (s : State) : State :=
  let size := s.plugins.length
  let plugins := s.plugins.map fun p => { p with indexed := decide (0 ≤ p.priority ∧ p.priority < Int.ofNat size) }
  let invalid := s.plugins.filter fun p => p.priority ≥ Int.ofNat size
  let byPriority := plugins.foldl (fun indices p => if p.indexed then setAt indices p.priority.toNat p.id else indices) (List.replicate size 0)
  { s with plugins, byPriority, errors := s.errors + invalid.length, indexCalls := s.indexCalls + 1 }
def setPriority (id : Nat) (rank : Int) (s : State) : State :=
  { s with plugins := s.plugins.map fun p => if p.id == id then { p with priority := rank } else p }
def order (names : List Nat) (s : State) : State :=
  let cleared := { s with plugins := s.plugins.map fun p => { p with priority := -1 } }
  let requested := names.foldl (fun (acc : State × Nat) id =>
    match find id acc.1 with
    | none => acc
    | some _ => (setPriority id (Int.ofNat acc.2) acc.1, acc.2 + 1)) (cleared, 0)
  let completed := s.plugins.foldl (fun (acc : State × Nat) old =>
    match acc.1.plugins.find? (fun p => p.id == old.id) with
    | none => acc
    | some p => if p.priority != -1 then acc
                else (setPriority p.id (Int.ofNat acc.2) acc.1, acc.2 + 1)) requested
  reindex completed.1

structure Action where
  kind : Nat -- API,helper,bulk,order,sync,masters
  target : Nat := 0
  active : Bool := false
  names : List Nat := []
  deriving Repr
def apply (action : Action) (s : State) : State :=
  match action.kind with
  | 0 => setState false action.target action.active s
  | 1 => setState true action.target action.active s
  | 2 => setAll action.active s
  | 3 => order action.names s
  | 4 => sync s
  | _ => checkMasters s -- Codec admits only tags 0..5.

theorem loaded_wins_over_disabled (wanted forced : Bool) : normalized wanted true forced true = true := by cases wanted <;> cases forced <;> rfl
theorem disabled_without_force_stays_off (wanted : Bool) : normalized wanted false false true = false := by cases wanted <;> rfl
theorem free_follows_request (wanted : Bool) : normalized wanted false false false = wanted := by cases wanted <;> rfl
theorem empty_notification_is_not_an_event (active : Bool) (s : State) : notify [] active s = s := rfl
theorem write_request_is_not_derived_generation (s : State) : (writeRequest s).indexCalls = s.indexCalls := rfl
theorem missing_api_preserves_catalog : (setState false 9 true {plugins := [], byPriority := []}).plugins = [] := rfl
theorem missing_api_is_warning : (setState false 9 true {plugins := [], byPriority := []}).warnings = 1 := rfl
theorem missing_helper_is_error : (setState true 9 true {plugins := [], byPriority := []}).errors = 1 := rfl

def free : Plugin := {id := 0,enabled := false,loaded := false,forced := false,disabled := false,priority := 0,loadOrder := -1}
def freeState : State := {plugins := [free], byPriority := [0]}
theorem api_flag_does_not_sync_order :
    (setState false 0 true freeState).plugins.map (·.loadOrder) = [-1] := by decide
theorem api_flag_has_no_write_request : (setState false 0 true freeState).writeRequests = 0 := by decide
theorem helper_requests_write_even_if_unchanged : (setState true 0 false freeState).writeRequests = 1 := by decide
theorem helper_change_emits_write_then_state :
    (setState true 0 true freeState).events = [⟨0,[],false⟩,⟨1,[0],true⟩] := by decide
theorem bulk_does_not_normalize_inconsistent_forced :
    (setAll false {plugins := [{ free with loaded := true }], byPriority := [0]}).plugins = [{ free with loaded := true }] := by decide
theorem enabled_master_presence_does_not_check_order :
    (checkMasters {plugins := [{ free with enabled := true, priority := 1 },
       { free with id := 1, enabled := true, priority := 0, masters := [0] }], byPriority := [1,0]}).plugins.map (·.missing) = [[],[]] := by decide

def orderedCatalog : State := {
  plugins := [{free with priority := 2}, {free with id := 1,priority := 0}, {free with id := 2,priority := 1}]
  byPriority := [1,2,0] }
theorem partial_order_appends_catalog_order :
    (order [2] orderedCatalog).plugins.map (·.priority) = [1,2,0] := by decide
theorem duplicate_order_can_lose_query_index :
    (order [0,0] orderedCatalog).plugins.map (·.indexed) = [true,true,false] ∧
    (order [0,0] orderedCatalog).byPriority = [0,0,1] := by decide
theorem reorder_is_not_load_order_sync :
    (order [2,1,0] orderedCatalog).plugins.map (·.loadOrder) = [-1,-1,-1] := by decide

end ApplicationStudy.Mo2Plugins
