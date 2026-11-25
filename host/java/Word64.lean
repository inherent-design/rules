import Std

namespace Host.Java.Word64

/-- Java signed-int widening represented as long bits. Inputs are int bit patterns. -/
def extendInt (bits : Nat) : UInt64 :=
  if bits < 2147483648 then UInt64.ofNat bits else UInt64.ofNat bits - 4294967296

def signed (word : UInt64) : Int :=
  if word.toNat < 9223372036854775808 then Int.ofNat word.toNat
  else Int.ofNat word.toNat - 18446744073709551616

def narrowed (word : UInt64) : UInt64 := extendInt word.toUInt32.toNat
def intRoundtrip (word : UInt64) : Bool := word == narrowed word
def estimate (widthBits heightBits : Nat) : UInt64 :=
  4 * extendInt widthBits * extendInt heightBits * 2

/-- Unbounded positive-input comparison, not the Java wrapped computation. -/
def mathematical (width height : Nat) : Nat := 4 * width * height * 2
def checkedLong (width height : Nat) : Bool := mathematical width height ≤ 9223372036854775807

theorem negative_int_widens_with_sign : signed (extendInt 4294967295) = -1 := by decide
theorem small_estimate : signed (estimate 2 3) = 48 := by decide
theorem int_overflow_not_roundtrip : intRoundtrip (estimate 16384 16384) = false := by decide
theorem int_overflow_can_still_fit_long : checkedLong 16384 16384 = true := by decide
theorem negative_wrap_bits : signed (estimate 1073741825 2147483646) = -16 := by decide
theorem negative_wrap_passes_narrowing : intRoundtrip (estimate 1073741825 2147483646) = true := by decide
theorem positive_wrap_bits : signed (estimate 1073763824 2147439649) = 846110592 := by decide
theorem positive_wrap_passes_narrowing : intRoundtrip (estimate 1073763824 2147439649) = true := by decide
theorem positive_wrap_is_not_checked_product : checkedLong 1073763824 2147439649 = false := by decide
theorem negative_wrap_is_not_checked_product : checkedLong 1073741825 2147483646 = false := by decide

end Host.Java.Word64
