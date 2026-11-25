import Std
namespace Host.Java.Word32

/-- Bit representation of Java int addition/subtraction. Signed interpretation,
    valid random bounds, and mathematical/unbounded sums are separate contracts. -/
def negative (word : UInt32) : Bool := word.toNat ≥ 2147483648
def positive (word : UInt32) : Bool := word != 0 && !negative word
def signed (word : UInt32) : Int :=
  if negative word then Int.ofNat word.toNat - 4294967296 else Int.ofNat word.toNat
theorem max_plus_one_is_negative : negative ((2147483647 : UInt32)+1) = true := by decide
theorem max_plus_one_bits : ((2147483647 : UInt32)+1).toNat = 2147483648 := by decide
theorem zero_minus_one_bits : ((0 : UInt32)-1).toNat = 4294967295 := by decide
theorem two_max_wrap_to_minus_two : signed ((2147483647 : UInt32)+2147483647) = -2 := by decide
theorem four_positive_terms_can_sum_to_zero :
    ((1073741824 : UInt32)+1073741824+1073741824+1073741824) = 0 := by decide
theorem zero_is_not_positive_bound : positive 0 = false := by decide
theorem signed_min_is_not_positive_bound : positive 2147483648 = false := by decide
theorem max_is_positive_bound : positive 2147483647 = true := by decide
end Host.Java.Word32
