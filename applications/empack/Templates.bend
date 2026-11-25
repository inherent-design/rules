import Base

def address_valid(valid: Maybe<&2, Bool>, explicit: Bool) -> Maybe<&2, Nat>:
  match valid:
    case None{}: None{}
    case Some{accepted}: Bool.pick(Maybe<&2, Nat>, accepted, Some{Bool.pick(Nat,explicit,2n,3n)}, Some{1n})
def address(recognized: Bool, valid: Maybe<&2, Bool>, explicit: Bool) -> Maybe<&2, Nat>:
  Bool.pick(Maybe<&2, Nat>,recognized,address_valid(valid,explicit),Some{0n})
def body(+mode: Nat, utf8: Bool, known: Bool) -> Nat:
  Bool.pick(Nat,Nat.is_eq(mode,0n),0n,
    Bool.pick(Nat,utf8,Bool.pick(Nat,known,1n,3n),Bool.pick(Nat,Nat.is_eq(mode,2n),0n,2n)))
def selected_layer(common: Bool, side: Bool) -> Maybe<&2, Nat>:
  Bool.pick(Maybe<&2, Nat>,side,Some{1n},Bool.pick(Maybe<&2, Nat>,common,Some{0n},None{}))
def gate(fact: Maybe<&2, Bool>, code: Nat, next: Maybe<&2, Nat>) -> Maybe<&2, Nat>:
  match fact:
    case None{}: None{}
    case Some{accepted}: Bool.pick(Maybe<&2, Nat>,accepted,next,Some{code})
def prepare(addresses: Maybe<&2, Bool>, same: Maybe<&2, Bool>, namespace: Maybe<&2, Bool>, bodies: Maybe<&2, Bool>, game: Maybe<&2, Bool>) -> Maybe<&2, Nat>:
  gate(addresses,1n,gate(same,2n,gate(namespace,3n,gate(bodies,4n,gate(game,5n,Some{0n})))))
def show_decision(result: Maybe<&2, Nat>) -> String:
  match result:
    case None{}: "unknown"
    case Some{n}: Nat.show(n)

law ignored_layer_needs_no_path:
  {address(False{},None{},True{}) == Some{0n} : Maybe<&2, Nat>}
def ignored_layer_needs_no_path():
  {==}
law explicit_binary_rejected:
  {body(1n,False{},True{}) == 2n : Nat}
def explicit_binary_rejected():
  {==}
law auto_binary_copied:
  {body(2n,False{},False{}) == 0n : Nat}
def auto_binary_copied():
  {==}
law auto_text_is_not_literal:
  {body(2n,True{},False{}) == 3n : Nat}
def auto_text_is_not_literal():
  {==}
law side_shadows_common:
  for common: Bool
  {selected_layer(common,True{}) == Some{1n} : Maybe<&2, Nat>}
def side_shadows_common(common):
  {==}
law needed_unknown_is_not_success:
  for code: Nat
  for next: Maybe<&2, Nat>
  {gate(None{},code,next) == None{} : Maybe<&2, Nat>}
def needed_unknown_is_not_success(code,next):
  {==}
