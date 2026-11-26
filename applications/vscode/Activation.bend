import Base

# Override0=inherit,1=allow,2=deny. ScopeFalse=A,True=B.
# Actions0=start,1=activate,2=disable,3=enable,4=held-ping,5=quit,6=retire.
type Policy is Data:
  Policy{disabled: Bool,a: Nat,b: Nat}
type State is Data:
  State{policy: Policy,scope: Bool,alive: Bool,quitting: Bool,visible: Bool,active: Bool}
def override_for(policy: Policy,scope: Bool) -> Nat:
  match policy:
    case Policy{_,a,b}: Bool.pick(Nat,scope,b,a)
def allows_override(disabled: Bool,value: Nat) -> Bool:
  match value:
    case 0n: Bool.not(disabled)
    case 1n: True{}
    case _: False{}
def allows(policy: Policy,scope: Bool) -> Bool:
  match policy:
    case Policy{disabled,a,b}: allows_override(disabled,Bool.pick(Nat,scope,b,a))
def set_workspace(policy: Policy,+scope: Bool,+value: Nat) -> Policy:
  match policy:
    case Policy{disabled,+a,+b}: Policy{disabled,Bool.pick(Nat,scope,a,value),Bool.pick(Nat,scope,value,b)}
def step(state: State,+workspace: Bool,action: Nat) -> State:
  match state:
    case State{+policy,+scope,alive,quitting,+visible,+active}:
      match action:
        case 0n: State{policy,workspace,True{},False{},allows(policy,workspace),False{}}
        case 1n: State{policy,scope,alive,quitting,visible,visible}
        case 2n: State{set_workspace(policy,scope,2n),scope,alive,quitting,active,active}
        case 3n: State{set_workspace(policy,scope,1n),scope,alive,quitting,True{},active}
        case 4n: State{policy,scope,alive,quitting,visible,active}
        case 5n: State{policy,scope,alive,True{},visible,active}
        case _: State{policy,scope,False{},False{},False{},False{}}
def bit(value: Bool) -> String:
  Bool.pick(String,value,"1","0")
def render(after: State,+old_active: Bool,+action: Nat) -> String:
  match after:
    case State{policy,scope,+alive,_,+visible,+active}:
      Bool.pick(String,alive,bit(visible),"~") ++ "/" ++
      Bool.pick(String,Bool.and(alive,visible),bit(active),"~") ++ "/" ++
      bit(Bool.or(Bool.and(Nat.is_eq(action,1n),active),Bool.and(Nat.is_eq(action,4n),old_active))) ++ "/" ++
      Bool.pick(String,Nat.is_eq(action,6n),Nat.show(override_for(policy,scope)),"~") ++ "/" ++
      Bool.pick(String,Nat.is_eq(action,6n),bit(old_active),"~") ++ "/" ++ bit(Bool.not(alive))
def observe(before: State,workspace: Bool,+action: Nat) -> String:
  match before:
    case State{policy,scope,alive,quitting,visible,+active}: render(step(State{policy,scope,alive,quitting,visible,active},workspace,action),active,action)
def running() -> State:
  State{Policy{False{},0n,0n},False{},True{},False{},True{},True{}}

law workspace_allow_overrides_global:
  for disabled: Bool
  {allows(Policy{disabled,1n,0n},False{}) == True{} : Bool}
def workspace_allow_overrides_global(disabled): {==}
law inherited_global_disable:
  for disabled: Bool
  {allows(Policy{disabled,0n,0n},False{}) == Bool.not(disabled) : Bool}
def inherited_global_disable(disabled): {==}
law a_change_preserves_b:
  {allows(set_workspace(Policy{False{},0n,0n},False{},2n),True{}) == True{} : Bool}
def a_change_preserves_b(): {==}
law start_does_not_activate:
  {observe(running(),False{},0n) == "1/0/0/~/~/0" : String}
def start_does_not_activate(): {==}
law disable_keeps_activation_flag:
  {observe(running(),False{},2n) == "1/1/0/~/~/0" : String}
def disable_keeps_activation_flag(): {==}
law enable_dormant_is_not_activation:
  {observe(State{Policy{False{},2n,0n},False{},True{},False{},False{},False{}},False{},3n) == "1/0/0/~/~/0" : String}
def enable_dormant_is_not_activation(): {==}
law quit_is_not_retirement:
  {observe(running(),False{},5n) == "1/1/0/~/~/0" : String}
def quit_is_not_retirement(): {==}
law retire_clears_observable_runtime:
  {observe(running(),False{},6n) == "~/~/0/0/1/1" : String}
def retire_clears_observable_runtime(): {==}
law held_api_after_policy_change:
  {observe(step(running(),False{},2n),False{},4n) == "1/1/1/~/~/0" : String}
def held_api_after_policy_change(): {==}
law restart_applies_workspace_deny:
  {observe(step(step(running(),False{},2n),False{},6n),False{},0n) == "0/~/0/~/~/0" : String}
def restart_applies_workspace_deny(): {==}
law other_workspace_still_admitted:
  {observe(step(step(running(),False{},2n),False{},6n),True{},0n) == "1/0/0/~/~/0" : String}
def other_workspace_still_admitted(): {==}
law inactive_quit_has_no_target_hooks:
  {observe(State{Policy{False{},1n,0n},False{},True{},True{},True{},False{}},False{},6n) == "~/~/0/1/0/1" : String}
def inactive_quit_has_no_target_hooks(): {==}
