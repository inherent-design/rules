import host.minecraft.LaterDecode

namespace MinecraftHost.Elements
open LaterDecode

structure Face where
  known : Bool
  isNull : Bool
  texture : Bool
  uv : Bool
  quadrant : Bool
  cull : Bool
  deriving DecidableEq, Repr
structure Input where
  vectors : Bool
  shadeValid : Bool
  shade : Bool
  lightNumeric : Bool
  lightNegative : Bool
  lightWhole : Nat
  lightFraction : Nat
  facesPresent : Bool
  faces : List Face
  rotation : RotationInput
  deriving DecidableEq, Repr
structure Output where
  shade : Bool
  light : Nat
  faces : Nat
  nulls : Nat
  culls : Nat
  rotation : Rotation
  deriving DecidableEq, Repr

def faceAdmitted (f : Face) : Bool := f.known && (f.isNull || (f.texture && f.uv && f.quadrant))
def lightAdmitted (i : Input) : Bool := i.lightNumeric && !(i.lightNegative && i.lightWhole != 0) && i.lightWhole ≤ 15
def decode (i : Input) : Option Output := do
  if !i.vectors || !i.shadeValid || !lightAdmitted i || !i.facesPresent || i.faces.isEmpty || !i.faces.all faceAdmitted then none
  else
    let r ← decodeRotation i.rotation
    pure ⟨i.shade,i.lightWhole,i.faces.length,(i.faces.filter (·.isNull)).length,
      (i.faces.filter (fun f => !f.isNull && f.cull)).length,r⟩

/-- Axis 0/1/2 is X/Y/Z. The adapter refuses other axes.
    Nonzero extents are supplied by the selected original element's coordinates. -/
def selected (axis : Nat) (dx dy dz : Bool) : Bool :=
  (axis == 0 && dy && dz) || (axis == 1 && dx && dz) || (axis == 2 && dx && dy)
/-- Closed controlled boundary: 0 empty result;1 null-face exception before lookup;
    2 non-null face reaches the explicit texture-resolution interception. -/
def consume (axis : Nat) (dx dy dz isNull : Bool) : Nat :=
  if !selected axis dx dy dz then 0 else if isNull then 1 else 2

def absentRotation : RotationInput := ⟨false,false,false,false,false,0,0,0,0,0,false⟩
def ordinaryFace : Face := ⟨true,false,true,true,true,false⟩
def nullFace : Face := ⟨true,true,false,false,false,false⟩
def baseline : Input := ⟨true,true,true,true,false,0,0,true,[ordinaryFace],absentRotation⟩

theorem missing_vectors_refuse : decode {baseline with vectors := false} = none := by decide
theorem missing_face_object_refuses : decode {baseline with facesPresent := false} = none := by decide
theorem empty_faces_refuse : decode {baseline with faces := []} = none := by decide
theorem unknown_facing_refuses : decode {baseline with faces := [{ordinaryFace with known := false}]} = none := by decide
theorem null_face_is_admitted : faceAdmitted nullFace = true := rfl
theorem null_bypasses_face_fields : faceAdmitted nullFace = true ∧ nullFace.texture = false := by decide
theorem unknown_cull_does_not_refuse : faceAdmitted ordinaryFace = true := rfl
theorem invalid_uv_refuses : decode {baseline with faces := [{ordinaryFace with uv := false}]} = none := by decide
theorem invalid_quadrant_refuses : decode {baseline with faces := [{ordinaryFace with quadrant := false}]} = none := by decide
theorem shade_shape_is_checked : decode {baseline with shadeValid := false} = none := by decide
theorem fractional_light_truncates : (decode {baseline with lightWhole := 1,lightFraction := 9}).map (·.light) = some 1 := by decide
theorem negative_fractional_light_can_be_zero : (decode {baseline with lightNegative := true,lightWhole := 0,lightFraction := 5}).map (·.light) = some 0 := by decide
theorem negative_whole_light_refuses : decode {baseline with lightNegative := true,lightWhole := 1} = none := by decide
theorem light_above15_refuses : decode {baseline with lightWhole := 16} = none := by decide
theorem numeric_light_required : decode {baseline with lightNumeric := false} = none := by decide
theorem null_face_count_survives : (decode {baseline with faces := [nullFace,ordinaryFace]}).map (fun o => (o.faces,o.nulls)) = some (2,1) := by decide
theorem legacy_shade_false_survives : (decode {baseline with shade := false}).map (·.shade) = some false := by decide
theorem inactive_face_not_dereferenced (axis : Nat) (isNull : Bool) : consume axis false false false isNull = 0 := by simp [consume,selected]
theorem x_face_requires_yz (dx : Bool) : selected 0 dx true true = true := by simp [selected]
theorem z_face_needs_xy : selected 2 true false true = false := by decide
theorem active_null_fails_before_lookup : consume 2 true true true true = 1 := rfl
theorem active_real_face_reaches_interception : consume 2 true true true false = 2 := rfl
theorem admitted_not_consumer_safe :
    (decode {baseline with faces := [nullFace]}).isSome = true ∧ consume 2 true true true true = 1 := by decide

end MinecraftHost.Elements
