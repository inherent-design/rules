import Base
type PAElement is Data:
  PAElement{kind: Nat,scale: Nat,cull: Bool,origin: Nat,numeric: Bool}
def pa_check(e: PAElement) -> Nat:
  match e:
    case PAElement{+kind,+scale,cull,+origin,numeric}:
      Bool.pick(Nat,Nat.is_eq(kind,0n),3n,Bool.pick(Nat,Nat.is_eq(kind,2n),
        Bool.pick(Nat,Nat.is_eq(scale,3n),4n,Bool.pick(Nat,Nat.is_eq(scale,2n),5n,
          Bool.pick(Nat,cull,6n,Bool.pick(Nat,Nat.is_eq(origin,0n),7n,
            Bool.pick(Nat,Bool.or(Nat.is_eq(origin,1n),Bool.not(numeric)),8n,0n))))),0n))
def pa_count(es: List<&2,PAElement>,+wanted: Nat) -> Nat:
  match es:
    case Nil{}: 0n
    case Con{PAElement{kind,scale,cull,origin,numeric},tail}:
      Nat.add(Bool.pick(Nat,Nat.is_eq(kind,wanted),1n,0n),pa_count(tail,wanted))
def pa_length(es: List<&2,PAElement>) -> Nat:
  match es:
    case Nil{}: 0n
    case Con{head,tail}: Nat.add(1n,pa_length(tail))
def pa_audit(es: List<&2,PAElement>) -> Nat:
  match es:
    case Nil{}: 0n
    case Con{head,tail}:
      +code = pa_check(head)
      Bool.pick(Nat,Nat.is_eq(code,0n),pa_audit(tail),code)
def pa_evaluate(ready: Bool,+es: List<&2,PAElement>) -> List<&2,Nat>:
  +modern = pa_count(es,2n)
  +error = pa_audit(es)
  Bool.pick(List<&2,Nat>,Bool.and(ready,Bool.not(Nat.is_eq(modern,0n))),
    Bool.pick(List<&2,Nat>,Nat.is_gt(pa_length(es),128n),[2n,0n,0n],
      Bool.pick(List<&2,Nat>,Nat.is_eq(error,0n),[1n,modern,pa_count(es,1n)],[error,0n,0n])),[0n,0n,0n])
law pa_unchanged_outer:
  {pa_evaluate(False{},[PAElement{2n,3n,True{},0n,False{}}]) == [0n,0n,0n] : List<&2,Nat>}
def pa_unchanged_outer():
  {==}
law pa_no_euler_not_validation:
  {pa_evaluate(True{},[PAElement{0n,0n,False{},0n,False{}}]) == [0n,0n,0n] : List<&2,Nat>}
def pa_no_euler_not_validation():
  {==}
law pa_good_rewrite:
  {pa_evaluate(True{},[PAElement{2n,0n,False{},2n,True{}}]) == [1n,1n,0n] : List<&2,Nat>}
def pa_good_rewrite():
  {==}
law pa_modern_checks_sibling:
  {pa_evaluate(True{},[PAElement{0n,0n,False{},0n,False{}},PAElement{2n,0n,False{},2n,True{}}]) == [3n,0n,0n] : List<&2,Nat>}
def pa_modern_checks_sibling():
  {==}
law pa_scale_type_first:
  {pa_check(PAElement{2n,3n,True{},0n,False{}}) == 4n : Nat}
def pa_scale_type_first():
  {==}
law pa_rescale_first:
  {pa_check(PAElement{2n,2n,True{},0n,False{}}) == 5n : Nat}
def pa_rescale_first():
  {==}
law pa_cull_first:
  {pa_check(PAElement{2n,0n,True{},0n,False{}}) == 6n : Nat}
def pa_cull_first():
  {==}
law pa_numeric_refuses:
  {pa_check(PAElement{2n,0n,False{},2n,False{}}) == 8n : Nat}
def pa_numeric_refuses():
  {==}
