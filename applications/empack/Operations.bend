import Base

# Selected source owner/retirement barriers. No native process-tree, publisher,
# durable storage, lock codec, or complete scheduler model.
type E is Data:
  E{phase: Nat,workers: Nat,cancelled: Bool,terminal: Nat}
def outcome(+driver: Nat,fault: Bool) -> Nat:
  Bool.pick(Nat,Nat.is_eq(driver,1n),2n,Bool.pick(Nat,Bool.or(Nat.is_eq(driver,2n),fault),3n,1n))
def drop_starter(s: E) -> E:
  match s:
    case E{p,w,_,t}: E{p,w,True{},t}
def begin_retirement(s: E) -> E:
  match s:
    case E{_,w,c,t}: E{2n,w,c,t}
def retire_worker(s: E) -> E:
  match s:
    case E{p,w,c,t}: E{p,Nat.sub(w,1n),c,t}
def finish(+s: E,driver: Nat,fault: Bool) -> E:
  match s:
    case E{p,w,c,_}: Bool.pick(E,Bool.and(Nat.is_eq(p,2n),Nat.is_eq(w,0n)),E{3n,0n,c,outcome(driver,fault)},s)
def step(action: Nat,s: E,driver: Nat,fault: Bool) -> E:
  match action:
    case 0n: s
    case 1n: drop_starter(s)
    case 2n: begin_retirement(s)
    case 3n: retire_worker(s)
    case 4n: finish(s,driver,fault)
    case _: s
def run(actions: List<&2,Nat>,s: E,+driver: Nat,+fault: Bool) -> E:
  match actions:
    case Nil{}: s
    case Con{a,rest}: run(rest,step(a,s,driver,fault),driver,fault)
def entry_text(s: E) -> String:
  match s:
    case E{p,w,c,t}: Nat.show(p) ++ "|" ++ Nat.show(w) ++ "|" ++ Bool.pick(String,c,"1","0") ++ "|" ++ Nat.show(t)
def admission(open: Bool,used: Nat,maximum: Nat) -> Nat:
  Bool.pick(Nat,open,Bool.pick(Nat,Nat.is_lt(used,maximum),0n,2n),1n)
def ordinary(accepting: Bool,cancelled: Bool,operation: Bool,owner: Bool,attempt: Bool) -> Bool:
  Bool.and(accepting,Bool.and(Bool.not(cancelled),Bool.and(operation,Bool.and(owner,attempt))))
def receipt(operation: Bool,owner: Bool) -> Bool:
  Bool.and(operation,owner)
def progress_text(terminal: Bool,value: Nat) -> String:
  Bool.pick(String,terminal,"1","0") ++ "|" ++ Nat.show(value)
def present_progress(terminal: Bool,value: Nat) -> Maybe<&2,Nat>:
  Bool.pick(Maybe<&2,Nat>,terminal,None{},Some{value})
def evidence_text(+driver: Nat,+fault: Bool) -> String:
  Nat.show(outcome(driver,fault)) ++ "|" ++ Nat.show(driver) ++ "|" ++ Bool.pick(String,fault,"1","0")

law observer_drop_does_not_cancel:
  for s: E
  {step(0n,s,0n,False{}) == s : E}
def observer_drop_does_not_cancel(s): {==}
law starter_drop_does_not_complete:
  {entry_text(drop_starter(E{1n,1n,False{},0n})) == "1|1|1|0" : String}
def starter_drop_does_not_complete(): {==}
law retirement_keeps_workers:
  {entry_text(begin_retirement(E{1n,1n,True{},0n})) == "2|1|1|0" : String}
def retirement_keeps_workers(): {==}
law pending_worker_prevents_completion:
  {entry_text(finish(E{2n,1n,True{},0n},1n,False{})) == "2|1|1|0" : String}
def pending_worker_prevents_completion(): {==}
law retired_worker_allows_terminal:
  {entry_text(finish(E{2n,0n,True{},0n},1n,False{})) == "3|0|1|2" : String}
def retired_worker_allows_terminal(): {==}
law retirement_fault_overrides_driver_success:
  {outcome(0n,True{}) == 3n : Nat}
def retirement_fault_overrides_driver_success(): {==}
law driver_cancellation_hides_secondary_fault:
  {outcome(1n,True{}) == 2n : Nat}
def driver_cancellation_hides_secondary_fault(): {==}
law closed_admission_wins:
  for used: Nat
  for maximum: Nat
  {admission(False{},used,maximum) == 1n : Nat}
def closed_admission_wins(used,maximum): {==}
law receipt_survives_cancel_and_supersession:
  {receipt(True{},True{}) == True{} : Bool}
def receipt_survives_cancel_and_supersession(): {==}
law ordinary_refuses_cancel:
  {ordinary(True{},True{},True{},True{},True{}) == False{} : Bool}
def ordinary_refuses_cancel(): {==}
law foreign_owner_receipt_refused:
  {receipt(True{},False{}) == False{} : Bool}
def foreign_owner_receipt_refused(): {==}
law terminal_progress_is_not_presented:
  for n: Nat
  {present_progress(True{},n) == None{} : Maybe<&2,Nat>}
def terminal_progress_is_not_presented(n): {==}
