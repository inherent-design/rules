import Base

# Only the admitted inner quoted payload; no complete shell or Prism parser.
def wrapper_program(values: List<&2,Nat>) -> List<&2,Nat>:
  match values:
    case Nil{}: []
    case Con{+head,tail}:
      match tail:
        case Nil{}:
          Bool.pick(List<&2,Nat>,Nat.is_eq(head,92n),[],[head])
        case Con{+next,+rest}:
          Bool.pick(List<&2,Nat>,Nat.is_eq(head,92n),Con{next,wrapper_program(rest)},Con{head,wrapper_program(Con{next,rest})})
def program(wrapper: Bool,+values: List<&2,Nat>) -> List<&2,Nat>:
  Bool.pick(List<&2,Nat>,wrapper,wrapper_program(values),values)
def escape_backslashes(values: List<&2,Nat>) -> List<&2,Nat>:
  match values:
    case Nil{}: []
    case Con{+head,+tail}:
      Bool.pick(List<&2,Nat>,Nat.is_eq(head,92n),Con{92n,Con{92n,escape_backslashes(tail)}},Con{head,escape_backslashes(tail)})
def show_units(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: Nat.show(head) ++ "," ++ show_units(tail)

law prepare_identity:
  for +values: List<&2,Nat>
  {program(False{},values) == values : List<&2,Nat>}
def prepare_identity(values): {==}
law empty_payload:
  {wrapper_program([]) == [] : List<&2,Nat>}
def empty_payload(): {==}
law native_backslash_lost:
  {wrapper_program([67n,58n,92n,74n]) == [67n,58n,74n] : List<&2,Nat>}
def native_backslash_lost(): {==}
law doubled_backslash_literal:
  {wrapper_program([67n,58n,92n,92n,74n]) == [67n,58n,92n,74n] : List<&2,Nat>}
def doubled_backslash_literal(): {==}
law forward_slash_kept:
  {wrapper_program([67n,58n,47n,74n]) == [67n,58n,47n,74n] : List<&2,Nat>}
def forward_slash_kept(): {==}
law escaped_control_roundtrip:
  {wrapper_program(escape_backslashes([67n,58n,92n,74n])) == [67n,58n,92n,74n] : List<&2,Nat>}
def escaped_control_roundtrip(): {==}
