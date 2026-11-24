import Base

# One admitted regular-file change. Shape/crypto/native authority are external.
type RView is Data:
  RView{supported: Bool, root: Bool, committed: Bool, restoring: Bool, position: Nat, object: Bool, candidate: Bool, before: Bool}
type RRequest is Data:
  RRequest{mode: Nat, restore: Bool, accepted: Bool, operation: Bool, same_journal: Bool, same_visible: Bool, prepared: RView, observed: RView}
type ROutcome is Data:
  ROutcome{success: Bool, plan: Nat, position: Nat, committed: Bool, restoring: Bool, scratch: Bool}
# plan0=unprepared;plan1=no change;plan2=one change.
def supported(v: RView) -> Bool:
  match v:
    case RView{s,r,_,_,_,_,_,_}: Bool.and(s,r)
def inverse(v: RView,restore: Bool) -> Bool:
  match v:
    case RView{_,_,_,r,_,_,_,_}: Bool.and(restore,Bool.not(r))
def candidate_needed(+v: RView,+restore: Bool) -> Bool:
  match v:
    case RView{_,_,_,_,p,_,_,_}: Bool.and(Bool.not(inverse(v,restore)),Bool.not(Nat.is_eq(p,1n)))
def target(v: RView) -> Bool:
  match v:
    case RView{_,_,_,_,+p,o,_,_}: Bool.or(Nat.is_eq(p,1n),Bool.and(Nat.is_eq(p,0n),o))
def preflight(+v: RView,restore: Bool) -> Bool:
  match v:
    case RView{_,_,_,_,_,_,c,_}: Bool.and(target(v),Bool.or(Bool.not(candidate_needed(v,restore)),c))
def before_needed(+v: RView,restore: Bool) -> Bool:
  match v:
    case RView{_,_,_,_,p,_,_,_}: Bool.and(inverse(v,restore),Bool.not(Nat.is_eq(p,0n)))
def changes(+v: RView,restore: Bool) -> Nat:
  match v:
    case RView{_,_,_,_,p,_,_,_}: Bool.pick(Nat,Nat.is_eq(p,Bool.pick(Nat,inverse(v,restore),0n,1n)),1n,2n)
def unchanged(v: RView,ok: Bool,plan: Nat,scratch: Bool) -> ROutcome:
  match v:
    case RView{_,_,c,r,p,_,_,_}: ROutcome{ok,plan,p,c,r,scratch}
def execute(+v: RView,+restore: Bool,+plan: Nat) -> ROutcome:
  match v:
    case RView{_,_,_,r,_,_,_,b}:
      +copy=before_needed(v,restore)
      Bool.pick(ROutcome,Bool.and(copy,Bool.not(b)),unchanged(v,False{},plan,True{}),ROutcome{True{},plan,Bool.pick(Nat,inverse(v,restore),0n,1n),True{},Bool.or(r,restore),copy})
def prepared_result(mode: Nat,+restore: Bool,accepted: Bool,journal: Bool,visible: Bool,+p: RView,+v: RView) -> ROutcome:
  +plan=changes(p,restore)
  +ready=Bool.and(Bool.and(journal,visible),Bool.and(supported(v),preflight(v,restore)))
  result=Bool.pick(ROutcome,ready,execute(v,restore,plan),unchanged(v,False{},plan,False{}))
  Bool.pick(ROutcome,Bool.or(Nat.is_eq(mode,1n),Bool.not(accepted)),unchanged(v,True{},plan,False{}),result)
def evaluate(q: RRequest) -> ROutcome:
  match q:
    case RRequest{+mode,+restore,a,+op,j,o,+p,+v}:
      match p:
        case RView{_,_,c,_,_,_,_,_}:
          planned=prepared_result(mode,restore,a,j,o,p,v)
          request_result=Bool.pick(ROutcome,Bool.or(c,Bool.not(preflight(p,restore))),unchanged(v,False{},0n,False{}),planned)
          inspected=Bool.pick(ROutcome,Nat.is_eq(mode,0n),unchanged(v,True{},0n,False{}),request_result)
          Bool.pick(ROutcome,Bool.and(supported(p),op),inspected,unchanged(v,False{},0n,False{}))
# PROPOSED preparation-only change;execute must still recheck its own inputs.
def proposed(+v: RView,+restore: Bool) -> Bool:
  match v:
    case RView{_,_,c,_,_,_,_,b}:
      Bool.and(Bool.and(supported(v),Bool.not(c)),Bool.and(preflight(v,restore),Bool.or(Bool.not(before_needed(v,restore)),b)))
def render(o: ROutcome) -> String:
  match o:
    case ROutcome{s,p,t,c,r,b}:
      Bool.pick(String,s,"0","1") ++ "/" ++ Nat.show(p) ++ "/" ++ Nat.show(t) ++ "/" ++ Bool.pick(String,c,"1","0") ++ "/" ++ Bool.pick(String,r,"1","0") ++ "/" ++ Bool.pick(String,b,"1","0")
def view(p: Nat,r: Bool,o: Bool,c: Bool,b: Bool) -> RView:
  RView{True{},True{},False{},r,p,o,c,b}
def request(+v: RView,r: Bool) -> RRequest:
  RRequest{2n,r,True{},True{},True{},True{},v,v}
law before_finish_needs_candidate:
  {candidate_needed(view(0n,False{},True{},True{},True{}),False{}) == True{} : Bool}
def before_finish_needs_candidate():
  {==}
law after_finish_does_not_need_candidate:
  {candidate_needed(view(1n,False{},True{},False{},True{}),False{}) == False{} : Bool}
def after_finish_does_not_need_candidate():
  {==}
law restoring_finish_follows_inverse_after:
  {render(evaluate(request(view(0n,True{},True{},True{},True{}),False{}))) == "0/2/1/1/1/0" : String}
def restoring_finish_follows_inverse_after():
  {==}
law restoring_restore_does_not_invert_again:
  {render(evaluate(request(view(0n,True{},True{},True{},True{}),True{}))) == "0/2/1/1/1/0" : String}
def restoring_restore_does_not_invert_again():
  {==}
law corrupt_before_fails_with_scratch:
  {render(evaluate(request(view(1n,False{},True{},True{},False{}),True{}))) == "1/2/1/0/0/1" : String}
def corrupt_before_fails_with_scratch():
  {==}
law unused_corrupt_before_is_not_required:
  {render(evaluate(request(view(0n,False{},True{},True{},False{}),True{}))) == "0/1/0/1/1/0" : String}
def unused_corrupt_before_is_not_required():
  {==}
law unused_forward_candidate_is_not_required:
  {render(evaluate(request(view(1n,False{},True{},False{},True{}),True{}))) == "0/2/0/1/1/1" : String}
def unused_forward_candidate_is_not_required():
  {==}
law same_bytes_do_not_adopt_replacement:
  {render(evaluate(request(view(0n,False{},False{},True{},True{}),False{}))) == "1/0/0/0/0/0" : String}
def same_bytes_do_not_adopt_replacement():
  {==}
law proposed_needed_corrupt_before_refuses:
  {proposed(view(1n,False{},True{},True{},False{}),True{}) == False{} : Bool}
def proposed_needed_corrupt_before_refuses():
  {==}
law proposed_noop_corrupt_before_is_preserved:
  {proposed(view(0n,False{},True{},True{},False{}),True{}) == True{} : Bool}
def proposed_noop_corrupt_before_is_preserved():
  {==}

law other_operation_is_not_approved:
  {render(evaluate(RRequest{2n,False{},True{},False{},True{},True{},view(0n,False{},True{},True{},True{}),view(0n,False{},True{},True{},True{})})) == "1/0/0/0/0/0" : String}
def other_operation_is_not_approved():
  {==}
