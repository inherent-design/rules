namespace ApplicationStudy.Mo2RefreshCallbacks

/-- Unique tokens label the controlled registrations, not arbitrary function identity. -/
structure Child where
  token : Nat
  group : Nat
  force : Bool
  deriving BEq, DecidableEq, Repr
structure Callback where
  token : Nat
  group : Nat
  child : Option Child := none
  deriving BEq, DecidableEq, Repr
structure Request where
  callback : Callback
  force : Bool
  deriving Repr
structure State where
  active : Bool
  trace : List Nat := []
  pending : List Callback := []
  deriving BEq, DecidableEq, Repr
structure Timeline where
  before : State
  first : State
  second : State
  deriving Repr

/-- Stable ordering within the selected Boost group policy. -/
def insert (callback : Callback) : List Callback → List Callback
  | [] => [callback]
  | head :: tail => if callback.group < head.group then callback :: head :: tail
    else head :: insert callback tail

def registerLeaf (state : State) (child : Child) : State :=
  if state.active || child.force then
    {state with pending := insert ⟨child.token,child.group,none⟩ state.pending}
  else {state with trace := state.trace ++ [child.token]}

def fire (state : State) (callback : Callback) : State :=
  let state := {state with trace := state.trace ++ [callback.token]}
  match callback.child with
  | none => state
  | some child => registerLeaf state child

def register (state : State) (request : Request) : State :=
  if state.active || request.force then
    {state with pending := insert request.callback state.pending}
  else fire state request.callback

/-- Current emission snapshots its slots, then disconnects the whole live signal.
    The alternative detaches the old batch before invocation. Callbacks here do
    not throw, disconnect, cross threads, or schedule children of children.
    No real refresh work, profile publication, Qt, or VFS is modeled. -/
def finish (detached : Bool) (state : State) : State :=
  let batch := state.pending
  let state : State := ⟨false,state.trace,if detached then [] else state.pending⟩
  let state := batch.foldl fire state
  if detached then state else {state with pending := []}

def run (detached active : Bool) (requests : List Request) : Timeline :=
  let before := requests.foldl register ⟨active,[],[]⟩
  let first := finish detached before
  ⟨before,first,finish detached first⟩

def future : Request := ⟨⟨1,0,some ⟨2,2,true⟩⟩,true⟩
def immediateChild : Request := ⟨⟨1,0,some ⟨2,2,false⟩⟩,true⟩

theorem active_registration_does_not_fire (callback : Callback) (force : Bool) :
    (register ⟨true,[],[]⟩ ⟨callback,force⟩).trace = [] := rfl
theorem forced_idle_registration_waits (callback : Callback) :
    (register ⟨false,[],[]⟩ ⟨callback,true⟩).pending = [callback] := rfl
theorem idle_leaf_runs_immediately (token group : Nat) :
    (register ⟨false,[],[]⟩ ⟨⟨token,group,none⟩,false⟩).trace = [token] := rfl
theorem current_loses_future_registration :
    (run false true [future]).first.pending = [] := rfl
theorem current_never_runs_lost_child :
    (run false true [future]).second.trace = [1] := rfl
theorem detached_retains_future_registration :
    (run true true [future]).first.pending = [⟨2,2,none⟩] := rfl
theorem detached_runs_child_next :
    (run true true [future]).second.trace = [1,2] := rfl
theorem detached_discharges_finished_child :
    (run true true [future]).second.pending = [] := rfl
theorem immediate_child_policy_preserved :
    (run false true [immediateChild]).first =
    (run true true [immediateChild]).first := rfl
theorem completed_one_shot_does_not_repeat :
    (run false true [⟨⟨1,0,none⟩,true⟩]).second.trace = [1] := rfl
theorem group_order_preserved :
    (run false true [⟨⟨3,2,none⟩,true⟩,⟨⟨1,0,none⟩,true⟩,
      ⟨⟨2,1,none⟩,true⟩]).first.trace = [1,2,3] := rfl

end ApplicationStudy.Mo2RefreshCallbacks
