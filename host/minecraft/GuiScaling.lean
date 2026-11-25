import host.java.Word32
namespace Host.Minecraft.GuiScaling
open Host.Java.Word32

/-- The selected integer corpus. Negative border facts remain explicit; numeric JSON,
    arbitrary constructors and downstream drawing are separate contracts. -/
structure Input where
  kind : Nat
  width : Nat
  height : Nat
  left : Nat
  top : Nat
  right : Nat
  bottom : Nat
  nonnegative : Bool
  scalar : Bool
  modern : Bool
  stretch : Bool
  deriving Repr
def beforeDimension (a b dim : Nat) : Bool :=
  signed (UInt32.ofNat a + UInt32.ofNat b) < Int.ofNat dim
def accepts (r : Input) : Bool :=
  if r.kind == 0 then true
  else if r.kind == 1 then 0 < r.width && 0 < r.height
  else if r.kind == 2 then
    0 < r.width && 0 < r.height && r.nonnegative && (!r.scalar || 0 < r.left) &&
    beforeDimension r.left r.right r.width && beforeDimension r.top r.bottom r.height
  else false
/-- 0 refusal;1 stretch;2 tile;3 old nine-slice;4 modern false;5 modern true. -/
def evaluate (r : Input) : Nat :=
  if !accepts r then 0
  else if r.kind == 0 then 1
  else if r.kind == 1 then 2
  else if !r.modern then 3
  else if r.stretch then 5 else 4
def sample : Input := ⟨2,8,8,1,1,1,1,true,true,false,false⟩
theorem normal_nine_slice : evaluate sample = 3 := by decide
theorem modern_false : evaluate {sample with modern := true} = 4 := by decide
theorem modern_true : evaluate {sample with modern := true, stretch := true} = 5 := by decide
theorem old_ignores_stretch : evaluate {sample with stretch := true} = 3 := by decide
theorem stretch_ignores_dimensions : evaluate {sample with kind := 0,width := 0,height := 0} = 1 := by decide
theorem tile_zero_width : evaluate {sample with kind := 1,width := 0} = 0 := by decide
theorem tile_zero_height : evaluate {sample with kind := 1,height := 0} = 0 := by decide
theorem scalar_zero_refused : evaluate {sample with left := 0,right := 0,top := 0,bottom := 0} = 0 := by decide
theorem record_zero_accepted :
    evaluate {sample with left := 0,right := 0,top := 0,bottom := 0,scalar := false} = 3 := by decide
theorem no_center_refused : evaluate {sample with left := 4,right := 4} = 0 := by decide
theorem negative_border_refused : evaluate {sample with nonnegative := false} = 0 := by decide
theorem horizontal_sum_wraps : beforeDimension 2147483647 1 8 = true := by decide
theorem two_max_sum_wraps : beforeDimension 2147483647 2147483647 8 = true := by decide
theorem overflow_can_pass : evaluate {sample with left := 2147483647,right := 1,scalar := false} = 3 := by decide
theorem natural_center_is_not_required_by_this_guard :
    accepts {sample with left := 2147483647,right := 1,scalar := false} = true ∧
    ¬ (2147483647 + 1 < (8 : Nat)) := by decide
end Host.Minecraft.GuiScaling
