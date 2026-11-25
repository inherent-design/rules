import Std
import host.java.Word32
namespace Host.Minecraft.Sounds
open Host.Java.Word32

/-- Authored callback profile:one value for the aggregate pass,one for traversal.
    Native SoundManager reference lookup and real file/engine work are external. -/
structure Entry where
  first : UInt32
  second : UInt32
  failPreload : Bool := false
  deriving Repr, DecidableEq
structure Outcome where
  weight : UInt32 := 0
  selected : Nat := 0
  fallback : Bool := false
  error : Nat := 0
  weightCalls : List Nat := []
  preloadCalls : List Nat := []
  randomBound : UInt32 := 0
  randomCalls : Nat := 0
  deriving Repr, DecidableEq
def sum (entries : List Entry) : UInt32 := entries.foldl (fun value entry => value+entry.first) 0
def traverse : List Entry → UInt32 → Nat → Nat × List Nat
  | [],_,_ => (0,[])
  | e::tail,index,ordinal =>
    let index := index-e.second
    if negative index then (ordinal,2::List.replicate tail.length 1)
    else let (selected,calls) := traverse tail index (ordinal+1);(selected,2::calls)
def preload : List Entry → Nat × List Nat
  | [] => (0,[])
  | e::tail => if e.failPreload then (2,1::List.replicate tail.length 0)
    else let (error,calls) := preload tail;(error,1::calls)
def run (operation : Nat) (entries : List Entry) (draw : UInt32) : Outcome :=
  if operation == 2 then
    let (error,calls) := preload entries
    {error := error,weightCalls := List.replicate entries.length 0,preloadCalls := calls}
  else
    let total := sum entries
    let base : Outcome := {weight := total,weightCalls := List.replicate entries.length 1,preloadCalls := List.replicate entries.length 0}
    if operation == 0 then base
    else if entries.isEmpty || total == 0 then {base with fallback := true}
    else if negative total then {base with error := 1,randomBound := total,randomCalls := 1}
    else let (selected,calls) := traverse entries draw 1
         {base with selected := selected,fallback := selected == 0,weightCalls := calls,randomBound := total,randomCalls := 1}
def fields (o : Outcome) : List Nat :=
  [o.weight.toNat,o.selected,o.fallback.toNat,o.error,o.randomBound.toNat,o.randomCalls]++o.weightCalls++o.preloadCalls

theorem empty_uses_fallback : (run 1 [] 0).fallback = true := by decide
theorem zero_weights_skip_random : (run 1 [⟨0,0,false⟩] 0).randomCalls = 0 := by decide
theorem positive_entries_can_wrap_to_invalid_bound :
    (run 1 [⟨2147483647,2147483647,false⟩,⟨1,1,false⟩] 0).error = 1 := by decide
theorem positive_entries_can_wrap_to_no_draw :
    (run 1 (List.replicate 4 ⟨1073741824,1073741824,false⟩) 0).randomCalls = 0 := by decide
theorem traversal_rereads_weights : (run 1 [⟨2,2,false⟩,⟨3,3,false⟩] 2).weightCalls = [2,2] := by decide
theorem selection_stops_later_rereads : (run 1 [⟨2,2,false⟩,⟨3,3,false⟩] 0).weightCalls = [2,1] := by decide
theorem changed_weights_can_reach_fallback : (run 1 [⟨3,0,false⟩,⟨2,0,false⟩] 0).fallback = true := by decide
theorem initially_zero_can_be_selected : (run 1 [⟨0,5,false⟩,⟨2,2,false⟩] 1).selected = 1 := by decide
theorem preload_includes_zero_weight : (run 2 [⟨0,0,false⟩,⟨2,2,false⟩] 0).preloadCalls = [1,1] := by decide
theorem preload_failure_keeps_earlier_effects :
    (run 2 [⟨1,1,false⟩,⟨2,2,true⟩,⟨3,3,false⟩] 0).preloadCalls = [1,1,0] := by decide
end Host.Minecraft.Sounds
