import Std
import host.java.CpuImage

namespace Host.Minecraft.SpriteInputs

/-- Explicit tiny FrameSize and original empty metadata only. The singleton
    frame label1 is preserved; it is not the backing-frame index. -/
def frameIds (masks : List Nat) : List Nat := if masks.length == 1 then [1] else [0, 1]

def backingMask (masks : List Nat) (frame : Nat) : Nat :=
  if masks.length == 1 then masks.headD 0 else masks[frame]!

def transparent (mask index : Nat) : Bool := (mask / 2 ^ index) % 2 == 0

structure Matrix where
  frame : Nat
  cells : List Bool
  deriving BEq, DecidableEq, Repr

def matrices (width height : Nat) (masks : List Nat) : List Matrix :=
  (frameIds masks).map fun frame =>
    ⟨frame, (List.range (width * height)).map (transparent (backingMask masks frame))⟩

/-- Source/observed identity coupling: the constructed sprite retains the input
    image. These alias helpers reuse the existing2x2 CPU model, not FFI memory. -/
def aliasBacking := Host.Java.CpuImage.initial
def aliasMutated := (Host.Java.CpuImage.step aliasBacking 2 1 1 0xffffffff).1
def aliasClosed := (Host.Java.CpuImage.step aliasMutated 3 0 0 0).1
def aliasFirstTransparent (s : Host.Java.CpuImage.State) : Bool :=
  s.words[0]!.toNat / 16777216 % 256 == 0
def aliasClosedAccess : Nat := (Host.Java.CpuImage.step aliasClosed 1 1 1 0).2.error

theorem singleton_label_is_one (mask : Nat) : frameIds [mask] = [1] := rfl
theorem singleton_ignores_frame_label (mask frame : Nat) : backingMask [mask] frame = mask := rfl
theorem two_frame_labels (a b : Nat) : frameIds [a, b] = [0, 1] := rfl
theorem first_two_frame_backing (a b : Nat) : backingMask [a, b] 0 = a := rfl
theorem second_two_frame_backing (a b : Nat) : backingMask [a, b] 1 = b := rfl
theorem zero_mask_transparent (index : Nat) : transparent 0 index = true := by simp [transparent]
theorem low_bit_is_parity (mask : Nat) : transparent mask 0 = (mask % 2 == 0) := by simp [transparent]
theorem matrix_keeps_cell_count (width height : Nat) (masks : List Nat) (frame : Nat) :
    ((List.range (width * height)).map (transparent (backingMask masks frame))).length = width * height := by simp
theorem solid2x2 : matrices 2 2 [15] = [⟨1, [false, false, false, false]⟩] := by decide
theorem two_masks_stay_distinct : matrices 2 2 [1, 8] =
    [⟨0, [false, true, true, true]⟩, ⟨1, [true, true, true, false]⟩] := by decide
theorem alias_write_changes_observation :
    aliasFirstTransparent aliasBacking = true ∧ aliasFirstTransparent aliasMutated = false := by decide
theorem sprite_close_revokes_alias_access : aliasClosedAccess = 2 := by decide
theorem closed_backing_metadata_survives : Host.Java.CpuImage.metadata aliasClosed = (2, 2) := rfl

end Host.Minecraft.SpriteInputs
