import Base

# Interpreted matching addresses and completed/incomplete scan boundary only.
def member(values: List<&2, Nat>,+needle: Nat) -> Bool:
  match values:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(head,needle),member(tail,needle))
def unique_count(values: List<&2, Nat>) -> Nat:
  match values:
    case Nil{}: 0n
    case Con{head,+tail}: Nat.add(Bool.pick(Nat,member(tail,head),0n,1n),unique_count(tail))
def count_decision(+count: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(count,0n),0n,Bool.pick(Nat,Nat.is_eq(count,1n),3n,1n))
def decision(entries: Nat,limit: Nat,matching: List<&2, Nat>,explicit: Bool,matches: Bool) -> Nat:
  Bool.pick(Nat,explicit,Bool.pick(Nat,matches,3n,4n),
    Bool.pick(Nat,Nat.is_lt(limit,entries),2n,
      count_decision(unique_count(matching))))
def published(kind: Nat) -> Bool:
  Nat.is_eq(kind,3n)
def selected_if(ok: Bool,explicit: Maybe<&2, Nat>,values: List<&2, Nat>) -> Maybe<&2, Nat>:
  match ok:
    case False{}: None{}
    case True{}:
      match explicit:
        case Some{n}: Some{n}
        case None{}:
          match values:
            case Nil{}: None{}
            case Con{head,tail}: Some{head}
def selected(kind: Nat,values: List<&2, Nat>,explicit: Maybe<&2, Nat>) -> Maybe<&2, Nat>:
  selected_if(Nat.is_eq(kind,3n),explicit,values)
def show_selected(value: Maybe<&2, Nat>) -> String:
  match value:
    case None{}: "none"
    case Some{n}: Nat.show(n)

law missing_count:
  {count_decision(0n) == 0n : Nat}
def missing_count(): {==}
law unique_count_selects:
  {count_decision(1n) == 3n : Nat}
def unique_count_selects(): {==}
law duplicate_bytes_collapse:
  {unique_count([0n,0n]) == 1n : Nat}
def duplicate_bytes_collapse(): {==}
law different_matching_bytes_ambiguous:
  {decision(2n,10000n,[0n,1n],False{},False{}) == 1n : Nat}
def different_matching_bytes_ambiguous(): {==}
law incomplete_scan_refuses:
  {decision(10001n,10000n,[0n],False{},False{}) == 2n : Nat}
def incomplete_scan_refuses(): {==}
law explicit_matching_choice:
  for entries: Nat
  for limit: Nat
  for matching: List<&2, Nat>
  {decision(entries,limit,matching,True{},True{}) == 3n : Nat}
def explicit_matching_choice(entries,limit,matching): {==}
law explicit_mismatch_refuses:
  for entries: Nat
  for limit: Nat
  for matching: List<&2, Nat>
  {decision(entries,limit,matching,True{},False{}) == 4n : Nat}
def explicit_mismatch_refuses(entries,limit,matching): {==}
