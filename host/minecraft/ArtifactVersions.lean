import Std

namespace MinecraftHost.ArtifactVersions

/-- Declared version.json pack_version facts, not a pack.mcmeta decoder or
    resource-pack compatibility decision. Major and minor are independent. -/
structure Version where
  major : Nat
  minor : Nat
  deriving DecidableEq, BEq, Repr

inductive Encoding where
  | legacy (value : Nat)
  | majorMinor (major minor : Nat)
  deriving DecidableEq, Repr

def normalize : Encoding → Version
  | .legacy n => ⟨n,0⟩
  | .majorMinor a b => ⟨a,b⟩

def legacyRepresentation (v : Version) : Option Nat :=
  if v.minor == 0 then some v.major else none

/-- A declared launcher-major prerequisite only. It is not evidence that an
    application runs on this JVM/vendor/OS/backend or that it renders correctly. -/
def declaredJavaSatisfied (required available : Nat) : Bool := required ≤ available

theorem legacy_minor_zero (n : Nat) : (normalize (.legacy n)).minor = 0 := rfl
theorem legacy_round_trip (n : Nat) : legacyRepresentation (normalize (.legacy n)) = some n := rfl
theorem pair_preserves_both (a b : Nat) : normalize (.majorMinor a b) = ⟨a,b⟩ := rfl
theorem normalized_pair_round_trip (v : Version) : normalize (.majorMinor v.major v.minor) = v := rfl
theorem nonzero_minor_has_no_lossless_legacy (a b : Nat) (nonzero : b ≠ 0) :
    legacyRepresentation ⟨a,b⟩ = none := by simp [legacyRepresentation,nonzero]
theorem minor_changes_identity (a b c : Nat) (different : b ≠ c) :
    normalize (.majorMinor a b) ≠ normalize (.majorMinor a c) := by
  intro equal
  exact different (congrArg Version.minor equal)
theorem major_only_projection_loses_information :
    (normalize (.majorMinor 97 0)).major = (normalize (.majorMinor 97 1)).major ∧
    normalize (.majorMinor 97 0) ≠ normalize (.majorMinor 97 1) := by decide
theorem java263_resource_minor_cannot_be_flattened : legacyRepresentation ⟨97,1⟩ = none := by decide
theorem java12111_data_minor_cannot_be_flattened : legacyRepresentation ⟨94,1⟩ = none := by decide
theorem zero_minor_pair_can_be_legacy : legacyRepresentation ⟨75,0⟩ = some 75 := by decide
theorem required25_is_not_satisfied_by21 : declaredJavaSatisfied 25 21 = false := by decide
theorem required21_is_not_satisfied_by17 : declaredJavaSatisfied 21 17 = false := by decide
theorem required25_is_satisfied_by25 : declaredJavaSatisfied 25 25 = true := by decide

end MinecraftHost.ArtifactVersions
