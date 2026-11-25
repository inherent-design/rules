import Base

# API execution identities, not native PIDs. Source-selected policies are
# separate from trace observations and proposed OS signal custody guard.
type E is Data:
  E{kind: Nat,task: Nat}
def contains(xs: List<&2,Nat>,+id: Nat) -> Bool:
  match xs:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,id),contains(tail,id))
def append(xs: List<&2,Nat>,id: Nat) -> List<&2,Nat>:
  match xs:
    case Nil{}: [id]
    case Con{head,tail}: Con{head,append(tail,id)}
def remove(xs: List<&2,Nat>,+id: Nat) -> List<&2,Nat>:
  match xs:
    case Nil{}: Nil{}
    case Con{+head,+tail}: Bool.pick(List<&2,Nat>,Nat.is_eq(head,id),remove(tail,id),Con{head,remove(tail,id)})
def step(+active: List<&2,Nat>,event: E) -> List<&2,Nat>:
  match event:
    case E{+kind,+id}:
      add=Bool.or(Nat.is_eq(kind,1n),Nat.is_eq(kind,2n))
      Bool.pick(List<&2,Nat>,add,Bool.pick(List<&2,Nat>,contains(active,id),active,append(active,id)),Bool.pick(List<&2,Nat>,Nat.is_eq(kind,6n),remove(active,id),active))
def tail_text(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: "," ++ Nat.show(head) ++ tail_text(tail)
def ids_text(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: Nat.show(head) ++ tail_text(tail)
def trace_tail(events: List<&2,E>,active: List<&2,Nat>) -> String:
  match events:
    case Nil{}: ""
    case Con{event,rest}:
      +next=step(active,event)
      ";[" ++ ids_text(next) ++ "]" ++ trace_tail(rest,next)
def trace_text(events: List<&2,E>) -> String:
  match events:
    case Nil{}: ""
    case Con{event,rest}:
      +next=step([],event)
      "[" ++ ids_text(next) ++ "]" ++ trace_tail(rest,next)
def admits(worker: Bool,+kind: Nat,handle: Bool) -> Bool:
  Bool.pick(Bool,worker,Nat.is_eq(kind,3n),Bool.or(Bool.not(Nat.is_eq(kind,0n)),handle))
def discover(enabled: Bool,registered: Bool,count: Nat) -> Nat:
  Bool.pick(Nat,Bool.and(enabled,registered),count,0n)
def dependency_ready(background: Bool,watching: Bool,inactive: Bool,exited: Bool) -> Bool:
  Bool.or(Bool.and(background,Bool.and(watching,inactive)),exited)
# sign is independently decoded: False includes virtual -1 and zero.
def may_signal(positive: Bool,bound: Bool) -> Bool:
  Bool.and(positive,bound)

law returned_handle_is_visible:
  {ids_text(step([],E{1n,1n})) == "1" : String}
def returned_handle_is_visible(): {==}
law repeated_start_keeps_identity:
  {ids_text(step([1n],E{2n,1n})) == "1" : String}
def repeated_start_keeps_identity(): {==}
law stop_request_does_not_remove:
  for active: List<&2,Nat>
  for id: Nat
  {step(active,E{4n,id}) == active : List<&2,Nat>}
def stop_request_does_not_remove(active,id): {==}
law process_end_is_not_task_end:
  for active: List<&2,Nat>
  for id: Nat
  {step(active,E{5n,id}) == active : List<&2,Nat>}
def process_end_is_not_task_end(active,id): {==}
law task_end_removes_only_target:
  {ids_text(step([1n,2n,3n],E{6n,2n})) == "1,3" : String}
def task_end_removes_only_target(): {==}
law disabled_discovery_is_empty:
  for registered: Bool
  for count: Nat
  {discover(False{},registered,count) == 0n : Nat}
def disabled_discovery_is_empty(registered,count): {==}
law node_preserved_handle_can_resolve:
  {admits(False{},0n,True{}) == True{} : Bool}
def node_preserved_handle_can_resolve(): {==}
law worker_requires_custom_even_with_handle:
  {admits(True{},0n,True{}) == False{} : Bool}
def worker_requires_custom_even_with_handle(): {==}
law background_inactivity_is_not_exit:
  {dependency_ready(True{},True{},True{},False{}) == True{} : Bool}
def background_inactivity_is_not_exit(): {==}
law ordinary_inactivity_does_not_satisfy:
  {dependency_ready(False{},True{},True{},False{}) == False{} : Bool}
def ordinary_inactivity_does_not_satisfy(): {==}
law virtual_pid_never_authorizes_signal:
  for bound: Bool
  {may_signal(False{},bound) == False{} : Bool}
def virtual_pid_never_authorizes_signal(bound): {==}
