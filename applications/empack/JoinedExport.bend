import Base
type State is Data:
  State{phase: Nat, basis: Nat}
type JResult is Data:
  JResult{state: State, current: Nat, ok: Bool, readable: Bool, copied: Bool, removed: Bool}
def writing(finished: Bool,basis: Nat) -> State:
  State{Bool.pick(Nat,finished,2n,1n),basis}
def phase(s: State) -> Nat:
  match s:
    case State{p,_}: p
def basis(s: State) -> Nat:
  match s:
    case State{_,b}: b
def reject(s: State,current: Nat) -> JResult:
  JResult{s,current,False{},False{},False{},False{}}
def act(action: Nat,+s: State,+current: Nat,capture: Nat,admitted: Bool,finished: Bool) -> JResult:
  match action:
    case 0n: Bool.pick(JResult,admitted,JResult{writing(finished,capture),current,True{},False{},False{},False{}},reject(s,current))
    case 1n:
      active=Bool.or(Nat.is_eq(phase(s),1n),Nat.is_eq(phase(s),2n))
      next=Bool.pick(JResult,admitted,JResult{writing(finished,basis(s)),current,True{},False{},False{},False{}},reject(State{0n,0n},current))
      Bool.pick(JResult,active,next,reject(s,current))
    case 2n:
      active=Bool.or(Nat.is_eq(phase(s),1n),Nat.is_eq(phase(s),2n))
      next=Bool.pick(JResult,Bool.and(Nat.is_eq(phase(s),2n),admitted),JResult{State{3n,basis(s)},current,True{},False{},False{},False{}},reject(State{0n,0n},current))
      Bool.pick(JResult,active,next,reject(s,current))
    case 3n:
      +readable=Bool.and(Nat.is_eq(phase(s),3n),admitted)
      JResult{s,current,readable,readable,False{},False{}}
    case 4n: JResult{State{0n,0n},current,True{},False{},Nat.is_eq(phase(s),3n),Bool.not(Nat.is_eq(phase(s),0n))}
    case _: reject(s,current)
def step(s: State,current: Nat,action: Nat,capture: Nat,admitted: Bool,finished: Bool) -> JResult:
  act(action,s,current,capture,admitted,finished)
def render(r: JResult) -> String:
  match r:
    case JResult{State{phase,basis},current,ok,readable,copied,removed}:
      Nat.show(phase) ++ "/" ++ Nat.show(basis) ++ "/" ++ Nat.show(current) ++ "/" ++ Bool.show(ok) ++ "/" ++ Bool.show(readable) ++ "/" ++ Bool.show(copied) ++ "/" ++ Bool.show(removed)
law input_completion_is_not_verified:
  {render(step(State{1n,7n},9n,1n,0n,True{},True{})) == "2/7/9/True/False/False/False" : String}
def input_completion_is_not_verified():
  {==}
law failed_verification_retires:
  {render(step(State{2n,7n},9n,2n,0n,False{},False{})) == "0/0/9/False/False/False/False" : String}
def failed_verification_retires():
  {==}
law unverified_output_unreadable:
  {render(step(State{2n,7n},9n,3n,0n,True{},False{})) == "2/7/9/False/False/False/False" : String}
def unverified_output_unreadable():
  {==}
law captured_output_keeps_newer_editor:
  {render(step(State{2n,7n},9n,2n,0n,True{},False{})) == "3/7/9/True/False/False/False" : String}
def captured_output_keeps_newer_editor():
  {==}
law cancel_ready_preserves_copy_uncertainty:
  {render(step(State{3n,7n},9n,4n,0n,True{},False{})) == "0/0/9/True/False/True/True" : String}
def cancel_ready_preserves_copy_uncertainty():
  {==}
