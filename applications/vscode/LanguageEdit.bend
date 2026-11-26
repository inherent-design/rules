import Base
import WorkspaceSearch.bend as S

# This is the admitted ASCII fixture, not a general text/range engine.
# Modes: workspace, guarded, editor-pair, format-compute, format-apply,
# format-command, rename-compute, rename-apply.
type Request is Data:
  Request{mode: Nat,basis: Nat,second_basis: Nat,intervened: Bool,second_empty: Bool}
type Outcome is Data:
  Outcome{response: String,text: String,changes: Nat,canceled: Bool}
def boolean(b: Bool) -> String:
  Bool.pick(String,b,"true","false")
def count(b: Bool) -> Nat:
  Bool.pick(Nat,b,1n,0n)
def editor_allowed(empty: Bool,captured: Nat,current: Nat) -> Bool:
  Bool.or(empty,S.current_guard(captured,current))
def workspace_allowed(guarded: Bool,planned: Nat,+submitted: Nat,+current: Nat) -> Bool:
  Bool.pick(Bool,guarded,S.planned_guard(planned,submitted,current),S.current_guard(submitted,current))
def initial(changed: Bool) -> String:
  Bool.pick(String,changed,"shift alpha beta\n","alpha beta\n")
def replace_initial(changed: Bool,value: String) -> String:
  value ++ Bool.pick(String,changed," alpha beta\n"," beta\n")
def workspace(+guarded: Bool,+basis: Nat,+changed: Bool) -> Outcome:
  +current=Nat.add(basis,count(changed))
  +allowed=workspace_allowed(guarded,basis,current,current)
  Outcome{Bool.pick(String,Bool.and(guarded,Bool.not(allowed)),"not-called",boolean(allowed)),Bool.pick(String,allowed,replace_initial(changed,"EDIT"),initial(changed)),Nat.add(count(changed),count(allowed)),False{}}
def pair(basis: Nat,second_basis: Nat,+empty: Bool) -> Outcome:
  +second=editor_allowed(empty,second_basis,Nat.add(basis,1n))
  +writes=Bool.and(second,Bool.not(empty))
  Outcome{"true," ++ boolean(second),Bool.pick(String,writes,"TWOeta\n","ONE beta\n"),Nat.add(1n,count(writes)),False{}}
def compute(+changed: Bool) -> Outcome:
  Outcome{"returned-edits",initial(changed),count(changed),False{}}
def apply_provider(+changed: Bool,replacement: String) -> Outcome:
  Outcome{"true",replace_initial(changed,replacement),Nat.add(count(changed),1n),False{}}
def format_command(+changed: Bool) -> Outcome:
  Outcome{"undefined",Bool.pick(String,changed,initial(changed),replace_initial(changed,"FMT(alpha)")),1n,changed}
def run(r: Request) -> Outcome:
  match r:
    case Request{mode,basis,second_basis,changed,empty}:
      match mode:
        case 0n: workspace(False{},basis,changed)
        case 1n: workspace(True{},basis,changed)
        case 2n: pair(basis,second_basis,empty)
        case 3n: compute(changed)
        case 4n: apply_provider(changed,"FMT(alpha)")
        case 5n: format_command(changed)
        case 6n: compute(changed)
        case _: apply_provider(changed,"REN")
def render(o: Outcome) -> String:
  match o:
    case Outcome{response,text,changes,canceled}: response ++ "|" ++ Nat.show(changes) ++ "|" ++ boolean(canceled) ++ "|" ++ text

law empty_does_not_check_version:
  for a: Nat
  for b: Nat
  {editor_allowed(True{},a,b) == True{} : Bool}
def empty_does_not_check_version(a,b): {==}
law matching_editor_version_applies:
  for v: Nat
  {editor_allowed(False{},v,v) == True{} : Bool}
def matching_editor_version_applies(v):
  match v:
    case 0n: {==}
    case 1n+p: matching_editor_version_applies(p)
law submission_does_not_retain_plan:
  for p: Nat
  for s: Nat
  {workspace_allowed(False{},p,s,s) == True{} : Bool}
def submission_does_not_retain_plan(p,s): matching_editor_version_applies(s)
law different_editor_version_refuses:
  {editor_allowed(False{},8n,9n) == False{} : Bool}
def different_editor_version_refuses(): {==}
law stricter_caller_guard_refuses:
  {workspace_allowed(True{},3n,4n,4n) == False{} : Bool}
def stricter_caller_guard_refuses(): {==}
law parallel_second_refuses:
  {render(run(Request{2n,8n,8n,False{},False{}})) == "true,false|1|false|ONE beta\n" : String}
def parallel_second_refuses(): {==}
law fresh_sequential_range_is_not_rebased:
  {render(run(Request{2n,10n,11n,False{},False{}})) == "true,true|2|false|TWOeta\n" : String}
def fresh_sequential_range_is_not_rebased(): {==}
law empty_second_does_not_write:
  {render(run(Request{2n,13n,13n,False{},True{}})) == "true,true|1|false|ONE beta\n" : String}
def empty_second_does_not_write(): {==}
law compute_is_not_apply:
  {render(compute(False{})) == "returned-edits|0|false|alpha beta\n" : String}
def compute_is_not_apply(): {==}
law normal_format_preserves_changed_buffer:
  {render(format_command(True{})) == "undefined|1|true|shift alpha beta\n" : String}
def normal_format_preserves_changed_buffer(): {==}
