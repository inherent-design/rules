import Base

type BSCullingSchema is Data:
  BSCullingSchema{condition_declared: Bool,opaque_declared: Bool,opaque_default_annotation: Bool}
type BSRule is Data:
  BSRule{object: Bool,direction: Bool,geometry: Bool,bone: Bool,cube: Bool,face: Bool,condition: Nat,opaque: Nat}
type BSCulling is Data:
  BSCulling{object: Bool,description: Bool,identifier: Bool,rules_array: Bool,rules: List<&2,BSRule>}
def bs_rule(s: BSCullingSchema,r: BSRule) -> Bool:
  match s:
    case BSCullingSchema{c,o,_}:
      match r:
        case BSRule{obj,d,g,b,cube,face,condition,opaque}:
          shape=Bool.and(obj,Bool.and(d,Bool.and(g,Bool.and(b,Bool.and(cube,face)))))
          Bool.and(shape,Bool.and(Bool.or(Bool.not(c),Nat.is_lt(condition,2n)),Bool.or(Bool.not(o),Nat.is_lt(opaque,3n))))
def bs_rules(+s: BSCullingSchema,rules: List<&2,BSRule>) -> Bool:
  match rules:
    case Nil{}: True{}
    case Con{r,rest}: Bool.and(bs_rule(s,r),bs_rules(s,rest))
def bs_culling(s: BSCullingSchema,input: BSCulling) -> Bool:
  match input:
    case BSCulling{obj,d,i,arr,rs}: Bool.and(obj,Bool.and(d,Bool.and(i,Bool.and(arr,bs_rules(s,rs)))))
def bs_biome(obj: Bool,required_string: Bool) -> Bool:
  Bool.and(obj,required_string)

law bs_empty_list:
  {bs_culling(BSCullingSchema{True{},True{},False{}},BSCulling{True{},True{},True{},True{},Nil{}}) == True{} : Bool}
def bs_empty_list():
  {==}
law bs_known_condition:
  {bs_rule(BSCullingSchema{True{},True{},False{}},BSRule{True{},True{},True{},True{},True{},True{},2n,0n}) == False{} : Bool}
def bs_known_condition():
  {==}
law bs_undeclared_condition:
  {bs_rule(BSCullingSchema{False{},False{},False{}},BSRule{True{},True{},True{},True{},True{},True{},2n,0n}) == True{} : Bool}
def bs_undeclared_condition():
  {==}
law bs_known_opaque:
  {bs_rule(BSCullingSchema{True{},True{},False{}},BSRule{True{},True{},True{},True{},True{},True{},0n,3n}) == False{} : Bool}
def bs_known_opaque():
  {==}
law bs_undeclared_opaque:
  {bs_rule(BSCullingSchema{False{},False{},False{}},BSRule{True{},True{},True{},True{},True{},True{},0n,3n}) == True{} : Bool}
def bs_undeclared_opaque():
  {==}
law bs_default_not_assertion:
  {bs_rule(BSCullingSchema{True{},True{},True{}},BSRule{True{},True{},True{},True{},True{},True{},0n,0n}) == bs_rule(BSCullingSchema{True{},True{},False{}},BSRule{True{},True{},True{},True{},True{},True{},0n,0n}) : Bool}
def bs_default_not_assertion():
  {==}
law bs_explicit_false:
  {bs_rule(BSCullingSchema{True{},True{},True{}},BSRule{True{},True{},True{},True{},True{},True{},0n,2n}) == True{} : Bool}
def bs_explicit_false():
  {==}
law bs_missing_bone:
  {bs_rule(BSCullingSchema{True{},True{},False{}},BSRule{True{},True{},True{},False{},True{},True{},0n,0n}) == False{} : Bool}
def bs_missing_bone():
  {==}
law bs_biome_string:
  {bs_biome(True{},True{}) == True{} : Bool}
def bs_biome_string():
  {==}
law bs_biome_missing:
  {bs_biome(True{},False{}) == False{} : Bool}
def bs_biome_missing():
  {==}
