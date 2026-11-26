import Base

# Directory traversal and Qt ordering are admitted upstream observations.
# Rows use [id,leaf_hidden,excluded,missing_at_write,link], each flag 0/1.
def visible(hidden: Nat,excluded: Nat) -> Bool:
  Bool.and(Nat.is_eq(hidden,0n),Nat.is_eq(excluded,0n))
def selected(entries: List<&2,List<&2,Nat>>) -> String:
  match entries:
    case Nil{}: ""
    case Con{head,+rest}:
      match head:
        case Con{id,t1}:
          match t1:
            case Con{hidden,t2}:
              match t2:
                case Con{excluded,t3}:
                  Bool.pick(String,visible(hidden,excluded),Nat.show(id) ++ ",","") ++ selected(rest)
                case Nil{}: "unsupported"
            case Nil{}: "unsupported"
        case Nil{}: "unsupported"
def write_state(entries: List<&2,List<&2,Nat>>) -> Nat:
  match entries:
    case Nil{}: 2n
    case Con{head,+rest}:
      match head:
        case Con{id,t1}:
          match t1:
            case Con{hidden,t2}:
              match t2:
                case Con{excluded,t3}:
                  match t3:
                    case Con{missing,t4}:
                      Bool.pick(Nat,visible(hidden,excluded),Bool.pick(Nat,Nat.is_eq(missing,1n),3n,write_state(rest)),write_state(rest))
                    case Nil{}: 9n
                case Nil{}: 9n
            case Nil{}: 9n
        case Nil{}: 9n
def state(root: Bool,directory: Bool,canceled: Bool,has_entries: Bool,has_extra: Bool,entries: List<&2,List<&2,Nat>>) -> Nat:
  Bool.pick(Nat,root,Bool.pick(Nat,directory,1n,Bool.pick(Nat,Bool.and(canceled,Bool.or(has_entries,has_extra)),4n,write_state(entries))),0n)
def error_present(+s: Nat) -> Bool:
  Bool.or(Nat.is_eq(s,1n),Nat.is_eq(s,3n))
def output_replaced(root: Bool,directory: Bool) -> Bool:
  Bool.and(root,Bool.not(directory))
def completed(s: Nat,canceled: Bool) -> Bool:
  Bool.and(Bool.not(canceled),Nat.is_eq(s,2n))
def retained_link(link: Bool,follow: Bool) -> Bool:
  Bool.and(Bool.not(follow),link)
# Same pure decision is a proposed publication policy, not executed staging.
def proposed_publish(s: Nat,canceled: Bool) -> Bool:
  completed(s,canceled)

law hidden_leaf_omitted:
  for excluded: Nat
  {visible(1n,excluded) == False{} : Bool}
def hidden_leaf_omitted(excluded): {==}
law excluded_omitted:
  for hidden: Bool
  {visible(Bool.pick(Nat,hidden,1n,0n),1n) == False{} : Bool}
def excluded_omitted(hidden):
  match hidden:
    case False{}: {==}
    case True{}: {==}
law visible_retained:
  {visible(0n,0n) == True{} : Bool}
def visible_retained(): {==}
law follows_regular:
  for link: Bool
  {retained_link(link,True{}) == False{} : Bool}
def follows_regular(link): {==}
law retains_link:
  {retained_link(True{},False{}) == True{} : Bool}
def retains_link(): {==}
law canceled_no_error:
  {error_present(4n) == False{} : Bool}
def canceled_no_error(): {==}
law read_error:
  {error_present(3n) == True{} : Bool}
def read_error(): {==}
law no_root_no_replacement:
  for directory: Bool
  {output_replaced(False{},directory) == False{} : Bool}
def no_root_no_replacement(directory): {==}
law directory_no_replacement:
  for root: Bool
  {output_replaced(root,True{}) == False{} : Bool}
def directory_no_replacement(root):
  match root:
    case False{}: {==}
    case True{}: {==}
law proposed_canceled_keeps:
  for s: Nat
  {proposed_publish(s,True{}) == False{} : Bool}
def proposed_canceled_keeps(s): {==}
