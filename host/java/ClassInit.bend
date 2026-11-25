import Base

# Serial authored-class profile, not arbitrary JVM loading or synchronization.
type CIDecision is Data:
  CIDecision{next: Nat,code: Nat,effect: Bool}
type CICell is Data:
  CICell{defined: Bool,status: Nat}
type CIAction is Data:
  CIAction{target: Nat,loader: Nat,request: Bool,array: Bool}
type CIState is Data:
  CIState{cells: List<&2,CICell>,seen: List<&2,Nat>,good: Nat,bad: Nat,hard: Nat,array: Nat,findA: Nat,findB: Nat}
type CIResult is Data:
  CIResult{state: CIState,code: Nat,identity: Nat,loader: Nat}

def ci_init(+status: Nat,+target: Nat,request: Bool) -> CIDecision:
  Bool.pick(CIDecision,request,
    Bool.pick(CIDecision,Nat.is_eq(status,1n),CIDecision{1n,0n,False{}},
      Bool.pick(CIDecision,Nat.is_eq(status,2n),CIDecision{2n,3n,False{}},
        Bool.pick(CIDecision,Nat.is_eq(target,1n),CIDecision{2n,2n,True{}},
          Bool.pick(CIDecision,Nat.is_eq(target,2n),CIDecision{2n,4n,True{}},CIDecision{1n,0n,True{}})))),
    CIDecision{status,0n,False{}})
def ci_cells(n: Nat) -> List<&2,CICell>:
  match n:
    case 0n: Nil{}
    case 1n+p: Con{CICell{False{},0n},ci_cells(p)}
def ci_empty() -> CIState:
  CIState{ci_cells(15n),Nil{},0n,0n,0n,0n,0n,0n}
def ci_at(cells: List<&2,CICell>,+index: Nat) -> CICell:
  match cells:
    case Nil{}: CICell{False{},0n}
    case Con{head,tail}: Bool.pick(CICell,Nat.is_eq(index,0n),head,ci_at(tail,Nat.sub(index,1n)))
def ci_replace(cells: List<&2,CICell>,+index: Nat,+value: CICell) -> List<&2,CICell>:
  match cells:
    case Nil{}: Nil{}
    case Con{+head,+tail}: Bool.pick(List<&2,CICell>,Nat.is_eq(index,0n),Con{value,tail},Con{head,ci_replace(tail,Nat.sub(index,1n),value)})
def ci_seen(seen: List<&2,Nat>,+key: Nat,+position: Nat) -> Nat:
  match seen:
    case Nil{}: 0n
    case Con{head,tail}: Bool.pick(Nat,Nat.is_eq(head,key),Nat.add(position,1n),ci_seen(tail,key,Nat.add(position,1n)))
def ci_append(seen: List<&2,Nat>,+key: Nat) -> List<&2,Nat>:
  match seen:
    case Nil{}: Con{key,Nil{}}
    case Con{head,tail}: Con{head,ci_append(tail,key)}
def ci_bit(value: Bool) -> Nat:
  Bool.pick(Nat,value,1n,0n)
def ci_action_cell(state: CIState,action: CIAction) -> CICell:
  match state action:
    case CIState{cells,_,_,_,_,_,_,_} CIAction{target,loader,_,_}: ci_at(cells,Nat.add(Nat.mul(loader,5n),target))
def ci_decision(action: CIAction,cell: CICell) -> CIDecision:
  match action cell:
    case CIAction{+target,_,request,array} CICell{_,+status}:
      Bool.pick(CIDecision,Nat.is_eq(target,4n),CIDecision{status,1n,False{}},ci_init(status,target,Bool.and(request,Bool.not(array))))
def ci_step_decision(state: CIState,action: CIAction,cell: CICell,decision: CIDecision) -> CIResult:
  match state action cell decision:
    case CIState{+cells,+seen,good,bad,hard,arr,findA,findB} CIAction{+target,+loader,_,array} CICell{defined,_} CIDecision{next,+code,+effect}:
      +index=Nat.add(Nat.mul(loader,5n),target)
      +find=Bool.and(Bool.not(Nat.is_eq(loader,0n)),Bool.or(Bool.not(defined),Nat.is_eq(target,4n)))
      findA=Nat.add(findA,ci_bit(Bool.and(find,Nat.is_eq(loader,1n))))
      findB=Nat.add(findB,ci_bit(Bool.and(find,Nat.is_eq(loader,2n))))
      cells=Bool.pick(List<&2,CICell>,Nat.is_eq(target,4n),cells,ci_replace(cells,index,CICell{True{},next}))
      +ok=Nat.is_eq(code,0n)
      +key=Nat.add(Nat.mul(index,2n),ci_bit(array))
      +existing=ci_seen(seen,key,0n)
      identity=Bool.pick(Nat,ok,Bool.pick(Nat,Nat.is_eq(existing,0n),Nat.add(List.length(&2,Nat,seen),1n),existing),0n)
      seen=Bool.pick(List<&2,Nat>,Bool.and(ok,Nat.is_eq(existing,0n)),ci_append(seen,key),seen)
      good=Nat.add(good,ci_bit(Bool.and(effect,Nat.is_eq(target,0n))))
      bad=Nat.add(bad,ci_bit(Bool.and(effect,Nat.is_eq(target,1n))))
      hard=Nat.add(hard,ci_bit(Bool.and(effect,Nat.is_eq(target,2n))))
      arr=Nat.add(arr,ci_bit(Bool.and(effect,Nat.is_eq(target,3n))))
      CIResult{CIState{cells,seen,good,bad,hard,arr,findA,findB},code,identity,Bool.pick(Nat,ok,Nat.add(loader,1n),0n)}
def ci_step(+state: CIState,+action: CIAction) -> CIResult:
  +cell=ci_action_cell(state,action)
  ci_step_decision(state,action,cell,ci_decision(action,cell))
def ci_state(result: CIResult) -> CIState:
  match result:
    case CIResult{s,_,_,_}: s
def ci_render(result: CIResult) -> String:
  match result:
    case CIResult{CIState{_,_,g,b,h,a,fa,fb},+code,identity,loader}:
      Nat.show(code) ++ ":" ++ Nat.show(ci_bit(Nat.is_eq(code,0n))) ++ ":" ++ Nat.show(identity) ++ ":" ++ Nat.show(loader) ++ ":" ++ Nat.show(ci_bit(Nat.is_eq(code,1n))) ++ ":" ++ Nat.show(ci_bit(Nat.is_eq(code,1n))) ++ ":" ++ Nat.show(g) ++ ":" ++ Nat.show(b) ++ ":" ++ Nat.show(h) ++ ":" ++ Nat.show(a) ++ ":" ++ Nat.show(fa) ++ ":" ++ Nat.show(fb)
def ci_trace(actions: List<&2,CIAction>,state: CIState) -> String:
  match actions:
    case Nil{}: ""
    case Con{action,rest}:
      +result=ci_step(state,action)
      ci_render(result) ++ "\n" ++ ci_trace(rest,ci_state(result))

law ci_no_init:
  {ci_init(0n,0n,False{}) == CIDecision{0n,0n,False{}} : CIDecision}
def ci_no_init():
  {==}
law ci_already_initialized:
  {ci_init(1n,0n,True{}) == CIDecision{1n,0n,False{}} : CIDecision}
def ci_already_initialized():
  {==}
law ci_erroneous_retry:
  {ci_init(2n,1n,True{}) == CIDecision{2n,3n,False{}} : CIDecision}
def ci_erroneous_retry():
  {==}
law ci_erroneous_metadata:
  {ci_init(2n,1n,False{}) == CIDecision{2n,0n,False{}} : CIDecision}
def ci_erroneous_metadata():
  {==}
law ci_wrapped_failure:
  {ci_init(0n,1n,True{}) == CIDecision{2n,2n,True{}} : CIDecision}
def ci_wrapped_failure():
  {==}
law ci_error_not_wrapped:
  {ci_init(0n,2n,True{}) == CIDecision{2n,4n,True{}} : CIDecision}
def ci_error_not_wrapped():
  {==}
law ci_success_effect:
  {ci_init(0n,0n,True{}) == CIDecision{1n,0n,True{}} : CIDecision}
def ci_success_effect():
  {==}
law ci_custom_false_effect:
  {ci_render(ci_step(ci_empty(),CIAction{0n,1n,False{},False{}})) == "0:1:1:2:0:0:0:0:0:0:1:0" : String}
def ci_custom_false_effect():
  {==}
law ci_default_init:
  {ci_render(ci_step(ci_empty(),CIAction{0n,0n,True{},False{}})) == "0:1:1:1:0:0:1:0:0:0:0:0" : String}
def ci_default_init():
  {==}
law ci_missing_with_effect:
  {ci_render(ci_step(ci_empty(),CIAction{4n,1n,False{},False{}})) == "1:0:0:0:1:1:0:0:0:0:1:0" : String}
def ci_missing_with_effect():
  {==}
law ci_failure_keeps_effect:
  {ci_render(ci_step(ci_empty(),CIAction{1n,0n,True{},False{}})) == "2:0:0:0:0:0:0:1:0:0:0:0" : String}
def ci_failure_keeps_effect():
  {==}
law ci_failed_retry_does_not_rerun:
  {ci_render(ci_step(ci_state(ci_step(ci_empty(),CIAction{1n,0n,True{},False{}})),CIAction{1n,0n,True{},False{}})) == "3:0:0:0:0:0:0:1:0:0:0:0" : String}
def ci_failed_retry_does_not_rerun():
  {==}
law ci_other_loader_runs_again:
  {ci_render(ci_step(ci_state(ci_step(ci_empty(),CIAction{0n,0n,True{},False{}})),CIAction{0n,1n,True{},False{}})) == "0:1:2:2:0:0:2:0:0:0:1:0" : String}
def ci_other_loader_runs_again():
  {==}
law ci_array_no_component_init:
  {ci_render(ci_step(ci_empty(),CIAction{3n,0n,True{},True{}})) == "0:1:1:1:0:0:0:0:0:0:0:0" : String}
def ci_array_no_component_init():
  {==}
