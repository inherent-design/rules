import Base

def rename_text(current: String,requested: String,role: Bool) -> String:
  Bool.pick(String,role,"1|" ++ requested,"0|" ++ current)
def key(present: Bool,alias: Bool,candidate: Bool) -> Nat:
  Bool.pick(Nat,Bool.or(candidate,Bool.or(present,Bool.not(alias))),0n,1n)
def group_text(present: Bool,alias: Bool,candidate: Bool) -> String:
  Bool.pick(String,Nat.is_eq(key(present,alias,candidate),0n),"0|1|1","1|0|0")
type I is Data:
  I{owner: Nat,directory: Nat,uuid: Nat}
def matches(i: I,+mode: Nat,+query: Nat) -> Bool:
  match i:
    case I{_,+d,+u}: Bool.pick(Bool,Nat.is_eq(mode,1n),Nat.is_eq(d,query),Bool.pick(Bool,Nat.is_eq(mode,2n),Nat.is_eq(u,query),Bool.or(Nat.is_eq(d,query),Nat.is_eq(u,query))))
def first(xs: List<&2,I>,+mode: Nat,+query: Nat) -> Nat:
  match xs:
    case Nil{}: 0n
    case Con{+i,rest}:
      match i:
        case I{owner,_,_}: Bool.pick(Nat,matches(i,mode,query),owner,first(rest,mode,query))
def unique_acc(xs: List<&2,I>,+mode: Nat,+query: Nat,+found: Nat) -> Nat:
  match xs:
    case Nil{}: found
    case Con{+i,rest}:
      match i:
        case I{owner,_,_}:
          next=Bool.pick(Nat,matches(i,mode,query),Bool.pick(Nat,Nat.is_eq(found,0n),owner,3n),found)
          unique_acc(rest,mode,query,next)
def remove_text(trash: Bool,success: Bool) -> String:
  "0|" ++ Bool.pick(String,Bool.and(trash,success),"1","0")
def undo_text(+has: Bool,+main: Bool,shortcuts: Bool) -> String:
  Bool.pick(String,Bool.or(Bool.not(has),Bool.and(main,shortcuts)),"1","0") ++ "|" ++ Bool.pick(String,Bool.and(has,main),"1","0") ++ "|0"
type R is Data:
  R{main_pending: Bool,shortcuts: Nat}
def advance(+s: R,main: Bool,shortcuts: Bool) -> R:
  match s:
    case R{pending,n}: Bool.pick(R,Bool.and(pending,Bool.not(main)),s,R{False{},Bool.pick(Nat,shortcuts,0n,n)})
def retry_text(s: R) -> String:
  match s:
    case R{+main,+n}: Bool.pick(String,main,"1","0") ++ "|" ++ Nat.show(n) ++ "|" ++ Bool.pick(String,Bool.and(Bool.not(main),Nat.is_eq(n,0n)),"1","0")
def save_text(probed: Bool,good: Bool) -> String:
  Bool.pick(String,probed,Bool.pick(String,good,"saved|1","failed|0"),"skipped|0")
def contains(xs: List<&2,Nat>,+key: Nat) -> Bool:
  match xs:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,key),contains(tail,key))
def length(xs: List<&2,Nat>) -> Nat:
  match xs:
    case Nil{}: 0n
    case Con{_,tail}: 1n+length(tail)
def distinct(xs: List<&2,Nat>) -> List<&2,Nat>:
  match xs:
    case Nil{}: Nil{}
    case Con{+head,+tail}: Bool.pick(List<&2,Nat>,contains(tail,head),distinct(tail),Con{head,distinct(tail)})
def filter(xs: List<&2,Nat>,+known: List<&2,Nat>) -> List<&2,Nat>:
  match xs:
    case Nil{}: Nil{}
    case Con{+head,+tail}: Bool.pick(List<&2,Nat>,contains(known,head),Con{head,filter(tail,known)},filter(tail,known))
def counts_text(+members: List<&2,Nat>,known: List<&2,Nat>) -> String:
  Nat.show(length(members)) ++ "|" ++ Nat.show(length(distinct(members))) ++ "|" ++ Nat.show(length(distinct(filter(members,known))))
def discovered(config: Bool,internal: Bool) -> Bool:
  Bool.and(Bool.not(internal),config)

law other_role_cannot_rename:
  {rename_text("a","b",False{}) == "0|a" : String}
def other_role_cannot_rename(): {==}
law first_uuid_assignment_uses_alias:
  {group_text(False{},True{},False{}) == "1|0|0" : String}
def first_uuid_assignment_uses_alias(): {==}
law candidate_uses_directory:
  for present: Bool
  for alias: Bool
  {key(present,alias,True{}) == 0n : Nat}
def candidate_uses_directory(present,alias): {==}
law first_match_can_choose_uuid_before_directory:
  {first([I{1n,0n,2n},I{2n,2n,3n}],0n,2n) == 1n : Nat}
def first_match_can_choose_uuid_before_directory(): {==}
law typed_directory_selects_second_owner:
  {unique_acc([I{1n,0n,2n},I{2n,2n,3n}],1n,2n,0n) == 2n : Nat}
def typed_directory_selects_second_owner(): {==}
law failed_trash_still_removes_group:
  {remove_text(True{},False{}) == "0|0" : String}
def failed_trash_still_removes_group(): {==}
law failed_restore_loses_current_history:
  {undo_text(True{},False{},True{}) == "0|0|0" : String}
def failed_restore_loses_current_history(): {==}
law no_history_is_success_without_work:
  {undo_text(False{},False{},False{}) == "1|0|0" : String}
def no_history_is_success_without_work(): {==}
law partial_shortcut_keeps_reference:
  {retry_text(advance(R{True{},1n},True{},False{})) == "0|1|0" : String}
def partial_shortcut_keeps_reference(): {==}
law retry_does_not_repeat_main:
  {retry_text(advance(R{False{},1n},False{},True{})) == "0|0|1" : String}
def retry_does_not_repeat_main(): {==}
law duplicate_members_count_but_save_once:
  {counts_text([1n,1n],[1n,2n]) == "2|1|1" : String}
def duplicate_members_count_but_save_once(): {==}
law sibling_alias_is_not_discovered:
  for config: Bool
  {discovered(config,True{}) == False{} : Bool}
def sibling_alias_is_not_discovered(config): {==}
