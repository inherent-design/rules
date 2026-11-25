import Base
type Selection is Data:
  Selection{left: Nat,right: Nat,copies: Nat}
type Outcome is Data:
  Outcome{selected: Selection,status: Nat,changed: Bool,moved: Bool,manifest: Bool}
def left(s: Selection) -> Nat:
  match s:
    case Selection{v,_,_}: v
def right(s: Selection) -> Nat:
  match s:
    case Selection{_,v,_}: v
def copies(s: Selection) -> Nat:
  match s:
    case Selection{_,_,v}: v
def contains(xs: List<&2,Nat>,v: Nat) -> Bool:
  List.contains(Nat,Nat.is_eq,xs,v)
def differs(+a: Selection,+b: Selection) -> Bool:
  Bool.or(Bool.not(Nat.is_eq(left(a),left(b))),Bool.or(Bool.not(Nat.is_eq(right(a),right(b))),Bool.not(Nat.is_eq(copies(a),copies(b)))))
def preview(before: Selection,status: Nat) -> Outcome:
  Outcome{before,status,False{},False{},False{}}
def applied(+before: Selection,+target: Selection) -> Outcome:
  changed=Bool.or(Bool.not(Nat.is_eq(left(before),left(target))),Bool.not(Nat.is_eq(right(before),right(target))))
  Outcome{target,0n,changed,Bool.not(Nat.is_eq(copies(before),copies(target))),False{}}
def run(npm: Bool,check: Bool,+before: Selection,+target: Selection,allowed_left: List<&2,Nat>,allowed_right: List<&2,Nat>) -> Outcome:
  within=Bool.and(contains(allowed_left,left(target)),Bool.and(contains(allowed_right,right(target)),Bool.or(Nat.is_eq(copies(target),1n),Nat.is_eq(copies(target),2n))))
  coherent=Bool.or(Bool.not(Nat.is_eq(copies(target),1n)),Nat.is_eq(left(target),right(target)))
  valid=Bool.and(within,coherent)
  status=Bool.pick(Nat,Bool.or(npm,Bool.not(differs(before,target))),0n,1n)
  Bool.pick(Outcome,valid,Bool.pick(Outcome,check,preview(before,status),applied(before,target)),preview(before,2n))
def render(o: Outcome) -> String:
  match o:
    case Outcome{Selection{l,r,c},status,changed,moved,manifest}:
      Nat.show(l) ++ "/" ++ Nat.show(r) ++ "/" ++ Nat.show(c) ++ "/" ++ Nat.show(status) ++ "/" ++ Bool.show(changed) ++ "/" ++ Bool.show(moved) ++ "/" ++ Bool.show(manifest)
def highest_walk(candidates: List<&2,Nat>,+current: Nat,+allowed: List<&2,Nat>) -> Nat:
  match candidates:
    case Nil{}: current
    case Con{+head,tail}: highest_walk(tail,Bool.pick(Nat,contains(allowed,head),Nat.max(current,head),current),allowed)
def highest(current: Nat,allowed: List<&2,Nat>,candidates: List<&2,Nat>) -> Nat:
  highest_walk(candidates,current,allowed)
law npm_preview_can_succeed_with_changes:
  {render(run(True{},True{},Selection{1n,2n,2n},Selection{1n,3n,2n},[1n],[2n,3n])) == "1/2/2/0/False/False/False" : String}
def npm_preview_can_succeed_with_changes():
  {==}
law explicit_check_reports_changes:
  {render(run(False{},True{},Selection{1n,2n,2n},Selection{2n,2n,1n},[1n,2n,3n],[2n,3n])) == "1/2/2/1/False/False/False" : String}
def explicit_check_reports_changes():
  {==}
law exact_pin_does_not_allow_consolidation:
  {render(run(False{},False{},Selection{1n,2n,2n},Selection{2n,2n,1n},[1n],[2n,3n])) == "1/2/2/2/False/False/False" : String}
def exact_pin_does_not_allow_consolidation():
  {==}
law version_update_need_not_reduce_copies:
  {render(run(True{},False{},Selection{1n,2n,2n},Selection{1n,3n,2n},[1n],[2n,3n])) == "1/3/2/0/True/False/False" : String}
def version_update_need_not_reduce_copies():
  {==}
law highest_uses_saved_candidates:
  {highest(1n,[1n,2n,3n],[1n,2n]) == 2n : Nat}
def highest_uses_saved_candidates():
  {==}

law one_copy_cannot_have_two_plain_versions:
  {render(run(False{},False{},Selection{1n,2n,2n},Selection{1n,2n,1n},[1n],[2n])) == "1/2/2/2/False/False/False" : String}
def one_copy_cannot_have_two_plain_versions():
  {==}
