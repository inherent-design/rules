import Base
import ../java/Word32.bend as W
def gui_sum_before(a: U32,b: U32,dim: U32) -> Bool:
  +sum = U32.add(a,b)
  Bool.or(W.jw_negative(sum),U32.is_lt(sum,dim))
def gui_scaling_eval(+kind: Nat,+w: U32,+h: U32,+l: U32,+t: U32,+r: U32,+b: U32,nonnegative: Bool,scalar: Bool,modern: Bool,stretch: Bool) -> Nat:
  dimensions = Bool.and(U32.is_gt(w,0),U32.is_gt(h,0))
  border = Bool.and(nonnegative,Bool.or(Bool.not(scalar),U32.is_gt(l,0)))
  centers = Bool.and(gui_sum_before(l,r,w),gui_sum_before(t,b,h))
  accepted = Bool.or(Nat.is_eq(kind,0n),Bool.and(dimensions,Bool.or(Nat.is_eq(kind,1n),Bool.and(Nat.is_eq(kind,2n),Bool.and(border,centers)))))
  tag = Bool.pick(Nat,Nat.is_eq(kind,0n),1n,Bool.pick(Nat,Nat.is_eq(kind,1n),2n,Bool.pick(Nat,modern,Bool.pick(Nat,stretch,5n,4n),3n)))
  Bool.pick(Nat,accepted,tag,0n)
law gui_horizontal_wrap_before:
  {gui_sum_before(2147483647,1,8) == True{} : Bool}
def gui_horizontal_wrap_before():
  {==}
law gui_double_max_before:
  {gui_sum_before(2147483647,2147483647,8) == True{} : Bool}
def gui_double_max_before():
  {==}
law gui_no_center_refused:
  {gui_scaling_eval(2n,8,8,4,4,4,4,True{},True{},False{},False{}) == 0n : Nat}
def gui_no_center_refused():
  {==}
law gui_record_zero_accepted:
  {gui_scaling_eval(2n,8,8,0,0,0,0,True{},False{},False{},False{}) == 3n : Nat}
def gui_record_zero_accepted():
  {==}
law gui_scalar_zero_refused:
  {gui_scaling_eval(2n,8,8,0,0,0,0,True{},True{},False{},False{}) == 0n : Nat}
def gui_scalar_zero_refused():
  {==}
law gui_modern_stretch:
  {gui_scaling_eval(2n,8,8,1,1,1,1,True{},True{},True{},True{}) == 5n : Nat}
def gui_modern_stretch():
  {==}
law gui_old_stretch_ignored:
  {gui_scaling_eval(2n,8,8,1,1,1,1,True{},True{},False{},True{}) == 3n : Nat}
def gui_old_stretch_ignored():
  {==}
law gui_negative_border_refused:
  {gui_scaling_eval(2n,8,8,1,0,0,0,False{},False{},True{},False{}) == 0n : Nat}
def gui_negative_border_refused():
  {==}
