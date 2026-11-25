import Base

# Two bounded 32-bit words. No conversion of large words to unary Nat.
type LongBits is Data:
  Bits{low: U32,high: U32}

def long_unsigned_product(+a: U32,+b: U32) -> LongBits:
  +a0=U32.and(a,65535)
  +a1=U32.shrn(a,16n)
  +b0=U32.and(b,65535)
  +b1=U32.shrn(b,16n)
  +p00=U32.mul(a0,b0)
  +t=U32.add(U32.mul(a1,b0),U32.shrn(p00,16n))
  +u=U32.add(U32.mul(a0,b1),U32.and(t,65535))
  Bits{U32.add(U32.shln(u,16n),U32.and(p00,65535)),U32.add(U32.add(U32.mul(a1,b1),U32.shrn(t,16n)),U32.shrn(u,16n))}

def long_signed_adjust(product: LongBits,+a: U32,+b: U32) -> LongBits:
  match product:
    case Bits{low,+high}:
      +high_a=Bool.pick(U32,U32.is_ge(a,2147483648),U32.sub(high,b),high)
      high_b=Bool.pick(U32,U32.is_ge(b,2147483648),U32.sub(high_a,a),high_a)
      Bits{low,high_b}

def long_shift_three(product: LongBits) -> LongBits:
  match product:
    case Bits{+low,high}: Bits{U32.shln(low,3n),U32.or(U32.shln(high,3n),U32.shrn(low,29n))}

def long_estimate(+width: U32,+height: U32) -> LongBits:
  long_shift_three(long_signed_adjust(long_unsigned_product(width,height),width,height))

def long_narrow(word: LongBits) -> LongBits:
  match word:
    case Bits{+low,high}: Bits{low,Bool.pick(U32,U32.is_ge(low,2147483648),4294967295,0)}

def long_roundtrip(word: LongBits) -> Bool:
  match word:
    case Bits{low,high}:
      U32.is_eq(high,Bool.pick(U32,U32.is_ge(low,2147483648),4294967295,0))

# Checked-product predicate restricted to positive signed int inputs by the codec.
def long_checked_product(product: LongBits) -> Bool:
  match product:
    case Bits{low,high}: U32.is_lt(high,268435456)
def long_checked(width: U32,height: U32) -> Bool:
  long_checked_product(long_unsigned_product(width,height))

law small_product:
  {long_estimate(2,3) == Bits{48,0} : LongBits}
def small_product():
  {==}
law negative_input_sign_extension:
  {long_estimate(4294967295,1) == Bits{4294967288,4294967295} : LongBits}
def negative_input_sign_extension():
  {==}
law narrow_rejects_int_overflow:
  {long_roundtrip(long_estimate(16384,16384)) == False{} : Bool}
def narrow_rejects_int_overflow():
  {==}
law checked_accepts_int_overflow:
  {long_checked(16384,16384) == True{} : Bool}
def checked_accepts_int_overflow():
  {==}
law negative_wrap_bits:
  {long_estimate(1073741825,2147483646) == Bits{4294967280,4294967295} : LongBits}
def negative_wrap_bits():
  {==}
law negative_wrap_roundtrip:
  {long_roundtrip(long_estimate(1073741825,2147483646)) == True{} : Bool}
def negative_wrap_roundtrip():
  {==}
law positive_wrap_bits:
  {long_estimate(1073763824,2147439649) == Bits{846110592,0} : LongBits}
def positive_wrap_bits():
  {==}
law positive_wrap_roundtrip:
  {long_roundtrip(long_estimate(1073763824,2147439649)) == True{} : Bool}
def positive_wrap_roundtrip():
  {==}
law positive_wrap_checked_refusal:
  {long_checked(1073763824,2147439649) == False{} : Bool}
def positive_wrap_checked_refusal():
  {==}
law negative_wrap_checked_refusal:
  {long_checked(1073741825,2147483646) == False{} : Bool}
def negative_wrap_checked_refusal():
  {==}
