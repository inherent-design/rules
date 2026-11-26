import Base

# Three-version generated-catalog projection; no general solver/materializer.
type V is Data:
  One{}
  Minor{}
  Two{}
type Profile is Data:
  Npm{}
  Pnpm{}
  Yarn{}
type Selector is Data:
  Global{}
  Parent{}
  Converge{}
  Broad{}
  Narrow{}
type Rule is Data:
  Rule{scope: Selector,version: V}
type ChoicePair is Data:
  ChoicePair{left: V,right: V}
type InstallState is Data:
  InstallState{choices: List<&2,ChoicePair>,manual: Maybe<&2,V>}
type Action is Data:
  Install{}
  SetResolution{}
  Check{}
  RemoveLock{}
  Query{}
type Request is Data:
  Request{action: Action,rules: List<&2,Rule>,target: V}
type StepResult is Data:
  StepResult{exit: Nat,state: InstallState}
def permitted(v: V) -> Bool:
  match v:
    case Two{}: False{}
    case _: True{}
def is_yarn(t: Profile) -> Bool:
  match t:
    case Yarn{}: True{}
    case _: False{}
def is_npm(t: Profile) -> Bool:
  match t:
    case Npm{}: True{}
    case _: False{}
def is_parent(s: Selector) -> Bool:
  match s:
    case Parent{}: True{}
    case _: False{}
def is_converge(s: Selector) -> Bool:
  match s:
    case Converge{}: True{}
    case _: False{}
def explicit_matches(+left: Bool,rs: List<&2,Rule>) -> List<&2,Rule>:
  match rs:
    case Nil{}: Nil{}
    case Con{Rule{+scope,v},+tail}:
      Bool.pick(List<&2,Rule>,Bool.and(Bool.not(is_converge(scope)),Bool.or(Bool.not(is_parent(scope)),left)),Con{Rule{scope,v},explicit_matches(left,tail)},explicit_matches(left,tail))
def parents(rs: List<&2,Rule>) -> List<&2,Rule>:
  match rs:
    case Nil{}: Nil{}
    case Con{Rule{+s,v},+tail}:
      Bool.pick(List<&2,Rule>,is_parent(s),Con{Rule{s,v},parents(tail)},parents(tail))
def preferred_parents(t: Profile,+head: Rule,rs: List<&2,Rule>,+ps: List<&2,Rule>) -> List<&2,Rule>:
  match ps:
    case Nil{}: Bool.pick(List<&2,Rule>,is_yarn(t),[head],rs)
    case Con{_,_}: Bool.pick(List<&2,Rule>,is_yarn(t),[head],ps)
def preferred(t: Profile,+rs: List<&2,Rule>) -> List<&2,Rule>:
  match rs:
    case Nil{}: Nil{}
    case Con{head,_}:
      preferred_parents(t,head,rs,parents(rs))
def same(a: V,b: V) -> Bool:
  match a b:
    case One{} One{}: True{}
    case Minor{} Minor{}: True{}
    case Two{} Two{}: True{}
    case _ _: False{}
def contains(+v: V,vs: List<&2,V>) -> Bool:
  match vs:
    case Nil{}: False{}
    case Con{h,t}: Bool.or(same(v,h),contains(v,t))
def rule_values(rs: List<&2,Rule>,+seen: List<&2,V>) -> List<&2,V>:
  match rs:
    case Nil{}: Nil{}
    case Con{Rule{_,+v},+tail}:
      Bool.pick(List<&2,V>,contains(v,seen),rule_values(tail,seen),Con{v,rule_values(tail,Con{v,seen})})
def converged(rs: List<&2,Rule>) -> List<&2,V>:
  match rs:
    case Nil{}: [Minor{}]
    case Con{Rule{s,+v},tail}:
      Bool.pick(List<&2,V>,Bool.and(is_converge(s),permitted(v)),[v],converged(tail))
def selected_values(+matches: List<&2,Rule>,rs: List<&2,Rule>) -> List<&2,V>:
  match matches:
    case Nil{}: converged(rs)
    case Con{_,_}: rule_values(matches,Nil{})
def values(t: Profile,left: Bool,+rs: List<&2,Rule>) -> List<&2,V>:
  selected_values(preferred(t,explicit_matches(left,rs)),rs)
# Proposed only: strict-containment pair, not a general range algorithm.
def narrow_target(rs: List<&2,Rule>) -> Maybe<&2,V>:
  match rs:
    case Nil{}: None{}
    case Con{Rule{s,v},tail}:
      match s:
        case Narrow{}: Some{v}
        case _: narrow_target(tail)
def candidate_selected(v: Maybe<&2,V>,rs: List<&2,Rule>) -> List<&2,V>:
  match v:
    case Some{x}: [x]
    case None{}: values(Pnpm{},True{},rs)
def candidate_narrowest(+rs: List<&2,Rule>) -> List<&2,V>:
  candidate_selected(narrow_target(rs),rs)
def append(a: List<&2,ChoicePair>,+b: List<&2,ChoicePair>) -> List<&2,ChoicePair>:
  match a:
    case Nil{}: b
    case Con{h,t}: Con{h,append(t,b)}
def paired(+v: V,vs: List<&2,V>) -> List<&2,ChoicePair>:
  match vs:
    case Nil{}: Nil{}
    case Con{h,t}: Con{ChoicePair{v,h},paired(v,t)}
def product(ls: List<&2,V>,+rs: List<&2,V>) -> List<&2,ChoicePair>:
  match ls:
    case Nil{}: Nil{}
    case Con{h,t}: append(paired(h,rs),product(t,rs))
def diagonal(vs: List<&2,V>) -> List<&2,ChoicePair>:
  match vs:
    case Nil{}: Nil{}
    case Con{+h,t}: Con{ChoicePair{h,h},diagonal(t)}
def graph(+t: Profile,+direct: Bool,+rs: List<&2,Rule>) -> List<&2,ChoicePair>:
  +ls=values(t,Bool.not(direct),rs)
  Bool.pick(List<&2,ChoicePair>,direct,diagonal(ls),product(ls,values(t,False{},rs)))
def has_global(rs: List<&2,Rule>) -> Bool:
  match rs:
    case Nil{}: False{}
    case Con{Rule{s,_},tail}:
      match s:
        case Global{}: True{}
        case _: has_global(tail)
def incompatible(ps: List<&2,ChoicePair>) -> Bool:
  match ps:
    case Nil{}: False{}
    case Con{ChoicePair{l,r},tail}: Bool.or(Bool.or(Bool.not(permitted(l)),Bool.not(permitted(r))),incompatible(tail))
def install(+t: Profile,+direct: Bool,+s: InstallState,+rules: List<&2,Rule>) -> StepResult:
  match s:
    case InstallState{_,None{}}:
      Bool.pick(StepResult,Bool.and(is_npm(t),Bool.and(direct,has_global(rules))),StepResult{1n,s},StepResult{0n,InstallState{graph(t,direct,rules),None{}}})
    case InstallState{_,Some{+v}}:
      Bool.pick(StepResult,Bool.and(is_npm(t),Bool.and(direct,has_global(rules))),StepResult{1n,s},StepResult{0n,InstallState{[ChoicePair{v,v}],Some{v}}})
def step(t: Profile,direct: Bool,+s: InstallState,r: Request) -> StepResult:
  match s r:
    case _ Request{Query{},_,_}: StepResult{0n,s}
    case InstallState{ps,_} Request{RemoveLock{},_,_}: StepResult{0n,InstallState{ps,None{}}}
    case InstallState{ps,_} Request{Check{},_,_}: StepResult{Bool.pick(Nat,incompatible(ps),1n,0n),s}
    case _ Request{SetResolution{},_,+v}: StepResult{0n,InstallState{[ChoicePair{v,v}],Some{v}}}
    case _ Request{Install{},rs,_}: install(t,direct,s,rs)
def after_state(result: StepResult) -> InstallState:
  match result:
    case StepResult{_,after}: after
def trace(rs: List<&2,Request>,+t: Profile,+direct: Bool,s: InstallState) -> List<&2,StepResult>:
  match rs:
    case Nil{}: Nil{}
    case Con{r,tail}:
      +result=step(t,direct,s,r)
      Con{result,trace(tail,t,direct,after_state(result))}
def vtext(v: V) -> String:
  match v:
    case One{}: "1.0.0"
    case Minor{}: "1.1.0"
    case Two{}: "2.0.0"
def manual_text(m: Maybe<&2,V>) -> String:
  match m:
    case None{}: "-"
    case Some{v}: vtext(v)
def pair_text(p: ChoicePair) -> String:
  match p:
    case ChoicePair{l,r}: vtext(l) ++ "," ++ vtext(r)
def pairs_text(ps: List<&2,ChoicePair>) -> String:
  match ps:
    case Nil{}: ""
    case Con{h,Nil{}}: pair_text(h)
    case Con{h,t}: pair_text(h) ++ ";" ++ pairs_text(t)
def text(r: StepResult) -> String:
  match r:
    case StepResult{exit,InstallState{ps,m}}: Nat.show(exit) ++ "/" ++ manual_text(m) ++ "/" ++ pairs_text(ps)
def texts(rs: List<&2,StepResult>) -> List<&2,String>:
  match rs:
    case Nil{}: Nil{}
    case Con{h,t}: Con{text(h),texts(t)}
def lines(xs: List<&2,String>) -> String:
  match xs:
    case Nil{}: ""
    case Con{h,t}: h ++ "\n" ++ lines(t)
def base() -> InstallState: InstallState{[ChoicePair{Minor{},Minor{}}],None{}}
def manual() -> InstallState: InstallState{[ChoicePair{Two{},Two{}}],Some{Two{}}}
def global_one() -> Rule: Rule{Global{},One{}}
def parent_two() -> Rule: Rule{Parent{},Two{}}
law query_preserves_state:
  {step(Yarn{},True{},manual(),Request{Query{},[],Two{}}) == StepResult{0n,manual()} : StepResult}
def query_preserves_state(): {==}
law check_refuses_without_repair:
  {step(Yarn{},True{},manual(),Request{Check{},[],Two{}}) == StepResult{1n,manual()} : StepResult}
def check_refuses_without_repair(): {==}
law lock_removal_keeps_installed:
  {step(Yarn{},True{},manual(),Request{RemoveLock{},[],Two{}}) == StepResult{0n,InstallState{[ChoicePair{Two{},Two{}}],None{}}} : StepResult}
def lock_removal_keeps_installed(): {==}
law npm_direct_refusal_preserves_state:
  {step(Npm{},True{},base(),Request{Install{},[Rule{Global{},Two{}}],Two{}}) == StepResult{1n,base()} : StepResult}
def npm_direct_refusal_preserves_state(): {==}
law npm_parent_precedes_global:
  {graph(Npm{},False{},[global_one(),parent_two()]) == [ChoicePair{Two{},One{}}] : List<&2,ChoicePair>}
def npm_parent_precedes_global(): {==}
law pnpm_parent_precedes_global:
  {graph(Pnpm{},False{},[global_one(),parent_two()]) == [ChoicePair{Two{},One{}}] : List<&2,ChoicePair>}
def pnpm_parent_precedes_global(): {==}
law yarn_global_first:
  {graph(Yarn{},False{},[global_one(),parent_two()]) == [ChoicePair{One{},One{}}] : List<&2,ChoicePair>}
def yarn_global_first(): {==}
law yarn_parent_first:
  {graph(Yarn{},False{},[parent_two(),global_one()]) == [ChoicePair{Two{},One{}}] : List<&2,ChoicePair>}
def yarn_parent_first(): {==}
law npm_order_swap_same:
  {graph(Npm{},False{},[global_one(),parent_two()]) == graph(Npm{},False{},[parent_two(),global_one()]) : List<&2,ChoicePair>}
def npm_order_swap_same(): {==}
law pnpm_order_swap_same:
  {graph(Pnpm{},False{},[global_one(),parent_two()]) == graph(Pnpm{},False{},[parent_two(),global_one()]) : List<&2,ChoicePair>}
def pnpm_order_swap_same(): {==}
law pnpm_direct_force:
  {graph(Pnpm{},True{},[Rule{Global{},Two{}}]) == [ChoicePair{Two{},Two{}}] : List<&2,ChoicePair>}
def pnpm_direct_force(): {==}
law yarn_direct_force:
  {graph(Yarn{},True{},[Rule{Global{},Two{}}]) == [ChoicePair{Two{},Two{}}] : List<&2,ChoicePair>}
def yarn_direct_force(): {==}
law convergence_does_not_force_outside:
  {graph(Pnpm{},False{},[Rule{Converge{},Two{}}]) == [ChoicePair{Minor{},Minor{}}] : List<&2,ChoicePair>}
def convergence_does_not_force_outside(): {==}
law convergence_chooses_inside:
  {graph(Pnpm{},False{},[Rule{Converge{},One{}}]) == [ChoicePair{One{},One{}}] : List<&2,ChoicePair>}
def convergence_chooses_inside(): {==}
law set_resolution_installs_outside:
  {step(Yarn{},True{},base(),Request{SetResolution{},[],Two{}}) == StepResult{0n,manual()} : StepResult}
def set_resolution_installs_outside(): {==}
law regeneration_loses_manual_choice:
  {step(Yarn{},True{},InstallState{[ChoicePair{Two{},Two{}}],None{}},Request{Install{},[],Two{}}) == StepResult{0n,base()} : StepResult}
def regeneration_loses_manual_choice(): {==}
law overlapping_ranges_have_no_qualified_winner:
  {values(Pnpm{},True{},[Rule{Broad{},One{}},Rule{Narrow{},Two{}}]) == [One{},Two{}] : List<&2,V>}
def overlapping_ranges_have_no_qualified_winner(): {==}
law proposed_strict_containment_prefers_narrow:
  {candidate_narrowest([Rule{Broad{},One{}},Rule{Narrow{},Two{}}]) == [Two{}] : List<&2,V>}
def proposed_strict_containment_prefers_narrow(): {==}
law proposed_containment_is_order_independent_in_this_pair:
  {candidate_narrowest([Rule{Broad{},One{}},Rule{Narrow{},Two{}}]) == candidate_narrowest([Rule{Narrow{},Two{}},Rule{Broad{},One{}}]) : List<&2,V>}
def proposed_containment_is_order_independent_in_this_pair(): {==}
