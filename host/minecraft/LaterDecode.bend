import Base

type LDNumber is Data:
  LDNumber{negative: Bool,whole: Nat,fraction: Nat}
type LDVersion is Data:
  LDVersion{major: Nat,minor: Nat}
type LDBounds is Data:
  LDBounds{lower: LDVersion,upper: LDVersion}
type LDOldRange is Data:
  LDOldRange{lower: Nat,upper: Nat}
type LDPack is Data:
  LDPack{threshold: Nat,lower: Maybe<&2,LDVersion>,upper: Maybe<&2,LDVersion>,main: Maybe<&2,Nat>,old: Maybe<&2,LDOldRange>}
type LDRotationInput is Data:
  LDRotationInput{present: Bool,origin_valid: Bool,axis_present: Bool,angle_present: Bool,xyz_present: Bool,axis: Nat,angle: Nat,x: Nat,y: Nat,z: Nat,rescale: Bool}
type LDRotation is Data:
  LDRotation{mode: Nat,axis: Nat,angle: Nat,x: Nat,y: Nat,z: Nat,rescale: Bool}

def ld_number(n: LDNumber) -> Maybe<&2,Nat>:
  match n:
    case LDNumber{negative,+whole,_}: Bool.pick(Maybe<&2,Nat>,Bool.and(negative,Bool.not(Nat.is_eq(whole,0n))),None{},Some{whole})
def ld_numbers_step(head: Maybe<&2,Nat>,tail: Maybe<&2,List<&2,Nat>>) -> Maybe<&2,List<&2,Nat>>:
  match head tail:
    case Some{n} Some{rest}: Some{Con{n,rest}}
    case _ _: None{}
def ld_numbers(ns: List<&2,LDNumber>) -> Maybe<&2,List<&2,Nat>>:
  match ns:
    case Nil{}: Some{Nil{}}
    case Con{head,rest}: ld_numbers_step(ld_number(head),ld_numbers(rest))
def ld_first_two(ns: List<&2,Nat>,default_minor: Nat) -> Maybe<&2,LDVersion>:
  match ns:
    case Nil{}: None{}
    case Con{a,Nil{}}: Some{LDVersion{a,default_minor}}
    case Con{a,Con{b,_}}: Some{LDVersion{a,b}}
def ld_format_step(allowed: Bool,top: Bool,values: Maybe<&2,List<&2,Nat>>) -> Maybe<&2,LDVersion>:
  match values:
    case None{}: None{}
    case Some{values}: Bool.pick(Maybe<&2,LDVersion>,allowed,ld_first_two(values,Bool.pick(Nat,top,2147483647n,0n)),None{})
def ld_decode_format(top: Bool,+tokens: List<&2,LDNumber>) -> Maybe<&2,LDVersion>:
  allowed=Bool.and(Bool.not(List.is_empty(&2,LDNumber,tokens)),Bool.not(Nat.is_gt(List.length(&2,LDNumber,tokens),256n)))
  ld_format_step(allowed,top,ld_numbers(tokens))
def ld_version_le(a: LDVersion,b: LDVersion) -> Bool:
  match a b:
    case LDVersion{+a,b} LDVersion{+c,d}: Bool.or(Nat.is_gt(c,a),Bool.and(Nat.is_eq(a,c),Bool.not(Nat.is_gt(b,d))))
def ld_major(v: LDVersion) -> Nat:
  match v:
    case LDVersion{a,_}: a
def ld_valid_main(+main: Nat,lower: Nat,upper: Nat) -> Bool:
  Bool.and(Bool.not(Nat.is_gt(15n,main)),Bool.and(Bool.not(Nat.is_gt(lower,main)),Bool.not(Nat.is_gt(main,upper))))
def ld_optional_main(main: Maybe<&2,Nat>,lower: Nat,upper: Nat) -> Bool:
  match main:
    case None{}: True{}
    case Some{n}: ld_valid_main(n,lower,upper)
def ld_required_main(main: Maybe<&2,Nat>,lower: Nat,upper: Nat) -> Bool:
  match main:
    case None{}: False{}
    case Some{n}: ld_valid_main(n,lower,upper)
def ld_old_present(old: Maybe<&2,LDOldRange>) -> Bool:
  match old:
    case None{}: False{}
    case Some{_}: True{}
def ld_mixed_old_valid(old: Maybe<&2,LDOldRange>,threshold: Nat,lower: Nat,upper: Nat) -> Bool:
  match old:
    case None{}: False{}
    case Some{LDOldRange{a,+b}}: Bool.and(Nat.is_eq(a,lower),Bool.or(Nat.is_eq(b,upper),Nat.is_eq(b,threshold)))
def ld_new_pack(+threshold: Nat,+lower: LDVersion,+upper: LDVersion,+main: Maybe<&2,Nat>,+old: Maybe<&2,LDOldRange>) -> Maybe<&2,LDBounds>:
  modern=Nat.is_gt(ld_major(lower),threshold)
  new_ok=Bool.and(Bool.not(ld_old_present(old)),ld_optional_main(main,ld_major(lower),ld_major(upper)))
  mixed_ok=Bool.and(ld_mixed_old_valid(old,threshold,ld_major(lower),ld_major(upper)),ld_required_main(main,ld_major(lower),ld_major(upper)))
  Bool.pick(Maybe<&2,LDBounds>,Bool.and(ld_version_le(lower,upper),Bool.pick(Bool,modern,new_ok,mixed_ok)),Some{LDBounds{lower,upper}},None{})
def ld_legacy_pack(+threshold: Nat,old: Maybe<&2,LDOldRange>,main: Maybe<&2,Nat>) -> Maybe<&2,LDBounds>:
  match old:
    case Some{LDOldRange{+a,+b}}:
      Bool.pick(Maybe<&2,LDBounds>,Bool.and(Bool.not(Nat.is_gt(b,threshold)),ld_required_main(main,a,b)),Some{LDBounds{LDVersion{a,0n},LDVersion{b,0n}}},None{})
    case None{}:
      match main:
        case None{}: None{}
        case Some{+n}: Bool.pick(Maybe<&2,LDBounds>,Bool.not(Nat.is_gt(n,threshold)),Some{LDBounds{LDVersion{n,0n},LDVersion{n,0n}}},None{})
def ld_decode_pack(p: LDPack) -> Maybe<&2,LDBounds>:
  match p:
    case LDPack{threshold,Some{lower},Some{upper},main,old}: ld_new_pack(threshold,lower,upper,main,old)
    case LDPack{threshold,None{},None{},main,old}: ld_legacy_pack(threshold,old,main)
    case _: None{}
def ld_decode_rotation(r: LDRotationInput) -> Maybe<&2,LDRotation>:
  match r:
    case LDRotationInput{present,origin,+axis_present,+angle_present,xyz_present,+axis,angle,x,y,z,+rescale}:
      scalar_ok=Bool.and(Bool.and(axis_present,angle_present),Bool.and(Bool.not(Nat.is_gt(1n,axis)),Bool.not(Nat.is_gt(axis,3n))))
      scalar=Bool.pick(Maybe<&2,LDRotation>,scalar_ok,Some{LDRotation{2n,axis,angle,0n,0n,0n,rescale}},None{})
      euler=Bool.pick(Maybe<&2,LDRotation>,xyz_present,Some{LDRotation{1n,0n,0n,x,y,z,rescale}},None{})
      chosen=Bool.pick(Maybe<&2,LDRotation>,Bool.or(axis_present,angle_present),scalar,euler)
      Bool.pick(Maybe<&2,LDRotation>,present,Bool.pick(Maybe<&2,LDRotation>,origin,chosen,None{}),Some{LDRotation{0n,0n,0n,0n,0n,0n,False{}}})
def ld_decode_shade(present: Bool,+direction: Nat) -> Maybe<&2,Nat>:
  Bool.pick(Maybe<&2,Nat>,present,Bool.pick(Maybe<&2,Nat>,Bool.and(Bool.not(Nat.is_gt(1n,direction)),Bool.not(Nat.is_gt(direction,6n))),Some{direction},None{}),Some{0n})

law ld_fraction_truncates:
  {ld_number(LDNumber{False{},97n,5n}) == Some{97n} : Maybe<&2,Nat>}
def ld_fraction_truncates():
  {==}
law ld_negative_whole_refuses:
  {ld_number(LDNumber{True{},1n,0n}) == None{} : Maybe<&2,Nat>}
def ld_negative_whole_refuses():
  {==}
law ld_upper_default_preserved:
  {ld_decode_format(True{},Con{LDNumber{False{},97n,0n},Nil{}}) == Some{LDVersion{97n,2147483647n}} : Maybe<&2,LDVersion>}
def ld_upper_default_preserved():
  {==}
law ld_extra_component_not_stored:
  {ld_decode_format(False{},Con{LDNumber{False{},97n,0n},Con{LDNumber{False{},1n,0n},Con{LDNumber{False{},7n,0n},Nil{}}}}) == Some{LDVersion{97n,1n}} : Maybe<&2,LDVersion>}
def ld_extra_component_not_stored():
  {==}
law ld_empty_format_refuses:
  {ld_decode_format(False{},Nil{}) == None{} : Maybe<&2,LDVersion>}
def ld_empty_format_refuses():
  {==}
law ld_resource_threshold:
  {ld_decode_pack(LDPack{64n,None{},None{},Some{65n},None{}}) == None{} : Maybe<&2,LDBounds>}
def ld_resource_threshold():
  {==}
law ld_data_threshold:
  {ld_decode_pack(LDPack{81n,None{},None{},Some{82n},None{}}) == None{} : Maybe<&2,LDBounds>}
def ld_data_threshold():
  {==}
law ld_pair_minor_order:
  {ld_version_le(LDVersion{97n,2n},LDVersion{97n,1n}) == False{} : Bool}
def ld_pair_minor_order():
  {==}
law ld_mixed_representation_scalar:
  {ld_decode_rotation(LDRotationInput{True{},True{},True{},True{},True{},2n,0n,20n,0n,0n,False{}}) == Some{LDRotation{2n,2n,0n,0n,0n,0n,False{}}} : Maybe<&2,LDRotation>}
def ld_mixed_representation_scalar():
  {==}
law ld_invalid_scalar_not_euler:
  {ld_decode_rotation(LDRotationInput{True{},True{},True{},True{},True{},0n,0n,20n,0n,0n,False{}}) == None{} : Maybe<&2,LDRotation>}
def ld_invalid_scalar_not_euler():
  {==}
law ld_euler_rescale_preserved:
  {ld_decode_rotation(LDRotationInput{True{},True{},False{},False{},True{},0n,0n,20n,0n,0n,True{}}) == Some{LDRotation{1n,0n,0n,20n,0n,0n,True{}}} : Maybe<&2,LDRotation>}
def ld_euler_rescale_preserved():
  {==}
law ld_unknown_shade_refuses:
  {ld_decode_shade(True{},0n) == None{} : Maybe<&2,Nat>}
def ld_unknown_shade_refuses():
  {==}
