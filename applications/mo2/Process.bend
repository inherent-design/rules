import Base

def refresh(trigger: Bool,+result: Nat) -> Bool:
  Bool.and(trigger,Bool.or(Nat.is_eq(result,2n),Nat.is_eq(result,5n)))
def early(hooked: Bool,+force: Bool,reason: Nat,locking: Bool) -> Bool:
  Bool.or(Bool.and(Bool.not(hooked),Bool.not(force)),
    Bool.and(Bool.not(force),Bool.or(Nat.is_eq(reason,0n),Bool.not(locking))))
def reason_after(force: Bool,+reason: Nat) -> Nat:
  Bool.pick(Nat,Bool.and(force,Nat.is_eq(reason,0n)),1n,reason)
def returned(hooked: Bool,+force: Bool,reason: Nat,locking: Bool,result: Nat) -> Nat:
  Bool.pick(Nat,Bool.or(Bool.and(Bool.not(hooked),Bool.not(force)),
    Bool.and(Bool.not(force),Nat.is_eq(reason,0n))),1n,
    Bool.pick(Nat,Bool.and(Bool.not(force),Bool.not(locking)),5n,result))
def background(force: Bool,reason: Nat,locking: Bool) -> Bool:
  Bool.and(force,Bool.and(Nat.is_eq(reason,3n),Bool.not(locking)))
def after(hooked: Bool,force: Bool,reason: Nat,locking: Bool,trigger: Bool,result: Nat) -> Bool:
  Bool.and(Bool.not(early(hooked,force,reason,locking)),refresh(trigger,result))

law no_trigger:
  for result: Nat
  {refresh(False{},result) == False{} : Bool}
def no_trigger(result): {==}
law completed:
  for +trigger: Bool
  {refresh(trigger,2n) == trigger : Bool}
def completed(trigger):
  match trigger:
    case False{}: {==}
    case True{}: {==}
law unlocked:
  for +trigger: Bool
  {refresh(trigger,5n) == trigger : Bool}
def unlocked(trigger):
  match trigger:
    case False{}: {==}
    case True{}: {==}
law cancelled:
  for +trigger: Bool
  {refresh(trigger,4n) == False{} : Bool}
def cancelled(trigger):
  match trigger:
    case False{}: {==}
    case True{}: {==}
law forced_wait_not_early:
  for hooked: Bool
  for reason: Nat
  for locking: Bool
  {early(hooked,True{},reason,locking) == False{} : Bool}
def forced_wait_not_early(hooked,reason,locking):
  match hooked:
    case False{}: {==}
    case True{}: {==}
law force_default:
  {reason_after(True{},0n) == 1n : Nat}
def force_default(): {==}
law no_background_with_lock:
  for force: Bool
  {background(force,3n,True{}) == False{} : Bool}
def no_background_with_lock(force):
  match force:
    case False{}: {==}
    case True{}: {==}
