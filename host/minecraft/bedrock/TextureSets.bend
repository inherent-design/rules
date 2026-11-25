import Base

type TSInput is Data:
  TSInput{color: Bool,normal: Bool,height: Bool,mer: Bool,mers: Bool,backing: Nat,vibrant: Bool,texture_object: Bool,variation: Bool}
def ts_bit(b: Bool,n: Nat) -> Nat:
  Bool.pick(Nat,b,n,0n)
def ts_issues(i: TSInput) -> Nat:
  match i:
    case TSInput{c,n,+h,mer,+mers,+back,+vv,obj,variation}:
      a=Nat.add(ts_bit(Bool.not(c),1n),ts_bit(Bool.and(n,h),2n))
      b=Nat.add(ts_bit(Bool.and(mer,mers),4n),ts_bit(Nat.is_eq(back,1n),8n))
      d=Nat.add(ts_bit(Nat.is_eq(back,2n),16n),ts_bit(Bool.and(vv,Bool.and(obj,h)),32n))
      Nat.add(Nat.add(a,b),Nat.add(d,ts_bit(Bool.and(vv,Bool.and(mers,variation)),64n)))
def ts_channels(+layer: Nat,image: Bool,+count: Nat) -> Bool:
  match image:
    case True{}:
      Bool.pick(Bool,Nat.is_eq(layer,2n),Nat.is_eq(count,1n),Bool.pick(Bool,Nat.is_eq(layer,4n),Nat.is_eq(count,4n),Bool.and(Bool.or(Nat.is_eq(layer,0n),Bool.or(Nat.is_eq(layer,1n),Nat.is_eq(layer,3n))),Bool.or(Nat.is_eq(count,3n),Nat.is_eq(count,4n)))))
    case False{}:
      Bool.or(Bool.and(Nat.is_eq(layer,0n),Nat.is_eq(count,4n)),Bool.or(Bool.and(Nat.is_eq(layer,2n),Nat.is_eq(count,1n)),Bool.or(Bool.and(Nat.is_eq(layer,3n),Nat.is_eq(count,3n)),Bool.and(Nat.is_eq(layer,4n),Nat.is_eq(count,4n)))))
type TSImage is Data:
  TSImage{pack: Nat,name: Nat,extension: Nat,content_token: Nat}
def ts_at(+pack: Nat,+name: Nat,+ext: Nat,images: List<&2,TSImage>) -> Maybe<&2,Nat>:
  match images:
    case Nil{}: None{}
    case Con{TSImage{p,n,e,b},rest}:
      Bool.pick(Maybe<&2,Nat>,Bool.and(Nat.is_eq(pack,p),Bool.and(Nat.is_eq(name,n),Nat.is_eq(ext,e))),Some{b},ts_at(pack,name,ext,rest))
def ts_or(a: Maybe<&2,Nat>,b: Maybe<&2,Nat>) -> Maybe<&2,Nat>:
  match a:
    case None{}: b
    case Some{n}: Some{n}
def ts_resolve(+pack: Nat,+name: Nat,+images: List<&2,TSImage>) -> Maybe<&2,Nat>:
  ts_or(ts_at(pack,name,0n,images),ts_or(ts_at(pack,name,1n,images),ts_or(ts_at(pack,name,2n,images),ts_at(pack,name,3n,images))))
type TSDefinition is Data:
  TSDefinition{name: Nat,pack: Nat,layers: Nat}
def ts_select(+name: Nat,definitions: List<&2,TSDefinition>) -> Maybe<&2,TSDefinition>:
  match definitions:
    case Nil{}: None{}
    case Con{TSDefinition{+n,p,l},rest}: Bool.pick(Maybe<&2,TSDefinition>,Nat.is_eq(name,n),Some{TSDefinition{n,p,l}},ts_select(name,rest))
type TSDeclaration is Data:
  TSDeclaration{pbr_authoring: Bool,raytraced_alternative: Bool}
def ts_declares(pbr: Bool,rtx: Bool,+major: Nat,+minor: Nat,patch: Nat) -> TSDeclaration:
  floor=Bool.or(Nat.is_gt(major,1n),Bool.and(Nat.is_eq(major,1n),Bool.or(Nat.is_gt(minor,21n),Bool.and(Nat.is_eq(minor,21n),Bool.not(Nat.is_lt(patch,120n))))))
  TSDeclaration{Bool.and(pbr,floor),rtx}
type TSMaterial is Data:
  TSMaterial{metal: Nat,subsurface: Nat}
def ts_predominant(+metal: Nat,+subsurface: Nat) -> TSMaterial:
  Bool.pick(TSMaterial,Nat.is_gt(metal,subsurface),TSMaterial{metal,0n},TSMaterial{0n,subsurface})

law ts_unknown_not_missing:
  {ts_issues(TSInput{True{},False{},False{},False{},False{},2n,False{},False{},False{}}) == 16n : Nat}
def ts_unknown_not_missing():
  {==}
law ts_independent_issues:
  {ts_issues(TSInput{False{},True{},True{},False{},False{},2n,False{},False{},False{}}) == 19n : Nat}
def ts_independent_issues():
  {==}
law ts_object_height:
  {ts_issues(TSInput{True{},False{},True{},False{},False{},0n,True{},True{},False{}}) == 32n : Nat}
def ts_object_height():
  {==}
law ts_mers_variation:
  {ts_issues(TSInput{True{},False{},False{},False{},True{},0n,True{},False{},True{}}) == 64n : Nat}
def ts_mers_variation():
  {==}
law ts_color_image:
  {ts_channels(0n,True{},3n) == True{} : Bool}
def ts_color_image():
  {==}
law ts_color_uniform:
  {ts_channels(0n,False{},3n) == False{} : Bool}
def ts_color_uniform():
  {==}
law ts_foreign_not_backing:
  {ts_resolve(1n,9n,Con{TSImage{2n,9n,0n,123n},Nil{}}) == None{} : Maybe<&2,Nat>}
def ts_foreign_not_backing():
  {==}
law ts_no_merge:
  {ts_select(9n,Con{TSDefinition{9n,2n,1n},Con{TSDefinition{9n,1n,14n},Nil{}}}) == Some{TSDefinition{9n,2n,1n}} : Maybe<&2,TSDefinition>}
def ts_no_merge():
  {==}
law ts_floor:
  {ts_declares(True{},False{},1n,21n,119n) == TSDeclaration{False{},False{}} : TSDeclaration}
def ts_floor():
  {==}
law ts_raytraced:
  {ts_declares(False{},True{},1n,16n,100n) == TSDeclaration{False{},True{}} : TSDeclaration}
def ts_raytraced():
  {==}
law ts_tie:
  {ts_predominant(64n,64n) == TSMaterial{0n,64n} : TSMaterial}
def ts_tie():
  {==}
