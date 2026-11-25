import Base

# Unicode scalar lists, not Java UTF-16 array indexes or a property grammar.
type BlockAtom is Data:
  Atom{value: List<&2,U32>,negated: Bool}
type AtomResult is Data:
  Refused{}
  Accepted{atom: BlockAtom}

def atom_construct(value: List<&2,U32>,negated: Bool) -> AtomResult:
  match value:
    case Nil{}: Refused{}
    case head <> tail: Accepted{Atom{head <> tail,negated}}
def atom_parse(value: List<&2,U32>) -> AtomResult:
  match value:
    case Nil{}: Refused{}
    case +head <> +tail:
      Bool.pick(AtomResult,U32.is_eq(head,33),atom_construct(tail,True{}),Accepted{Atom{head <> tail,False{}}})
def atom_encode(atom: BlockAtom) -> List<&2,U32>:
  match atom:
    case Atom{+value,negated}: Bool.pick(List<&2,U32>,negated,33 <> value,value)
def atom_roundtrip(atom: BlockAtom) -> AtomResult:
  atom_parse(atom_encode(atom))

law empty_parse_refuses:
  {atom_parse([]) == Refused{} : AtomResult}
def empty_parse_refuses():
  {==}
law lone_bang_refuses:
  {atom_parse([33]) == Refused{} : AtomResult}
def lone_bang_refuses():
  {==}
law empty_flagged_constructor_refuses:
  {atom_construct([],True{}) == Refused{} : AtomResult}
def empty_flagged_constructor_refuses():
  {==}
law one_bang_only:
  {atom_parse([33,33,97]) == Accepted{Atom{[33,97],True{}}} : AtomResult}
def one_bang_only():
  {==}
law separator_literal:
  {atom_parse([97,124,98]) == Accepted{Atom{[97,124,98],False{}}} : AtomResult}
def separator_literal():
  {==}
law whitespace_literal:
  {atom_parse([32,33,97]) == Accepted{Atom{[32,33,97],False{}}} : AtomResult}
def whitespace_literal():
  {==}
law fullwidth_bang_literal:
  {atom_parse([65281,97]) == Accepted{Atom{[65281,97],False{}}} : AtomResult}
def fullwidth_bang_literal():
  {==}
law supplementary_scalar_preserved:
  {atom_parse([33,129302]) == Accepted{Atom{[129302],True{}}} : AtomResult}
def supplementary_scalar_preserved():
  {==}
law decoded_image_roundtrip_example:
  {atom_roundtrip(Atom{[33,97],True{}}) == Accepted{Atom{[33,97],True{}}} : AtomResult}
def decoded_image_roundtrip_example():
  {==}
law unflagged_direct_constructor_can_fail_reparse:
  {atom_roundtrip(Atom{[33],False{}}) == Refused{} : AtomResult}
def unflagged_direct_constructor_can_fail_reparse():
  {==}
law unflagged_direct_constructor_can_change:
  {atom_roundtrip(Atom{[33,97],False{}}) == Accepted{Atom{[97],True{}}} : AtomResult}
def unflagged_direct_constructor_can_change():
  {==}
