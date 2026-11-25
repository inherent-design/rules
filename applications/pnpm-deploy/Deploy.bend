import Base

type RootDependency is Data:
  Root{target: Nat, group: Nat}
type Arc is Data:
  Edge{owner: Nat, target: Nat}
def enabled(+group: Nat, production: Bool, optional: Bool) -> Bool:
  Bool.pick(Bool,Nat.is_eq(group,0n),True{},Bool.pick(Bool,Nat.is_eq(group,1n),optional,Bool.not(production)))
def keep_root(keep: Bool, target: Nat, +tail: List<&2, Nat>) -> List<&2, Nat>:
  Bool.pick(List<&2, Nat>,keep,target<>tail,tail)
def roots(deps: List<&2, RootDependency>, +production: Bool, +optional: Bool) -> List<&2, Nat>:
  match deps:
    case Nil{}: []
    case Con{head,tail}:
      match head:
        case Root{target,group}: keep_root(enabled(group,production,optional),target,roots(tail,production,optional))
def member(values: List<&2, Nat>, +value: Nat) -> Bool:
  match values:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,value),member(tail,value))
def incoming(edges: List<&2, Arc>, +reached: List<&2, Nat>, +node: Nat) -> Bool:
  match edges:
    case Nil{}: False{}
    case Con{head,tail}:
      match head:
        case Edge{owner,target}: Bool.or(Bool.and(Nat.is_eq(target,node),member(reached,owner)),incoming(tail,reached,node))
def select_nodes(universe: List<&2, Nat>, +reached: List<&2, Nat>, +edges: List<&2, Arc>) -> List<&2, Nat>:
  match universe:
    case Nil{}: []
    case Con{+head,tail}: keep_root(Bool.or(member(reached,head),incoming(edges,reached,head)),head,select_nodes(tail,reached,edges))
def direct_nodes(universe: List<&2, Nat>, +selected: List<&2, Nat>) -> List<&2, Nat>:
  match universe:
    case Nil{}: []
    case Con{+head,tail}: keep_root(member(selected,head),head,direct_nodes(tail,selected))
def iterate(fuel: Nat, +universe: List<&2, Nat>, +edges: List<&2, Arc>, reached: List<&2, Nat>) -> List<&2, Nat>:
  match fuel:
    case Zero{}: reached
    case Succ{rest}: iterate(rest,universe,edges,select_nodes(universe,reached,edges))
def admission(+selected: Nat, unsafe: Bool, +force: Bool, inside: Bool, link: Bool, occupied: Bool) -> Nat:
  Bool.pick(Nat,Nat.is_eq(selected,0n),1n,Bool.pick(Nat,Nat.is_lt(1n,selected),2n,
    Bool.pick(Nat,Bool.or(Bool.or(unsafe,Bool.and(force,Bool.not(inside))),link),3n,
      Bool.pick(Nat,Bool.and(occupied,Bool.not(force)),4n,0n))))
type Outcome is Data:
  Result{code: Nat, payload_copied: Bool, prior_removed: Bool, command_succeeded: Bool, source_preserved: Bool}
def prepared_source(removed: Bool, +preserved: Bool, +available: Bool) -> Outcome:
  Result{Bool.pick(Nat,available,0n,5n),preserved,removed,available,preserved}
def prepared_result(+removed: Bool, alias: Bool, available: Bool) -> Outcome:
  prepared_source(removed,Bool.not(Bool.and(alias,removed)),available)
def prepared_available(available: Maybe<&2, Bool>, force: Bool, occupied: Bool, alias: Bool) -> Maybe<&2, Outcome>:
  match available:
    case None{}: None{}
    case Some{value}: Some{prepared_result(Bool.and(force,occupied),alias,value)}
def finish(+admitted: Nat, force: Bool, occupied: Bool, alias: Bool, available: Maybe<&2, Bool>) -> Maybe<&2, Outcome>:
  Bool.pick(Maybe<&2, Outcome>,Nat.is_eq(admitted,0n),prepared_available(available,force,occupied,alias),Some{Result{admitted,False{},False{},False{},True{}}})
def physical_admission(physical: Maybe<&2, Bool>) -> Maybe<&2, Nat>:
  match physical:
    case None{}: None{}
    case Some{conflict}: Some{Bool.pick(Nat,conflict,3n,0n)}
def proposed_admission(physical: Maybe<&2, Bool>, +current: Nat) -> Maybe<&2, Nat>:
  Bool.pick(Maybe<&2, Nat>,Nat.is_eq(current,0n),physical_admission(physical),Some{current})
def show_list(values: List<&2, Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: Nat.show(head) ++ "," ++ show_list(tail)
def usable(result: Maybe<&2, Outcome>) -> Bool:
  match result:
    case None{}: False{}
    case Some{out}:
      match out:
        case Result{code,copied,removed,success,preserved}: Bool.and(copied,success)
def runtime_direct(result: Maybe<&2, Outcome>, universe: List<&2, Nat>, selected: List<&2, Nat>) -> List<&2, Nat>:
  Bool.pick(List<&2, Nat>,usable(result),direct_nodes(universe,selected),[])
def runtime_closure(result: Maybe<&2, Outcome>, count: Nat, universe: List<&2, Nat>, edges: List<&2, Arc>, selected: List<&2, Nat>) -> List<&2, Nat>:
  Bool.pick(List<&2, Nat>,usable(result),iterate(count,universe,edges,0n<>selected),[])
def show_result(result: Outcome) -> String:
  match result:
    case Result{code,copied,removed,success,preserved}: Nat.show(code) ++ ":" ++ Bool.show(copied) ++ ":" ++ Bool.show(removed) ++ ":" ++ Bool.show(success) ++ ":" ++ Bool.show(preserved)
def show_outcome(result: Maybe<&2, Outcome>) -> String:
  match result:
    case None{}: "unknown"
    case Some{out}: show_result(out)

law production_excludes_development:
  for optional: Bool
  {enabled(2n,True{},optional) == False{} : Bool}
def production_excludes_development(optional):
  {==}
law optional_exclusion_is_separate:
  for production: Bool
  {enabled(1n,production,False{}) == False{} : Bool}
def optional_exclusion_is_separate(production):
  {==}
law force_outside_is_not_permission:
  {admission(1n,False{},True{},False{},False{},True{}) == 3n : Nat}
def force_outside_is_not_permission():
  {==}
law occupied_requires_force:
  {admission(1n,False{},False{},True{},False{},True{}) == 4n : Nat}
def occupied_requires_force():
  {==}
law blocked_before_copy:
  for force: Bool
  for occupied: Bool
  for alias: Bool
  for available: Maybe<&2, Bool>
  {finish(3n,force,occupied,alias,available) == Some{Result{3n,False{},False{},False{},True{}}} : Maybe<&2, Outcome>}
def blocked_before_copy(force,occupied,alias,available):
  {==}
law later_failure_keeps_partial_effects:
  {finish(0n,True{},True{},False{},Some{False{}}) == Some{Result{5n,True{},True{},False{},True{}}} : Maybe<&2, Outcome>}
def later_failure_keeps_partial_effects():
  {==}
law lexical_admission_is_not_source_protection:
  {finish(0n,True{},True{},True{},Some{True{}}) == Some{Result{0n,False{},True{},True{},False{}}} : Maybe<&2, Outcome>}
def lexical_admission_is_not_source_protection():
  {==}
law unknown_physical_relation_is_not_distinct:
  {proposed_admission(None{},0n) == None{} : Maybe<&2, Nat>}
def unknown_physical_relation_is_not_distinct():
  {==}
law known_refusal_needs_no_physical_observation:
  {proposed_admission(None{},3n) == Some{3n} : Maybe<&2, Nat>}
def known_refusal_needs_no_physical_observation():
  {==}
