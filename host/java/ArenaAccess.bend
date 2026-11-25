import Base

type Operation is Data:
  ReadArena{}
  WriteArena{}
  CloseArena{}
type State is Data:
  State{alive: Bool, historical_value: Nat}
type Context is Data:
  Context{shared: Bool, actor_is_owner_thread: Bool}

def reasons_fields(alive: Bool, shared: Bool, owner: Bool) -> Nat:
  Nat.add(Bool.pick(Nat,alive,0n,1n),Bool.pick(Nat,Bool.or(shared,owner),0n,2n))
def reasons(s: State,c: Context) -> Nat:
  match s c:
    case State{alive,_} Context{shared,owner}: reasons_fields(alive,shared,owner)
def allowed(s: State,c: Context) -> Bool:
  Nat.is_eq(reasons(s,c),0n)
def admitted(s: State,op: Operation) -> State:
  match s op:
    case State{alive,v} ReadArena{}: State{alive,v}
    case State{alive,v} WriteArena{}: State{alive,99n}
    case State{alive,v} CloseArena{}: State{False{},v}
def after(+s: State,c: Context,op: Operation) -> State:
  Bool.pick(State,allowed(s,c),admitted(s,op),s)
def read_value(s: State,op: Operation) -> Maybe<&2,Nat>:
  match s op:
    case State{_,v} ReadArena{}: Some{v}
    case State{_,v} WriteArena{}: Some{99n}
    case State{_,v} CloseArena{}: None{}
def returned_value(+s: State,c: Context,op: Operation) -> Maybe<&2,Nat>:
  Bool.pick(Maybe<&2,Nat>,allowed(s,c),read_value(s,op),None{})

law owner_reads_open_confined:
  {allowed(State{True{},42n},Context{False{},True{}}) == True{} : Bool}
def owner_reads_open_confined():
  {==}
law wrong_thread_close_preserves_scope:
  {after(State{True{},42n},Context{False{},False{}},CloseArena{}) == State{True{},42n} : State}
def wrong_thread_close_preserves_scope():
  {==}
law closed_owner_temporal_reason:
  {reasons(State{False{},42n},Context{False{},True{}}) == 1n : Nat}
def closed_owner_temporal_reason():
  {==}
law both_failures_retained:
  {reasons(State{False{},42n},Context{False{},False{}}) == 3n : Nat}
def both_failures_retained():
  {==}
law shared_other_thread_write:
  {after(State{True{},42n},Context{True{},False{}},WriteArena{}) == State{True{},99n} : State}
def shared_other_thread_write():
  {==}
law shared_other_thread_close:
  {after(State{True{},42n},Context{True{},False{}},CloseArena{}) == State{False{},42n} : State}
def shared_other_thread_close():
  {==}
law closed_read_has_no_value:
  {returned_value(State{False{},42n},Context{True{},True{}},ReadArena{}) == None{} : Maybe<&2,Nat>}
def closed_read_has_no_value():
  {==}
