import Base

type KState is Data:
  KState{a: Bool,b: Bool,c: Bool,backing: Nat}
type KOutcome is Data:
  KOutcome{state: KState,exit: Nat,current: Nat}
def present(s: KState,+id: Nat) -> Bool:
  match s:
    case KState{a,b,c,_}: Bool.pick(Bool,Nat.is_eq(id,1n),a,Bool.pick(Bool,Nat.is_eq(id,2n),b,Bool.pick(Bool,Nat.is_eq(id,3n),c,False{})))
def accepts(+s: KState,+id: Nat,+password: Nat) -> Bool:
  Bool.and(present(s,id),Bool.pick(Bool,Nat.is_eq(id,3n),Nat.is_eq(password,2n),Nat.is_eq(password,1n)))
def access(+s: KState,+password: Nat,+hint: Nat) -> Nat:
  Bool.pick(Nat,accepts(s,hint,password),hint,Bool.pick(Nat,accepts(s,1n,password),1n,Bool.pick(Nat,accepts(s,2n,password),2n,Bool.pick(Nat,accepts(s,3n,password),3n,0n))))
def without(s: KState,+id: Nat) -> KState:
  match s:
    case KState{a,b,c,backing}: KState{Bool.and(a,Bool.not(Nat.is_eq(id,1n))),Bool.and(b,Bool.not(Nat.is_eq(id,2n))),Bool.and(c,Bool.not(Nat.is_eq(id,3n))),backing}
def added(s: KState) -> KState:
  match s:
    case KState{a,_,c,backing}: KState{a,True{},c,backing}
def changed(s: KState) -> KState:
  match s:
    case KState{a,b,_,backing}: KState{a,b,True{},backing}
def admitted(+s: KState,+kind: Nat,+current: Nat,+target: Nat) -> KOutcome:
  refused=Bool.or(Nat.is_eq(target,current),Bool.not(present(s,target)))
  removal=Bool.pick(KOutcome,refused,KOutcome{s,1n,current},KOutcome{without(s,target),0n,current})
  Bool.pick(KOutcome,Nat.is_eq(kind,1n),KOutcome{added(s),0n,2n},Bool.pick(KOutcome,Nat.is_eq(kind,2n),KOutcome{changed(without(s,current)),0n,3n},Bool.pick(KOutcome,Nat.is_eq(kind,3n),removal,Bool.pick(KOutcome,Nat.is_eq(kind,4n),KOutcome{s,1n,current},KOutcome{s,0n,current}))))
def run(+s: KState,+kind: Nat,password: Nat,hint: Nat,+target: Nat) -> KOutcome:
  +current=access(s,password,hint)
  Bool.pick(KOutcome,Nat.is_eq(current,0n),KOutcome{s,12n,0n},admitted(s,kind,current,target))
def render(r: KOutcome) -> String:
  match r:
    case KOutcome{KState{a,b,c,backing},exit,current}:
      Bool.pick(String,a,"1","0") ++ "/" ++ Bool.pick(String,b,"1","0") ++ "/" ++ Bool.pick(String,c,"1","0") ++ "/" ++ Nat.show(backing) ++ "/" ++ Nat.show(exit) ++ "/" ++ Nat.show(current)
law access_key_is_per_process:
  {render(run(KState{True{},True{},False{},1n},0n,1n,2n,0n)) == "1/1/0/1/0/2" : String}
def access_key_is_per_process(): {==}
law same_password_adds_an_independent_wrapper:
  {render(run(KState{True{},False{},False{},1n},1n,1n,1n,0n)) == "1/1/0/1/0/2" : String}
def same_password_adds_an_independent_wrapper(): {==}
law another_key_does_not_allow_removing_current:
  {render(run(KState{True{},True{},False{},1n},3n,1n,1n,1n)) == "1/1/0/1/1/1" : String}
def another_key_does_not_allow_removing_current(): {==}
law password_change_only_removes_used_wrapper:
  {render(run(KState{True{},True{},False{},1n},2n,1n,1n,0n)) == "0/1/1/1/0/3" : String}
def password_change_only_removes_used_wrapper(): {==}
law old_password_opens_remaining_wrapper:
  {render(run(KState{False{},True{},True{},1n},0n,1n,2n,0n)) == "0/1/1/1/0/2" : String}
def old_password_opens_remaining_wrapper(): {==}
law wrong_password_cannot_add:
  {render(run(KState{False{},True{},True{},1n},1n,3n,0n,0n)) == "0/1/1/1/12/0" : String}
def wrong_password_cannot_add(): {==}
law empty_new_password_refuses:
  {render(run(KState{False{},True{},True{},1n},4n,2n,3n,0n)) == "0/1/1/1/1/3" : String}
def empty_new_password_refuses(): {==}
law revoked_password_cannot_open_remaining_key:
  {render(run(KState{False{},True{},False{},1n},0n,2n,3n,0n)) == "0/1/0/1/12/0" : String}
def revoked_password_cannot_open_remaining_key(): {==}
law unknown_key_cannot_be_removed:
  {render(run(KState{False{},True{},False{},1n},3n,1n,2n,4n)) == "0/1/0/1/1/2" : String}
def unknown_key_cannot_be_removed(): {==}
