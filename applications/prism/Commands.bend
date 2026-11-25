import Base

# Observed parsed-token lists are premises; this does not implement either parser.
def empty(values: List<&2, Nat>) -> Bool:
  match values:
    case Nil{}: True{}
    case Con{head,tail}: False{}
def disposition(mode: Nat,nonempty: Bool,trimmed_empty: Bool,+tokens: List<&2, Nat>,exists: Bool) -> Nat:
  Bool.pick(Nat,Nat.is_eq(mode,2n),
      Bool.pick(Nat,trimmed_empty,2n,Bool.pick(Nat,empty(tokens),5n,Bool.pick(Nat,exists,3n,4n))),
      Bool.pick(Nat,nonempty,Bool.pick(Nat,empty(tokens),5n,1n),0n))
def attempts_start(+kind: Nat) -> Bool:
  Bool.or(Bool.or(Nat.is_eq(kind,1n),Nat.is_eq(kind,2n)),Nat.is_eq(kind,3n))
def terminal(+kind: Nat) -> Bool:
  Bool.or(attempts_start(kind),Nat.is_eq(kind,4n))
def successful(kind: Nat,result: Nat) -> Bool:
  Bool.and(attempts_start(kind),Nat.is_eq(result,0n))
def child(kind: Nat,result: Nat) -> Bool:
  Bool.and(attempts_start(kind),Bool.not(Nat.is_eq(result,2n)))
def abort_accepted(kind: Nat,requested: Bool) -> Bool:
  Bool.and(Nat.is_eq(kind,1n),requested)
def guarded(+kind: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(kind,5n),4n,kind)
def tail(values: List<&2, Nat>) -> List<&2, Nat>:
  match values:
    case Nil{}: []
    case Con{head,rest}: rest
def append(values: List<&2, Nat>,suffix: List<&2, Nat>) -> List<&2, Nat>:
  match values:
    case Nil{}: suffix
    case Con{head,rest}: Con{head,append(rest,suffix)}
def child_args(+kind: Nat,result: Nat,+tokens: List<&2, Nat>,+game: List<&2, Nat>) -> List<&2, Nat>:
  Bool.pick(List<&2,Nat>,child(kind,result),
    Bool.pick(List<&2,Nat>,Nat.is_eq(kind,1n),tail(tokens),
      Bool.pick(List<&2,Nat>,Nat.is_eq(kind,2n),game,append(tail(tokens),Con{0n,game}))),[])
def show_args(values: List<&2, Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,rest}: Nat.show(head) ++ "," ++ show_args(rest)

law whitespace_wrapper_direct:
  for nonempty: Bool
  for tokens: List<&2, Nat>
  for exists: Bool
  {disposition(2n,nonempty,True{},tokens,exists) == 2n : Nat}
def whitespace_wrapper_direct(nonempty,tokens,exists): {==}
law expanded_empty_unmet:
  for nonempty: Bool
  for exists: Bool
  {disposition(2n,nonempty,False{},[],exists) == 5n : Nat}
def expanded_empty_unmet(nonempty,exists): {==}
law hook_empty_tokens_unmet:
  for trimmed_empty: Bool
  for exists: Bool
  {disposition(0n,True{},trimmed_empty,[],exists) == 5n : Nat}
def hook_empty_tokens_unmet(trimmed_empty,exists): {==}
law refusal_not_success:
  for result: Nat
  {successful(4n,result) == False{} : Bool}
def refusal_not_success(result): {==}
law refusal_no_start_attempt:
  {attempts_start(4n) == False{} : Bool}
def refusal_no_start_attempt(): {==}
law guard_unmet:
  {guarded(5n) == 4n : Nat}
def guard_unmet(): {==}
law wrapper_keeps_invocation:
  {child_args(3n,0n,[0n,7n,8n],[1n,2n,9n,4n]) == [7n,8n,0n,1n,2n,9n,4n] : List<&2,Nat>}
def wrapper_keeps_invocation(): {==}
