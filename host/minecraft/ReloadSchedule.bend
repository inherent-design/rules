import Base
def reload_arrived(barrier: Bool,p0: Nat,p1: Nat) -> Bool:
  Bool.and(barrier,Bool.and(Nat.is_eq(p0,1n),Nat.is_eq(p1,1n)))
def reload_first(+barrier: Bool,+fail: Bool,+initial: Nat,+p0: Nat,p1: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(p0,2n),2n,Bool.pick(Nat,Nat.is_eq(p0,0n),0n,
    Bool.pick(Nat,barrier,
      Bool.pick(Nat,Bool.or(Bool.not(reload_arrived(barrier,p0,p1)),Nat.is_eq(initial,0n)),0n,
        Bool.pick(Nat,Nat.is_eq(initial,2n),2n,Bool.pick(Nat,fail,2n,1n))),Bool.pick(Nat,fail,2n,1n))))
def reload_second(barrier: Bool,p0: Nat,+p1: Nat,+state0: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(p1,2n),2n,Bool.pick(Nat,Nat.is_eq(p1,0n),0n,
    Bool.pick(Nat,Bool.or(Bool.not(reload_arrived(barrier,p0,p1)),Nat.is_eq(state0,0n)),0n,
      Bool.pick(Nat,Nat.is_eq(state0,2n),2n,1n))))
def reload_summary(+a: Nat,+b: Nat) -> Nat:
  Bool.pick(Nat,Bool.or(Nat.is_eq(a,2n),Nat.is_eq(b,2n)),2n,
    Bool.pick(Nat,Bool.and(Nat.is_eq(a,1n),Nat.is_eq(b,1n)),1n,0n))
def reload_evaluate(+count: Nat,+shared: Bool,failure: Bool,+initial: Nat,+p0: Nat,+p1: Nat,+barrier: Bool,fail: Bool) -> List<&2, Nat>:
  +a = reload_first(barrier,fail,initial,p0,p1)
  +b = reload_second(barrier,p0,p1,a)
  effect = Bool.and(Nat.is_eq(p0,1n),Bool.or(Bool.not(barrier),Bool.and(reload_arrived(barrier,p0,p1),Nat.is_eq(initial,1n))))
  Bool.pick(List<&2, Nat>,Nat.is_eq(count,0n),[0n,3n,3n,1n,0n,0n,0n,0n],
    Bool.pick(List<&2, Nat>,Bool.and(shared,failure),[1n,3n,3n,3n,0n,0n,2n,0n],
      [0n,a,b,reload_summary(a,b),Bool.pick(Nat,effect,1n,0n),Bool.pick(Nat,Nat.is_eq(b,1n),1n,0n),Bool.pick(Nat,shared,2n,0n),2n]))
law reload_pending_initial:
  {reload_evaluate(2n,False{},False{},0n,1n,1n,True{},False{}) == [0n,0n,0n,0n,0n,0n,0n,2n] : List<&2, Nat>}
def reload_pending_initial():
  {==}
law reload_ordered_success:
  {reload_evaluate(2n,False{},False{},1n,1n,1n,True{},False{}) == [0n,1n,1n,1n,1n,1n,0n,2n] : List<&2, Nat>}
def reload_ordered_success():
  {==}
law reload_failure_not_peer_join:
  {reload_evaluate(2n,False{},False{},1n,2n,0n,True{},False{}) == [0n,2n,0n,2n,0n,0n,0n,2n] : List<&2, Nat>}
def reload_failure_not_peer_join():
  {==}
law reload_failure_not_rollback:
  {reload_evaluate(2n,False{},False{},1n,1n,1n,True{},True{}) == [0n,2n,2n,2n,1n,0n,0n,2n] : List<&2, Nat>}
def reload_failure_not_rollback():
  {==}
law reload_initial_failure_waits_barrier:
  {reload_evaluate(2n,False{},False{},2n,1n,0n,True{},False{}) == [0n,0n,0n,0n,0n,0n,0n,2n] : List<&2, Nat>}
def reload_initial_failure_waits_barrier():
  {==}
law reload_bypass_early_effect:
  {reload_evaluate(2n,False{},False{},0n,1n,0n,False{},False{}) == [0n,1n,0n,0n,1n,0n,0n,2n] : List<&2, Nat>}
def reload_bypass_early_effect():
  {==}
law reload_empty_initial_pending:
  {reload_evaluate(0n,False{},False{},0n,0n,0n,False{},False{}) == [0n,3n,3n,1n,0n,0n,0n,0n] : List<&2, Nat>}
def reload_empty_initial_pending():
  {==}
law reload_shared_failure:
  {reload_evaluate(2n,True{},True{},1n,0n,0n,True{},False{}) == [1n,3n,3n,3n,0n,0n,2n,0n] : List<&2, Nat>}
def reload_shared_failure():
  {==}
