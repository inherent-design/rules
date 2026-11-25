import Base

# Selected exact atoms; this is not a full float encoding/arithmetic model.
type FloatAtom is Data:
  NegativeTen{}
  NegativeZero{}
  PositiveZero{}
  PositiveTen{}
  NotANumber{}

def jf_rank(value: FloatAtom) -> Nat:
  match value:
    case NegativeTen{}: 0n
    case NegativeZero{}: 1n
    case PositiveZero{}: 2n
    case PositiveTen{}: 3n
    case NotANumber{}: 4n

def jf_total_le(a: FloatAtom,b: FloatAtom) -> Bool:
  Nat.is_le(jf_rank(a),jf_rank(b))

def jf_numeric_rank(value: FloatAtom) -> Nat:
  match value:
    case NegativeTen{}: 0n
    case NegativeZero{}: 1n
    case PositiveZero{}: 1n
    case PositiveTen{}: 2n
    case NotANumber{}: 3n

def jf_numeric_le(a: FloatAtom,b: FloatAtom) -> Bool:
  +x = jf_numeric_rank(a)
  +y = jf_numeric_rank(b)
  Bool.and(Bool.and(Nat.is_lt(x,3n),Nat.is_lt(y,3n)),Nat.is_le(x,y))

def jf_negate(value: FloatAtom) -> FloatAtom:
  match value:
    case NegativeTen{}: PositiveTen{}
    case NegativeZero{}: PositiveZero{}
    case PositiveZero{}: NegativeZero{}
    case PositiveTen{}: NegativeTen{}
    case NotANumber{}: NotANumber{}

def jf_scale(flip: Bool,+value: FloatAtom) -> FloatAtom:
  Bool.pick(FloatAtom,flip,jf_negate(value),value)

def jf_nan(value: FloatAtom) -> Bool:
  Nat.is_eq(jf_rank(value),4n)

law jf_zero_total_order:
  {jf_total_le(NegativeZero{},PositiveZero{}) == True{} : Bool}
def jf_zero_total_order():
  {==}
law jf_zero_reverse_total_refuses:
  {jf_total_le(PositiveZero{},NegativeZero{}) == False{} : Bool}
def jf_zero_reverse_total_refuses():
  {==}
law jf_zero_reverse_numeric_accepts:
  {jf_numeric_le(PositiveZero{},NegativeZero{}) == True{} : Bool}
def jf_zero_reverse_numeric_accepts():
  {==}
law jf_nan_total_self:
  {jf_total_le(NotANumber{},NotANumber{}) == True{} : Bool}
def jf_nan_total_self():
  {==}
law jf_nan_numeric_self_refuses:
  {jf_numeric_le(NotANumber{},NotANumber{}) == False{} : Bool}
def jf_nan_numeric_self_refuses():
  {==}
law jf_negative_zero_scale_flip:
  {jf_scale(True{},NegativeZero{}) == PositiveZero{} : FloatAtom}
def jf_negative_zero_scale_flip():
  {==}
law jf_positive_zero_scale_flip:
  {jf_scale(True{},PositiveZero{}) == NegativeZero{} : FloatAtom}
def jf_positive_zero_scale_flip():
  {==}
law jf_nan_flip_preserved:
  {jf_scale(True{},NotANumber{}) == NotANumber{} : FloatAtom}
def jf_nan_flip_preserved():
  {==}
