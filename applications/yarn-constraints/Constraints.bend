import Base

type CImage is Data:
  CImage{counter: Nat, root_license: Nat, child_license: Nat, object: Nat}
type CPass is Data:
  CPass{image: CImage, remaining: Bool, throws: Bool}
type CResult is Data:
  CResult{image: CImage, exit: Nat, evaluations: Nat}

def simple(s: CImage,+fix: Bool) -> CPass:
  match s:
    case CImage{counter,+root,+child,object}:
      needed=Bool.or(Bool.not(Nat.is_eq(root,1n)),Bool.not(Nat.is_eq(child,1n)))
      CPass{CImage{counter,Bool.pick(Nat,fix,1n,root),Bool.pick(Nat,fix,1n,child),object},Bool.and(Bool.not(fix),needed),False{}}
def mixed(s: CImage,fix: Bool) -> CPass:
  match s:
    case CImage{counter,root,child,object}: CPass{CImage{counter,root,Bool.pick(Nat,fix,1n,child),object},True{},False{}}
def chain(s: CImage,+fix: Bool) -> CPass:
  match s:
    case CImage{+counter,root,child,object}:
      +needed=Nat.is_lt(counter,12n)
      CPass{CImage{Bool.pick(Nat,Bool.and(fix,needed),Nat.add(counter,1n),counter),root,child,object},Bool.and(Bool.not(fix),needed),False{}}
def late_throw(s: CImage,+fix: Bool) -> CPass:
  match s:
    case CImage{+counter,+root,+child,+object}:
      CPass{Bool.pick(CImage,Nat.is_eq(counter,1n),CImage{counter,root,child,object},CImage{Bool.pick(Nat,fix,1n,counter),root,child,object}),Bool.and(Bool.not(fix),Bool.not(Nat.is_eq(counter,1n))),Nat.is_eq(counter,1n)}
def same_object(s: CImage,+fix: Bool) -> CPass:
  match s:
    case CImage{counter,root,child,+object}:
      CPass{CImage{counter,root,child,Bool.pick(Nat,fix,1n,object)},Bool.and(Bool.not(fix),Bool.not(Nat.is_eq(object,1n))),False{}}
def process(+mode: Nat,+fix: Bool,+s: CImage) -> CPass:
  Bool.pick(CPass,Nat.is_eq(mode,0n),simple(s,fix),Bool.pick(CPass,Nat.is_eq(mode,1n),mixed(s,fix),Bool.pick(CPass,Nat.is_eq(mode,2n),chain(s,fix),Bool.pick(CPass,Nat.is_eq(mode,3n),late_throw(s,fix),Bool.pick(CPass,Nat.is_eq(mode,4n),same_object(s,fix),CPass{s,True{},False{}})))))

def increment(r: CResult) -> CResult:
  match r:
    case CResult{s,exit,n}: CResult{s,exit,Nat.add(n,1n)}
def pass_image(p: CPass) -> CImage:
  match p:
    case CPass{s,_,_}: s
def terminal(p: CPass) -> CResult:
  match p:
    case CPass{s,remaining,_}: CResult{s,Bool.pick(Nat,remaining,1n,0n),1n}
def stopped(p: CPass) -> CResult:
  match p:
    case CPass{s,_,_}: CResult{s,1n,1n}
def threw(p: CPass) -> Bool:
  match p:
    case CPass{_,_,throws}: throws
def after_pass(rest: Nat,p: CPass,more: CResult) -> CResult:
  match rest:
    case Zero{}: terminal(p)
    case Succ{_}: increment(more)
def result_of(+p: CPass,rest: Nat,more: CResult) -> CResult:
  Bool.pick(CResult,threw(p),stopped(p),after_pass(rest,p,more))
def loop(fuel: Nat,+mode: Nat,+fix: Bool,s: CImage) -> CResult:
  match fuel:
    case Zero{}: CResult{s,0n,0n}
    case Succ{+rest}:
      +p=process(mode,fix,s)
      result_of(p,rest,loop(rest,mode,fix,pass_image(p)))
def current(+mode: Nat,+fix: Bool,s: CImage) -> CResult:
  loop(Bool.pick(Nat,fix,10n,1n),mode,fix,s)
def invalid(p: CPass) -> Bool:
  match p:
    case CPass{_,remaining,throws}: Bool.or(remaining,throws)
def proposed_status(mode: Nat,r: CResult) -> Nat:
  match r:
    case CResult{s,exit,_}: Bool.pick(Nat,Bool.or(Bool.not(Nat.is_eq(exit,0n)),invalid(process(mode,False{},s))),1n,0n)
def render(r: CResult) -> String:
  match r:
    case CResult{CImage{counter,root,child,object},exit,n}:
      Nat.show(counter) ++ "/" ++ Nat.show(root) ++ "/" ++ Nat.show(child) ++ "/" ++ Nat.show(object) ++ "/" ++ Nat.show(exit) ++ "/" ++ Nat.show(n)
def empty() -> CImage:
  CImage{0n,0n,0n,0n}
def has_fixable(+mode: Nat,s: CImage) -> Bool:
  match s:
    case CImage{+counter,+root,+child,object}:
      Bool.pick(Bool,Nat.is_eq(mode,0n),Bool.or(Bool.not(Nat.is_eq(root,1n)),Bool.not(Nat.is_eq(child,1n))),Bool.pick(Bool,Nat.is_eq(mode,1n),Bool.not(Nat.is_eq(child,1n)),Bool.pick(Bool,Nat.is_eq(mode,2n),Nat.is_lt(counter,12n),Bool.pick(Bool,Nat.is_eq(mode,3n),Bool.not(Nat.is_eq(counter,1n)),Bool.pick(Bool,Nat.is_eq(mode,4n),Bool.not(Nat.is_eq(object,1n)),False{})))))
def human_guidance(mode: Nat,fix: Bool,s: CImage) -> Bool:
  Bool.and(Bool.not(fix),has_fixable(mode,s))

law stable_simple_fix_still_uses_ten_passes:
  {render(current(0n,True{},empty())) == "0/1/1/0/0/10" : String}
def stable_simple_fix_still_uses_ten_passes():
  {==}
law mixed_conflict_preserves_child_fix:
  {render(current(1n,True{},empty())) == "0/0/1/0/1/10" : String}
def mixed_conflict_preserves_child_fix():
  {==}
law capped_success_is_not_convergence:
  {render(current(2n,True{},empty())) == "10/0/0/0/0/10" : String}
def capped_success_is_not_convergence():
  {==}
law later_throw_preserves_earlier_counter:
  {render(current(3n,True{},empty())) == "1/0/0/0/1/2" : String}
def later_throw_preserves_earlier_counter():
  {==}
law shared_object_succeeds:
  {render(current(4n,True{},empty())) == "0/0/0/1/0/10" : String}
def shared_object_succeeds():
  {==}
law equal_objects_conflict:
  {render(current(5n,True{},empty())) == "0/0/0/0/1/10" : String}
def equal_objects_conflict():
  {==}
law proposed_final_check_refuses_unfinished_chain:
  {proposed_status(2n,current(2n,True{},empty())) == 1n : Nat}
def proposed_final_check_refuses_unfinished_chain():
  {==}
law unmet_check_has_human_guidance:
  {human_guidance(0n,False{},empty()) == True{} : Bool}
def unmet_check_has_human_guidance():
  {==}
