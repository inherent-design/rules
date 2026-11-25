import Std

namespace MinecraftHost.Decoding

/-- Parser observations are not resource availability or consumer execution. -/
structure Consumer where
  decoded : Bool
  references : Bool
  context : Bool
  prepared : Bool
  published : Bool
  deriving DecidableEq

def usable (c : Consumer) : Bool :=
  c.decoded && c.references && c.context && c.prepared && c.published

def metadata (description number : Bool) : Bool := description && number
def optionalRange (present valid : Bool) : Bool := present && valid
def identifier (namespaceChars pathChars : Bool) : Bool := namespaceChars && pathChars

/-- Natural dimensions describe the retained fixtures, not signed integer overflow. -/
def gui (kind width height left top right bottom : Nat) (scalar : Bool) : Bool :=
  if kind == 0 then true
  else if kind == 1 then 0 < width && 0 < height
  else if kind == 2 then
    0 < width && 0 < height && (!scalar || 0 < left) &&
      left + right < width && top + bottom < height
  else false

/-- Legacy primitive frame indices escape the object's nonnegative-index check.
    Sprite/frame bounds belong to the later texture consumer. -/
def animation (successor dimensions times negativePrimitive negativeObject : Bool) : Bool :=
  dimensions && times && !negativeObject && (!successor || !negativePrimitive)

/-- Shape: 0 absent, 1 false, 2 true, 3 number, 4 other string, 5 "true". -/
def booleanShape (successor : Bool) (shape : Nat) : Bool := !successor || shape ≤ 2
def booleanValue (shape : Nat) : Bool := shape == 2 || shape == 5
def texture (successor : Bool) (blur clamp : Nat) : Bool :=
  booleanShape successor blur && booleanShape successor clamp
def textureValue (blur clamp : Nat) : Nat :=
  (if booleanValue blur then 1 else 0) + (if booleanValue clamp then 2 else 0)

/-- Twice the absolute scalar angle avoids claiming a floating-point proof. -/
def angle (twiceAbsolute : Nat) : Bool :=
  twiceAbsolute == 0 || twiceAbsolute == 45 || twiceAbsolute == 90
def geometry (negativeExtent positiveExtent twiceAngle : Nat) (shape axis : Bool) : Bool :=
  shape && axis && negativeExtent ≤ 16 && positiveExtent ≤ 32 && angle twiceAngle

def equipment (known : Bool) (groups smallestGroup : Nat) : Bool :=
  known && 0 < groups && 0 < smallestGroup

/-- Codec.either(fixed, unit(fullscreen)): failed fixed dimensions can select
    fullscreen rather than reject the entire target. No allocation is modeled. -/
def postTarget (width height : Nat) : Nat := if 0 < width && 0 < height then 2 else 1

theorem missing_metadata_description (n : Bool) : metadata false n = false := by simp [metadata]
theorem metadata_format_sign_not_checked : metadata true true = true := rfl
theorem invalid_optional_range_is_absent (p : Bool) : optionalRange p false = false := by simp [optionalRange]
theorem range_failure_does_not_reject_required_fields : metadata true true = true ∧ optionalRange true false = false := by decide
theorem identifier_both_parts_required (a b : Bool) : identifier a b = true ↔ a = true ∧ b = true := by simp [identifier]
theorem stretch_has_no_dimension_requirement (w h l t r b : Nat) (s : Bool) : gui 0 w h l t r b s = true := by simp [gui]
theorem zero_tile_width_refused (h : Nat) : gui 1 0 h 0 0 0 0 false = false := by simp [gui]
theorem zero_scalar_border_refused : gui 2 8 8 0 0 0 0 true = false := by decide
theorem zero_record_border_accepted : gui 2 8 8 0 0 0 0 false = true := by decide
theorem missing_center_refused : gui 2 8 8 4 4 4 4 true = false := by decide
theorem negative_primitive_changes_between_versions :
    animation false true true true false = true ∧ animation true true true true false = false := by decide
theorem negative_object_refused (v : Bool) : animation v true true false true = false := by simp [animation]
theorem zero_frame_time_refused (v : Bool) : animation v true false false false = false := by simp [animation]
theorem legacy_boolean_coercion : texture false 3 5 = true ∧ textureValue 3 5 = 2 := by decide
theorem successor_refuses_boolean_coercion : texture true 3 0 = false ∧ texture true 5 0 = false := by decide
theorem ordinary_angle_accepted : geometry 0 16 45 true true = true := by decide
theorem arbitrary_scalar_angle_refused : geometry 0 16 122 true true = false := by decide
theorem xyz_without_axis_refused : geometry 0 16 0 true false = false := by decide
theorem extent_below_minus16_refused : geometry 17 16 0 true true = false := by decide
theorem empty_equipment_refused : equipment true 0 0 = false := by decide
theorem empty_equipment_group_refused : equipment true 1 0 = false := by decide
theorem zero_fixed_target_falls_back : postTarget 0 16 = 1 := by decide
theorem valid_fixed_target_selected : postTarget 16 16 = 2 := by decide
theorem accepted_parser_does_not_imply_usable : usable ⟨true,false,true,true,true⟩ = false := rfl
theorem unpublished_not_usable (c : Consumer) : usable {c with published := false} = false := by simp [usable]
end MinecraftHost.Decoding
