import host.java.ArraySearch

namespace MinecraftHost.RangeIndex
open Host.Java.ArraySearch

/-- Composed source/API contract, not a prediction of a stable JDK duplicate index. -/
def admitted (values : List Nat) (query : Nat) (result : Option Nat) : Bool :=
  if values.length < 16 then upperFloorAllowed values query result
  else binaryFloorAllowed values query result

theorem empty_is_fallback : admitted [] 2 none = true := by decide
theorem fifteen_last_tie : admitted (List.replicate 15 2) 2 (some 14) = true := by decide
theorem fifteen_earlier_tie_refuses : admitted (List.replicate 15 2) 2 (some 7) = false := by decide
theorem sixteen_observed_tie_permitted : admitted (List.replicate 16 2) 2 (some 7) = true := by decide
theorem sixteen_other_tie_also_permitted : admitted (List.replicate 16 2) 2 (some 15) = true := by decide
theorem sixteen_first_tie_also_permitted : admitted (List.replicate 16 2) 2 (some 0) = true := by decide
theorem invalid_index_refuses : admitted (List.replicate 16 2) 2 (some 16) = false := by decide
theorem below_all_is_fallback : admitted (List.replicate 16 2) 1 none = true := by decide
theorem above_all_is_last : admitted (List.replicate 16 2) 3 (some 15) = true := by decide
theorem wrong_after_last_refuses : admitted (List.replicate 16 2) 3 (some 7) = false := by decide
theorem small_branch (v : List Nat) (q : Nat) (r : Option Nat) (h : v.length < 16) :
    admitted v q r = upperFloorAllowed v q r := by simp [admitted,h]
theorem large_branch (v : List Nat) (q : Nat) (r : Option Nat) (h : ¬ v.length < 16) :
    admitted v q r = binaryFloorAllowed v q r := by simp [admitted,h]

end MinecraftHost.RangeIndex
