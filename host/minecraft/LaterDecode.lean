import host.minecraft.ArtifactVersions

namespace MinecraftHost.LaterDecode
open ArtifactVersions

/-- A bounded decimal input profile. Fraction is retained before integer coercion;
    arbitrary numeric syntax,overflow and negative fractional tokens are not admitted. -/
structure NumberToken where
  negative : Bool
  whole : Nat
  fraction : Nat
  deriving DecidableEq, BEq, Repr
def nonnegativeInt (n : NumberToken) : Option Nat :=
  if n.negative && n.whole != 0 then none else some n.whole

def decodeFormat (top : Bool) (tokens : List NumberToken) : Option Version := do
  if tokens.isEmpty || tokens.length > 256 then none else do
    let values ← tokens.mapM nonnegativeInt
    let major ← values.head?
    pure ⟨major,values[1]?.getD (if top then 2147483647 else 0)⟩

def versionLe (a b : Version) : Bool := a.major < b.major || (a.major == b.major && a.minor ≤ b.minor)
structure PackInput where
  threshold : Nat
  lower : Option Version
  upper : Option Version
  main : Option Nat
  old : Option (Nat × Nat)
  deriving DecidableEq, Repr
structure Bounds where
  lower : Version
  upper : Version
  deriving DecidableEq, BEq, Repr

def validMain (main lower upper : Nat) : Bool := 15 ≤ main && lower ≤ main && main ≤ upper
def optionalMain (main : Option Nat) (lower upper : Nat) : Bool :=
  main.map (fun n => validMain n lower upper) |>.getD true
def requiredMain (main : Option Nat) (lower upper : Nat) : Bool :=
  main.map (fun n => validMain n lower upper) |>.getD false

def decodePack (p : PackInput) : Option Bounds :=
  match p.lower,p.upper with
  | some lower,some upper =>
    if !versionLe lower upper then none
    else if lower.major > p.threshold then
      if p.old.isSome || !optionalMain p.main lower.major upper.major then none
      else some ⟨lower,upper⟩
    else match p.old with
      | none => none
      | some (a,b) =>
        if a == lower.major && (b == upper.major || b == p.threshold) && requiredMain p.main lower.major upper.major
        then some ⟨lower,upper⟩ else none
  | none,none => match p.old with
    | some (a,b) =>
      if b ≤ p.threshold && requiredMain p.main a b then some ⟨⟨a,0⟩,⟨b,0⟩⟩ else none
    | none => match p.main with
      | some main => if main ≤ p.threshold then some ⟨⟨main,0⟩,⟨main,0⟩⟩ else none
      | none => none
  | _,_ => none

structure RotationInput where
  present : Bool
  originValid : Bool
  axisPresent : Bool
  anglePresent : Bool
  xyzPresent : Bool
  axis : Nat
  angle : Nat
  x : Nat
  y : Nat
  z : Nat
  rescale : Bool
  deriving DecidableEq, Repr
structure Rotation where
  mode : Nat
  axis : Nat := 0
  angle : Nat := 0
  x : Nat := 0
  y : Nat := 0
  z : Nat := 0
  rescale : Bool := false
  deriving DecidableEq, BEq, Repr
def decodeRotation (r : RotationInput) : Option Rotation :=
  if !r.present then some {mode := 0}
  else if !r.originValid then none
  else if r.axisPresent || r.anglePresent then
    if r.axisPresent && r.anglePresent && 1 ≤ r.axis && r.axis ≤ 3
    then some { mode := 2,axis := r.axis,angle := r.angle,rescale := r.rescale } else none
  else if r.xyzPresent then some { mode := 1,x := r.x,y := r.y,z := r.z,rescale := r.rescale }
  else none

def decodeShade (present : Bool) (direction : Nat) : Option Nat :=
  if !present then some 0 else if 1 ≤ direction && direction ≤ 6 then some direction else none

theorem fractional_token_is_not_strict_integer_rejection : nonnegativeInt ⟨false,97,5⟩ = some 97 := rfl
theorem negative_whole_refuses : nonnegativeInt ⟨true,1,0⟩ = none := rfl
theorem endpoint_defaults_differ :
    decodeFormat false [⟨false,97,0⟩] = some ⟨97,0⟩ ∧
    decodeFormat true [⟨false,97,0⟩] = some ⟨97,2147483647⟩ := by decide
theorem extra_component_not_part_of_stored_version :
    decodeFormat false [⟨false,97,0⟩,⟨false,1,0⟩,⟨false,7,0⟩] = some ⟨97,1⟩ := by decide
theorem empty_format_refuses : decodeFormat false [] = none := rfl
theorem version_minor_orders_bounds : versionLe ⟨97,2⟩ ⟨97,1⟩ = false := by decide
theorem resource_legacy_threshold : decodePack ⟨64,none,none,some 65,none⟩ = none := by decide
theorem data_legacy_threshold : decodePack ⟨81,none,none,some 82,none⟩ = none := by decide
theorem incomplete_pair_refuses : decodePack ⟨64,some ⟨97,0⟩,none,none,none⟩ = none := rfl
theorem new_range_without_old_fields :
    decodePack ⟨64,some ⟨97,0⟩,some ⟨97,2147483647⟩,none,none⟩ = some ⟨⟨97,0⟩,⟨97,2147483647⟩⟩ := by decide
theorem deprecated_old_field_refuses_new_only_range :
    decodePack ⟨64,some ⟨97,0⟩,some ⟨97,1⟩,none,some (97,97)⟩ = none := by decide
theorem mixed_legacy_range_retains_minor_endpoint :
    decodePack ⟨64,some ⟨64,0⟩,some ⟨97,2147483647⟩,some 64,some (64,64)⟩ = some ⟨⟨64,0⟩,⟨97,2147483647⟩⟩ := by decide
theorem absent_rotation_does_not_require_origin : decodeRotation ⟨false,false,false,false,false,0,0,0,0,0,false⟩ = some {mode := 0} := rfl
theorem mixed_representation_uses_scalar :
    decodeRotation ⟨true,true,true,true,true,2,0,20,0,0,false⟩ = some {mode := 2,axis := 2} := by decide
theorem invalid_scalar_does_not_fall_back_to_xyz :
    decodeRotation ⟨true,true,true,true,true,0,0,20,0,0,false⟩ = none := by decide
theorem incomplete_scalar_does_not_fall_back :
    decodeRotation ⟨true,true,true,false,true,2,0,20,0,0,false⟩ = none := by decide
theorem unrestricted_scalar_angle_in_profile :
    decodeRotation ⟨true,true,true,true,false,2,123,0,0,0,false⟩ = some {mode := 2,axis := 2,angle := 123} := by decide
theorem euler_rescale_retained :
    decodeRotation ⟨true,true,false,false,true,0,0,20,0,0,true⟩ = some {mode := 1,x := 20,rescale := true} := by decide
theorem present_rotation_requires_origin :
    decodeRotation ⟨true,false,false,false,true,0,0,20,0,0,false⟩ = none := rfl
theorem unknown_direction_refuses : decodeShade true 0 = none := rfl
theorem legacy_shade_is_not_an_override_input : decodeShade false 0 = some 0 := rfl

end MinecraftHost.LaterDecode
