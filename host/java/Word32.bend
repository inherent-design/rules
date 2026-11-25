import Base

# Unsigned bit representation, signed int interpretation supplied by the high bit.
def jw_negative(word: U32) -> Bool:
  U32.is_ge(word,2147483648)
def jw_positive(+word: U32) -> Bool:
  Bool.and(Bool.not(U32.is_zero(word)),Bool.not(jw_negative(word)))
law jw_max_plus_one_negative:
  {jw_negative(U32.add(2147483647,1)) == True{} : Bool}
def jw_max_plus_one_negative():
  {==}
law jw_zero_minus_one:
  {U32.sub(0,1) == 4294967295 : U32}
def jw_zero_minus_one():
  {==}
law jw_two_max_wrap:
  {U32.add(2147483647,2147483647) == 4294967294 : U32}
def jw_two_max_wrap():
  {==}
law jw_positive_sum_can_zero:
  {U32.add(U32.add(U32.add(1073741824,1073741824),1073741824),1073741824) == 0 : U32}
def jw_positive_sum_can_zero():
  {==}
law jw_zero_bound_refuses:
  {jw_positive(0) == False{} : Bool}
def jw_zero_bound_refuses():
  {==}
law jw_min_bound_refuses:
  {jw_positive(2147483648) == False{} : Bool}
def jw_min_bound_refuses():
  {==}
