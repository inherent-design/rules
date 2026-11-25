import Base
import ../java/Word64.bend as W

# Versioned header predicates. Ignored CRC/encoding fields are not PNG validation.
type HeaderInput is Data:
  Input{generation: Nat,limit: Nat,magic: Bool,length13: Bool,ihdr: Bool,width: U32,height: U32,depth: Nat,color: Nat}
def header_error(input: HeaderInput) -> Nat:
  match input:
    case Input{+generation,+limit,magic,length13,ihdr,width,height,+depth,+color}:
      size=Bool.or(Bool.and(Nat.is_eq(generation,1n),Nat.is_lt(limit,16n)),Bool.and(Nat.is_eq(generation,2n),Nat.is_lt(limit,33n)))
      depth_ok=Bool.or(Nat.is_eq(depth,1n),Bool.or(Nat.is_eq(depth,2n),Bool.or(Nat.is_eq(depth,4n),Bool.or(Nat.is_eq(depth,8n),Nat.is_eq(depth,16n)))))
      color_ok=Bool.or(Nat.is_eq(color,0n),Bool.or(Nat.is_eq(color,2n),Bool.or(Nat.is_eq(color,3n),Bool.or(Nat.is_eq(color,4n),Nat.is_eq(color,6n)))))
      bounds=Bool.or(Bool.not(Nat.is_eq(depth,16n)),W.long_roundtrip(W.long_estimate(width,height)))
      modern=Bool.pick(Nat,Bool.and(depth_ok,Bool.and(color_ok,bounds)),0n,1n)
      tail=Bool.pick(Nat,Nat.is_eq(generation,2n),modern,0n)
      Bool.pick(Nat,size,1n,
        Bool.pick(Nat,Nat.is_lt(limit,8n),2n,
          Bool.pick(Nat,Bool.not(magic),1n,
            Bool.pick(Nat,Nat.is_lt(limit,12n),2n,
              Bool.pick(Nat,Bool.not(length13),1n,
                Bool.pick(Nat,Nat.is_lt(limit,16n),2n,
                  Bool.pick(Nat,Bool.not(ihdr),1n,tail)))))))
def header_little(+error: Nat,little: Bool) -> Bool:
  Bool.and(Nat.is_eq(error,0n),little)

law old_short_unchecked:
  {header_error(Input{0n,15n,True{},True{},True{},2,3,8n,6n}) == 2n : Nat}
def old_short_unchecked():
  {==}
law intermediate_short_checked:
  {header_error(Input{1n,15n,True{},True{},True{},2,3,8n,6n}) == 1n : Nat}
def intermediate_short_checked():
  {==}
law intermediate_sixteen:
  {header_error(Input{1n,16n,True{},True{},True{},2,3,8n,6n}) == 0n : Nat}
def intermediate_sixteen():
  {==}
law latest_thirty_three:
  {header_error(Input{2n,32n,True{},True{},True{},2,3,8n,6n}) == 1n : Nat}
def latest_thirty_three():
  {==}
law failure_changes_little_endian:
  {header_little(1n,True{}) == False{} : Bool}
def failure_changes_little_endian():
  {==}
law success_restores_little_endian:
  {header_little(0n,True{}) == True{} : Bool}
def success_restores_little_endian():
  {==}
law independent_pair_not_full_png:
  {header_error(Input{2n,33n,True{},True{},True{},2,3,1n,6n}) == 0n : Nat}
def independent_pair_not_full_png():
  {==}
law int_overflow_rejected:
  {header_error(Input{2n,33n,True{},True{},True{},16384,16384,16n,6n}) == 1n : Nat}
def int_overflow_rejected():
  {==}
law negative_wrap_admitted:
  {header_error(Input{2n,33n,True{},True{},True{},1073741825,2147483646,16n,6n}) == 0n : Nat}
def negative_wrap_admitted():
  {==}
law positive_wrap_admitted:
  {header_error(Input{2n,33n,True{},True{},True{},1073763824,2147439649,16n,6n}) == 0n : Nat}
def positive_wrap_admitted():
  {==}
