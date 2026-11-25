import Std
namespace Host.Minecraft.FontFilter

/-- Two selected font options; each field is0 absent,1 requires false,2 requires true. -/
structure Filter where
  uniform : Nat := 0
  japanese : Nat := 0
  deriving DecidableEq, Repr
def ofCode (code : Nat) : Filter := ⟨code % 3,code / 3⟩
def overrideField (left right : Nat) : Nat := if left == 0 then right else left
def merge (left right : Filter) : Filter :=
  ⟨overrideField left.uniform right.uniform,overrideField left.japanese right.japanese⟩
def fieldPass (mode : Nat) (enabled : Bool) : Bool := mode == 0 || enabled == (mode == 2)
def allows (filter : Filter) (mask : Nat) : Bool :=
  fieldPass filter.uniform (mask % 2 == 1) && fieldPass filter.japanese (mask / 2 == 1)
def evaluate (left right mask : Nat) (merged : Bool) : Nat :=
  (allows (if merged then merge (ofCode left) (ofCode right) else ofCode left) mask).toNat

theorem absent_field_passes (enabled : Bool) : fieldPass 0 enabled = true := by rfl
theorem left_absent_uses_right (right : Nat) : overrideField 0 right = right := by rfl
theorem right_absent_preserves_left (left : Nat) : overrideField left 0 = left := by
  by_cases h : left = 0 <;> simp [overrideField,h]
theorem field_idempotent (field : Nat) : overrideField field field = field := by
  by_cases h : field = 0 <;> simp [overrideField,h]
theorem field_associative (a b c : Nat) :
    overrideField a (overrideField b c) = overrideField (overrideField a b) c := by
  by_cases h : a = 0 <;> simp [overrideField,h]
theorem merge_empty_left (filter : Filter) : merge {} filter = filter := by cases filter; rfl
theorem merge_empty_right (filter : Filter) : merge filter {} = filter := by
  cases filter; simp [merge,right_absent_preserves_left]
theorem empty_filter_allows (mask : Nat) : allows {} mask = true := by rfl
theorem declared_false_overrides_true : merge (ofCode 1) (ofCode 2) = ofCode 1 := by decide
theorem merge_is_not_commutative : merge (ofCode 1) (ofCode 2) ≠ merge (ofCode 2) (ofCode 1) := by decide
theorem override_can_allow_disjoint_predicates : evaluate 1 2 0 true = 1 := by decide
theorem conjunction_of_disjoint_predicates_refuses :
    (allows (ofCode 1) 0 && allows (ofCode 2) 0) = false := by decide
end Host.Minecraft.FontFilter
