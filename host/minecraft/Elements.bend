import Base
import LaterDecode.bend as LD

type ERFace is Data:
  ERFace{known: Bool,is_null: Bool,texture: Bool,uv: Bool,quadrant: Bool,cull: Bool}
type ERInput is Data:
  ERInput{vectors: Bool,shade_valid: Bool,shade: Bool,light_numeric: Bool,light_negative: Bool,light_whole: Nat,light_fraction: Nat,faces_present: Bool,faces: List<&2,ERFace>,rotation: LD.LDRotationInput}
type EROutput is Data:
  EROutput{shade: Bool,light: Nat,faces: Nat,nulls: Nat,culls: Nat,rotation: LD.LDRotation}

def er_face(f: ERFace) -> Bool:
  match f:
    case ERFace{k,n,t,u,q,_}: Bool.and(k,Bool.or(n,Bool.and(t,Bool.and(u,q))))
def er_faces(fs: List<&2,ERFace>) -> Bool:
  match fs:
    case Nil{}: True{}
    case Con{f,rest}: Bool.and(er_face(f),er_faces(rest))
def er_nulls(fs: List<&2,ERFace>) -> Nat:
  match fs:
    case Nil{}: 0n
    case Con{ERFace{_,n,_,_,_,_},rest}: Nat.add(Bool.pick(Nat,n,1n,0n),er_nulls(rest))
def er_culls(fs: List<&2,ERFace>) -> Nat:
  match fs:
    case Nil{}: 0n
    case Con{ERFace{_,n,_,_,_,c},rest}: Nat.add(Bool.pick(Nat,Bool.and(Bool.not(n),c),1n,0n),er_culls(rest))
def er_finish(ok: Bool,rotation: Maybe<&2,LD.LDRotation>,shade: Bool,light: Nat,faces: Nat,nulls: Nat,culls: Nat) -> Maybe<&2,EROutput>:
  match rotation:
    case None{}: None{}
    case Some{r}: Bool.pick(Maybe<&2,EROutput>,ok,Some{EROutput{shade,light,faces,nulls,culls,r}},None{})
def er_decode(i: ERInput) -> Maybe<&2,EROutput>:
  match i:
    case ERInput{v,s,shade,num,neg,+whole,_,present,+faces,r}:
      light_ok=Bool.and(num,Bool.and(Bool.not(Bool.and(neg,Bool.not(Nat.is_eq(whole,0n)))),Bool.not(Nat.is_gt(whole,15n))))
      faces_ok=Bool.and(present,Bool.and(Bool.not(List.is_empty(&2,ERFace,faces)),er_faces(faces)))
      ok=Bool.and(v,Bool.and(s,Bool.and(light_ok,faces_ok)))
      er_finish(ok,LD.ld_decode_rotation(r),shade,whole,List.length(&2,ERFace,faces),er_nulls(faces),er_culls(faces))
def er_selected(+axis: Nat,+dx: Bool,+dy: Bool,+dz: Bool) -> Bool:
  Bool.or(Bool.and(Nat.is_eq(axis,0n),Bool.and(dy,dz)),Bool.or(Bool.and(Nat.is_eq(axis,1n),Bool.and(dx,dz)),Bool.and(Nat.is_eq(axis,2n),Bool.and(dx,dy))))
def er_consume(axis: Nat,dx: Bool,dy: Bool,dz: Bool,is_null: Bool) -> Nat:
  Bool.pick(Nat,er_selected(axis,dx,dy,dz),Bool.pick(Nat,is_null,1n,2n),0n)

law er_null_admitted:
  {er_face(ERFace{True{},True{},False{},False{},False{},False{}}) == True{} : Bool}
def er_null_admitted():
  {==}
law er_unknown_facing_refuses:
  {er_face(ERFace{False{},True{},False{},False{},False{},False{}}) == False{} : Bool}
def er_unknown_facing_refuses():
  {==}
law er_missing_texture_refuses:
  {er_face(ERFace{True{},False{},False{},True{},True{},False{}}) == False{} : Bool}
def er_missing_texture_refuses():
  {==}
law er_bad_uv_refuses:
  {er_face(ERFace{True{},False{},True{},False{},True{},False{}}) == False{} : Bool}
def er_bad_uv_refuses():
  {==}
law er_unknown_cull_admitted:
  {er_face(ERFace{True{},False{},True{},True{},True{},False{}}) == True{} : Bool}
def er_unknown_cull_admitted():
  {==}
law er_null_retained:
  {er_nulls(Con{ERFace{True{},True{},False{},False{},False{},False{}},Nil{}}) == 1n : Nat}
def er_null_retained():
  {==}
law er_null_not_culled:
  {er_culls(Con{ERFace{True{},True{},False{},False{},False{},True{}},Nil{}}) == 0n : Nat}
def er_null_not_culled():
  {==}
law er_degenerate_skips:
  {er_consume(2n,False{},False{},False{},True{}) == 0n : Nat}
def er_degenerate_skips():
  {==}
law er_null_selected_exception:
  {er_consume(2n,True{},True{},True{},True{}) == 1n : Nat}
def er_null_selected_exception():
  {==}
law er_real_selected_intercepts:
  {er_consume(2n,True{},True{},True{},False{}) == 2n : Nat}
def er_real_selected_intercepts():
  {==}
law er_axis_guard:
  {er_consume(0n,True{},False{},True{},True{}) == 0n : Nat}
def er_axis_guard():
  {==}
