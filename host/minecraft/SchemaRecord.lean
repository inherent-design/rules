namespace MinecraftHost.CodecUI

/-- Six authored one-field callers of bundled CodecUI 1.21.1-1.4.10.
    These are not the grammar of a Polytone manager or arbitrary DFU codecs. -/
inductive Form where
  | required | optionalWrapper | defaultZero | defaultNull | mapRequired | mapDefaultTwo
  deriving DecidableEq, BEq
inductive Input where
  | missing | zero | seven | wrongType | nullValue
  deriving DecidableEq, BEq
structure Result where
  advertisedOptional : Bool
  advertisedDefaultPresent : Bool
  advertisedDefault : Nat
  success : Bool
  valuePresent : Bool
  value : Nat
  encodedField : Bool
  deriving DecidableEq, BEq, Repr

def acceptsAbsent : Form → Bool
  | .optionalWrapper | .defaultZero | .mapDefaultTwo => true
  | _ => false
def missingLike : Input → Bool
  | .missing | .nullValue => true
  | _ => false
def evaluate (form : Form) (input : Input) : Result :=
  let success := input != .wrongType && (!missingLike input || acceptsAbsent form)
  let present := success && !(form == .optionalWrapper && missingLike input)
  let value := if !present then 0 else if input == .seven then 7
    else if form == .mapDefaultTwo && missingLike input then 2 else 0
  let encoded := present && !(form == .defaultZero && value == 0) && !(form == .mapDefaultTwo && value == 2)
  ⟨form != .required, form == .defaultZero, 0, success, present, value, encoded⟩

theorem required_missing_refuses : (evaluate .required .missing).success = false := rfl
theorem wrapper_missing_succeeds : (evaluate .optionalWrapper .missing).success = true := rfl
theorem wrapper_empty_is_not_zero : (evaluate .optionalWrapper .missing).valuePresent = false := rfl
theorem default_zero_is_present : (evaluate .defaultZero .missing).valuePresent = true := rfl
theorem default_zero_omits_field : (evaluate .defaultZero .zero).encodedField = false := rfl
theorem explicit_nondefault_is_encoded : (evaluate .defaultZero .seven).encodedField = true := rfl
theorem null_default_advertises_optional : (evaluate .defaultNull .missing).advertisedOptional = true := rfl
theorem null_default_still_requires_value : (evaluate .defaultNull .missing).success = false := rfl
theorem map_required_advertises_optional : (evaluate .mapRequired .missing).advertisedOptional = true := rfl
theorem map_required_still_requires_value : (evaluate .mapRequired .missing).success = false := rfl
theorem map_default_not_in_schema : (evaluate .mapDefaultTwo .missing).advertisedDefaultPresent = false := rfl
theorem map_default_is_used : (evaluate .mapDefaultTwo .missing).value = 2 := rfl
theorem map_default_omits_field : (evaluate .mapDefaultTwo .missing).encodedField = false := rfl
theorem equal_metadata_different_admission :
    (evaluate .optionalWrapper .missing).advertisedOptional = (evaluate .mapRequired .missing).advertisedOptional ∧
    (evaluate .optionalWrapper .missing).success ≠ (evaluate .mapRequired .missing).success := by decide
theorem wrong_type_does_not_use_default (form : Form) : (evaluate form .wrongType).success = false := by cases form <;> rfl
theorem null_and_missing_selected_policy (form : Form) : evaluate form .nullValue = evaluate form .missing := by cases form <;> rfl
theorem seven_value_preserved (form : Form) : (evaluate form .seven).value = 7 := by cases form <;> rfl
theorem seven_field_encoded (form : Form) : (evaluate form .seven).encodedField = true := by cases form <;> rfl

end MinecraftHost.CodecUI
