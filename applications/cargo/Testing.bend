import Base

def selected(+scope: Nat) -> List<&2,Nat>:
  Bool.pick(List<&2,Nat>,Nat.is_eq(scope,1n),[0n],
    Bool.pick(List<&2,Nat>,Nat.is_eq(scope,2n),[3n],
      Bool.pick(List<&2,Nat>,Nat.is_eq(scope,3n),[5n],
        Bool.pick(List<&2,Nat>,Nat.is_eq(scope,4n),[0n,1n,2n,3n,4n],[0n,1n,2n,3n,5n]))))
def unit_bodies(+id: Nat,+filter: Nat) -> List<&2,Nat>:
  Bool.pick(List<&2,Nat>,Nat.is_eq(id,0n),
    Bool.pick(List<&2,Nat>,Nat.is_eq(filter,1n),[1n],
      Bool.pick(List<&2,Nat>,Nat.is_eq(filter,2n),[],
        Bool.pick(List<&2,Nat>,Nat.is_eq(filter,3n),[2n],[0n,1n]))),
    Bool.pick(List<&2,Nat>,Nat.is_eq(id,1n),[3n],
      Bool.pick(List<&2,Nat>,Nat.is_eq(id,2n),[4n],
        Bool.pick(List<&2,Nat>,Nat.is_eq(id,3n),[5n],
          Bool.pick(List<&2,Nat>,Nat.is_eq(id,5n),[6n],[])))))
def failed(id: Nat,filter: Nat,fail: Bool) -> Bool:
  Bool.and(Nat.is_eq(id,0n),Bool.and(Nat.is_eq(filter,0n),fail))
def append(left: List<&2,Nat>,right: List<&2,Nat>) -> List<&2,Nat>:
  match left:
    case Nil{}: right
    case Con{head,tail}: Con{head,append(tail,right)}
def invoked(values: List<&2,Nat>,+filter: Nat,+fail: Bool,+keep: Bool) -> List<&2,Nat>:
  match values:
    case Nil{}: []
    case Con{+head,+tail}:
      Bool.pick(List<&2,Nat>,Bool.and(failed(head,filter,fail),Bool.not(keep)),[head],Con{head,invoked(tail,filter,fail,keep)})
def bodies(values: List<&2,Nat>,+filter: Nat,+fail: Bool,+keep: Bool) -> List<&2,Nat>:
  match values:
    case Nil{}: []
    case Con{+head,+tail}:
      Bool.pick(List<&2,Nat>,Bool.and(failed(head,filter,fail),Bool.not(keep)),unit_bodies(head,filter),append(unit_bodies(head,filter),bodies(tail,filter,fail,keep)))
def all_success(values: List<&2,Nat>,+filter: Nat,+fail: Bool) -> Bool:
  match values:
    case Nil{}: True{}
    case Con{head,tail}: Bool.and(Bool.not(failed(head,filter,fail)),all_success(tail,filter,fail))
def refused(scope: Nat,no_run: Bool) -> Bool:
  Bool.and(Nat.is_eq(scope,3n),no_run)
def run_invoked(scope: Nat,filter: Nat,no_run: Bool,fail: Bool,keep: Bool) -> List<&2,Nat>:
  Bool.pick(List<&2,Nat>,no_run,[],invoked(selected(scope),filter,fail,keep))
def run_bodies(scope: Nat,filter: Nat,no_run: Bool,fail: Bool,keep: Bool) -> List<&2,Nat>:
  Bool.pick(List<&2,Nat>,no_run,[],bodies(selected(scope),filter,fail,keep))
def success(+scope: Nat,filter: Nat,+no_run: Bool,fail: Bool) -> Bool:
  Bool.and(Bool.not(refused(scope,no_run)),Bool.or(no_run,all_success(selected(scope),filter,fail)))
def show_units(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: Nat.show(head) ++ "," ++ show_units(tail)

law compile_only_no_bodies:
  {run_bodies(0n,0n,True{},False{},False{}) == [] : List<&2,Nat>}
def compile_only_no_bodies(): {==}
law compile_only_success:
  {success(0n,0n,True{},False{}) == True{} : Bool}
def compile_only_success(): {==}
law doc_no_run_refused:
  {refused(3n,True{}) == True{} : Bool}
def doc_no_run_refused(): {==}
law empty_filter_no_body:
  {run_bodies(1n,2n,False{},False{},False{}) == [] : List<&2,Nat>}
def empty_filter_no_body(): {==}
law custom_filter_not_libtest:
  {run_bodies(2n,2n,False{},False{},False{}) == [5n] : List<&2,Nat>}
def custom_filter_not_libtest(): {==}
law failure_completes_harness:
  {run_bodies(0n,0n,False{},True{},False{}) == [0n,1n] : List<&2,Nat>}
def failure_completes_harness(): {==}
law continuation_reaches_docs:
  {run_invoked(0n,0n,False{},True{},True{}) == [0n,1n,2n,3n,5n] : List<&2,Nat>}
def continuation_reaches_docs(): {==}
law all_targets_excludes_docs:
  {run_invoked(4n,0n,False{},False{},False{}) == [0n,1n,2n,3n,4n] : List<&2,Nat>}
def all_targets_excludes_docs(): {==}
