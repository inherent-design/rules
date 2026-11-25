import Base

type Pack is Data:
  Pack{id: Nat, body: Nat, metadata: Nat, blocks_body: Bool, blocks_metadata: Bool}
type Resource is Data:
  Resource{source: Nat, body: Nat, metadata: Nat}

def choose(pending: Maybe<&2,Nat>, +metadata: Nat, blocks: Bool) -> Maybe<&2,Nat>:
  match pending:
    case Some{n}: Some{n}
    case None{}: Bool.pick(Maybe<&2,Nat>,Bool.not(Nat.is_eq(metadata,0n)),Some{metadata},Bool.pick(Maybe<&2,Nat>,blocks,Some{0n},None{}))
def value(v: Maybe<&2,Nat>) -> Nat:
  match v:
    case None{}: 0n
    case Some{n}: n
def single_high(packs: List<&2,Pack>, pending: Maybe<&2,Nat>) -> Maybe<&2,Resource>:
  match packs:
    case Nil{}: None{}
    case Con{p,rest}:
      match p:
        case Pack{id,+body,metadata,blocks_body,blocks_metadata}:
          +next=choose(pending,metadata,blocks_metadata)
          Bool.pick(Maybe<&2,Resource>,Bool.not(Nat.is_eq(body,0n)),Some{Resource{id,body,value(next)}},Bool.pick(Maybe<&2,Resource>,blocks_body,None{},single_high(rest,next)))
def stack_high(packs: List<&2,Pack>, +blocked: Bool) -> List<&2,Resource>:
  match packs:
    case Nil{}: Nil{}
    case Con{p,rest}:
      match p:
        case Pack{id,+body,metadata,blocks_body,blocks_metadata}:
          +tail=Bool.pick(List<&2,Resource>,blocks_body,Nil{},stack_high(rest,Bool.or(blocked,blocks_metadata)))
          Bool.pick(List<&2,Resource>,Nat.is_eq(body,0n),tail,Con{Resource{id,body,Bool.pick(Nat,blocked,0n,metadata)},tail})
def reverse_packs(xs: List<&2,Pack>, acc: List<&2,Pack>) -> List<&2,Pack>:
  match xs:
    case Nil{}: acc
    case Con{p,ps}: reverse_packs(ps,Con{p,acc})
def reverse_resources(xs: List<&2,Resource>, acc: List<&2,Resource>) -> List<&2,Resource>:
  match xs:
    case Nil{}: acc
    case Con{p,ps}: reverse_resources(ps,Con{p,acc})
def single(packs: List<&2,Pack>, admitted: Bool) -> Maybe<&2,Resource>:
  Bool.pick(Maybe<&2,Resource>,admitted,single_high(reverse_packs(packs,Nil{}),None{}),None{})
def stack(packs: List<&2,Pack>, admitted: Bool) -> List<&2,Resource>:
  Bool.pick(List<&2,Resource>,admitted,reverse_resources(stack_high(reverse_packs(packs,Nil{}),False{}),Nil{}),Nil{})
def low() -> Pack:
  Pack{1n,1n,1n,False{},False{}}
def high() -> Pack:
  Pack{2n,2n,2n,False{},False{}}

law last_pack_wins:
  {single(Con{low(),Con{high(),Nil{}}},True{}) == Some{Resource{2n,2n,2n}} : Maybe<&2,Resource>}
def last_pack_wins():
  {==}
law stack_keeps_own_metadata:
  {stack(Con{low(),Con{Pack{2n,0n,2n,False{},False{}},Nil{}}},True{}) == Con{Resource{1n,1n,1n},Nil{}} : List<&2,Resource>}
def stack_keeps_own_metadata():
  {==}
law single_uses_higher_metadata:
  {single(Con{low(),Con{Pack{2n,0n,2n,False{},False{}},Nil{}}},True{}) == Some{Resource{1n,1n,2n}} : Maybe<&2,Resource>}
def single_uses_higher_metadata():
  {==}
law filter_only_removes_lower_body:
  {single(Con{low(),Con{Pack{2n,0n,0n,True{},False{}},Nil{}}},True{}) == None{} : Maybe<&2,Resource>}
def filter_only_removes_lower_body():
  {==}
law metadata_filter_preserves_file:
  {single(Con{low(),Con{Pack{2n,0n,0n,False{},True{}},Nil{}}},True{}) == Some{Resource{1n,1n,0n}} : Maybe<&2,Resource>}
def metadata_filter_preserves_file():
  {==}
law malformed_metadata_is_selected:
  {single(Con{low(),Con{Pack{2n,0n,3n,False{},False{}},Nil{}}},True{}) == Some{Resource{1n,1n,3n}} : Maybe<&2,Resource>}
def malformed_metadata_is_selected():
  {==}
law sealed_absence_is_preserved:
  {choose(Some{0n},2n,False{}) == Some{0n} : Maybe<&2,Nat>}
def sealed_absence_is_preserved():
  {==}
law invalid_bytes_are_still_bytes:
  {single(Con{low(),Con{Pack{2n,3n,2n,False{},False{}},Nil{}}},True{}) == Some{Resource{2n,3n,2n}} : Maybe<&2,Resource>}
def invalid_bytes_are_still_bytes():
  {==}
