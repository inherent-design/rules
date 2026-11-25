import Std

namespace Host.Minecraft.BlockTerm

/-- Well-formed Unicode scalar lists. ASCII ! has the same one-unit prefix in
    Java UTF-16. This is a literal atom, not a Terms splitter or property value. -/
structure Term where
  value : List UInt32
  negated : Bool
  deriving BEq, DecidableEq, Repr

def construct (value : List UInt32) (negated : Bool) : Option Term :=
  if value.isEmpty then none else some ⟨value, negated⟩

def parse : List UInt32 → Option Term
  | [] => none
  | c :: cs => if c == 33 then construct cs true else some ⟨c :: cs, false⟩

def encode (t : Term) : List UInt32 := if t.negated then 33 :: t.value else t.value

def roundtrip (t : Term) : Option Term := parse (encode t)

theorem empty_parse_refuses : parse [] = none := rfl
theorem lone_bang_refuses : parse [33] = none := by decide
theorem empty_constructor_refuses (negated : Bool) : construct [] negated = none := rfl
theorem parse_strips_one_bang : parse [33, 33, 97] = some ⟨[33, 97], true⟩ := by decide
theorem separator_is_literal : parse [97, 124, 98] = some ⟨[97, 124, 98], false⟩ := by decide
theorem whitespace_is_literal : parse [32, 33, 97] = some ⟨[32, 33, 97], false⟩ := by decide
theorem fullwidth_bang_is_literal : parse [65281, 97] = some ⟨[65281, 97], false⟩ := by decide
theorem supplementary_scalar_is_preserved : parse [33, 129302] = some ⟨[129302], true⟩ := by decide

theorem flagged_constructor_roundtrips (c : UInt32) (cs : List UInt32) :
    roundtrip ⟨c :: cs, true⟩ = some ⟨c :: cs, true⟩ := by
  simp [roundtrip, encode, parse, construct]

theorem unflagged_constructor_roundtrips_without_bang (c : UInt32) (cs : List UInt32)
    (notBang : c ≠ 33) : roundtrip ⟨c :: cs, false⟩ = some ⟨c :: cs, false⟩ := by
  simp [roundtrip, encode, parse, notBang]

theorem parse_image_roundtrips (input : List UInt32) (t : Term) (parsed : parse input = some t) :
    roundtrip t = some t := by
  cases input with
  | nil => simp [parse] at parsed
  | cons c cs =>
    by_cases bang : c = 33
    · subst c
      cases cs with
      | nil => simp [parse, construct] at parsed
      | cons d ds =>
        simp [parse, construct] at parsed
        subst t
        exact flagged_constructor_roundtrips d ds
    · simp [parse, bang] at parsed
      subst t
      exact unflagged_constructor_roundtrips_without_bang c cs bang

theorem direct_constructor_can_encode_refused_input :
    construct [33] false = some ⟨[33], false⟩ ∧ roundtrip ⟨[33], false⟩ = none := by decide
theorem direct_constructor_can_reparse_to_different_record :
    roundtrip ⟨[33, 97], false⟩ = some ⟨[97], true⟩ := by decide
theorem explicit_flag_preserves_leading_bang_value :
    roundtrip ⟨[33, 97], true⟩ = some ⟨[33, 97], true⟩ := by decide

end Host.Minecraft.BlockTerm
