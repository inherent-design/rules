import Base

# Finite path/pattern witnesses come from the checked research adapter. This
# models ordered exclusion, traversal and outcome, not Go glob or list parsing.
type IRule is Data:
  IRule{negated: Bool,hits: List<&2,String>}
def bit(value: Bool) -> String:
  Bool.pick(String,value,"1","0")
def contains(paths: List<&2,String>,+path: String) -> Bool:
  match paths:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(String.eq(head,path),contains(tail,path))
def rejected(rules: List<&2,IRule>,+path: String,+prior: Bool) -> Bool:
  match rules:
    case Nil{}: prior
    case Con{IRule{negated,hits},tail}:
      +hit=contains(hits,path)
      next=Bool.pick(Bool,negated,Bool.and(prior,Bool.not(hit)),Bool.or(prior,hit))
      rejected(tail,path,next)
def excluded(groups: List<&2,List<&2,IRule>>,+path: String) -> Bool:
  match groups:
    case Nil{}: False{}
    case Con{rules,tail}: Bool.or(rejected(rules,path,False{}),excluded(tail,path))
def allowed_chain(+groups: List<&2,List<&2,IRule>>,chain: List<&2,String>) -> Bool:
  match chain:
    case Nil{}: True{}
    case Con{head,tail}: Bool.and(Bool.not(excluded(groups,head)),allowed_chain(groups,tail))
def reachable(+groups: List<&2,List<&2,IRule>>,chains: List<&2,List<&2,String>>) -> Bool:
  match chains:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(allowed_chain(groups,head),reachable(groups,tail))
def selected(groups: List<&2,List<&2,IRule>>,explicit_file: Bool,chains: List<&2,List<&2,String>>) -> Bool:
  Bool.or(explicit_file,reachable(groups,chains))
def snapshot(+valid_framing: Bool,has_roots: Bool) -> Bool:
  Bool.and(valid_framing,has_roots)
def exit_code(valid_framing: Bool,has_roots: Bool,missing: Bool) -> Nat:
  Bool.pick(Nat,snapshot(valid_framing,has_roots),Bool.pick(Nat,missing,3n,0n),1n)
def parent_rule() -> IRule:
  IRule{False{},["pruned","pruned/keep.txt"]}
def child_rule() -> IRule:
  IRule{True{},["pruned/keep.txt"]}
def reopen_rule() -> IRule:
  IRule{True{},["pruned","pruned/keep.txt"]}

law explicit_file_bypasses_filter:
  {selected([[parent_rule()]],True{},[["pruned","pruned/keep.txt"]]) == True{} : Bool}
def explicit_file_bypasses_filter(): {==}
law child_negation_does_not_reopen_parent:
  {selected([[parent_rule(),child_rule()]],False{},[["pruned","pruned/keep.txt"]]) == False{} : Bool}
def child_negation_does_not_reopen_parent(): {==}
law reopened_parent_allows_traversal:
  {selected([[parent_rule(),reopen_rule(),child_rule()]],False{},[["pruned","pruned/keep.txt"]]) == True{} : Bool}
def reopened_parent_allows_traversal(): {==}
law explicit_directory_still_filters_child:
  {selected([[parent_rule()]],False{},[["pruned/keep.txt"]]) == False{} : Bool}
def explicit_directory_still_filters_child(): {==}
law order_is_semantic:
  {rejected([child_rule(),parent_rule()],"pruned/keep.txt",False{}) == True{} : Bool}
def order_is_semantic(): {==}
law group_negation_does_not_cross_groups:
  {excluded([[parent_rule()],[child_rule()]],"pruned/keep.txt") == True{} : Bool}
def group_negation_does_not_cross_groups(): {==}
law invalid_framing_refuses:
  {snapshot(False{},True{}) == False{} : Bool}
def invalid_framing_refuses(): {==}
law missing_some_can_publish:
  {exit_code(True{},True{},True{}) == 3n : Nat}
def missing_some_can_publish(): {==}
law no_roots_refuses:
  {exit_code(True{},False{},False{}) == 1n : Nat}
def no_roots_refuses(): {==}
