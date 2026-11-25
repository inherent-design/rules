import Std

namespace MinecraftHost.Polytone.Priority

/-- Rank is Java signed int priority shifted by 2^31,not a pack-stack rank. -/
structure Entry where
  key : Nat
  enabled : Bool
  rank : Nat
  marker : Nat
  deriving DecidableEq, BEq, Repr

def replaces (old candidate : Entry) : Bool := candidate.enabled && old.rank < candidate.rank

def put : List Entry → Entry → List Entry
  | [],candidate => [candidate]
  | old::rest,candidate =>
    if old.key == candidate.key then
      (if replaces old candidate then candidate else old)::rest
    else old::put rest candidate

def replacement (entries : List Entry) (candidate : Entry) : Bool :=
  ((entries.find? (fun old => old.key == candidate.key)).map (fun old => replaces old candidate)).getD false

structure State where
  entries : List Entry
  warnings : Nat
  deriving DecidableEq, BEq, Repr

def step (s : State) (candidate : Entry) : State :=
  ⟨put s.entries candidate,s.warnings + (if replacement s.entries candidate then 1 else 0)⟩
def run (entries : List Entry) : State := entries.foldl step ⟨[],0⟩

def orderedInsert (entry : Entry) : List Entry → List Entry
  | [] => [entry]
  | head::rest => if entry.rank ≤ head.rank then entry::head::rest else head::orderedInsert entry rest
def ordered : List Entry → List Entry
  | [] => []
  | head::rest => orderedInsert head (ordered rest)

def javaRank (priority : Int) : Nat := (priority+2147483648).toNat
theorem signed_priority_order_preserved (a b : Int)
    (aLower : -2147483648 ≤ a) (bLower : -2147483648 ≤ b) :
    javaRank a < javaRank b ↔ a < b := by
  unfold javaRank
  omega
theorem first_disabled_is_retained (key rank marker : Nat) :
    put [] ⟨key,false,rank,marker⟩ = [⟨key,false,rank,marker⟩] := rfl
theorem absent_is_not_a_low_priority_entry (entry : Entry) : put [] entry = [entry] := rfl
theorem incoming_disabled_cannot_replace (old : Entry) (rank marker : Nat) :
    put [old] ⟨old.key,false,rank,marker⟩ = [old] := by simp [put,replaces]
theorem equal_priority_preserves_existing (old : Entry) (enabled : Bool) (marker : Nat) :
    put [old] ⟨old.key,enabled,old.rank,marker⟩ = [old] := by simp [put,replaces]
theorem higher_enabled_replaces (old : Entry) (rank marker : Nat) (higher : old.rank < rank) :
    put [old] ⟨old.key,true,rank,marker⟩ = [⟨old.key,true,rank,marker⟩] := by simp [put,replaces,higher]
theorem old_enablement_is_not_replacement_authority (old : Entry) (enabled : Bool) (candidate : Entry) :
    replaces {old with enabled := enabled} candidate = replaces old candidate := rfl
theorem disabled_higher_priority_can_remain :
    put [⟨0,false,2,1⟩] ⟨0,true,1,2⟩ = [⟨0,false,2,1⟩] := by decide
theorem priority_sort_differs_from_insertion :
    ordered [⟨0,true,2,1⟩,⟨1,true,0,2⟩] = [⟨1,true,0,2⟩,⟨0,true,2,1⟩] := by decide
theorem ties_preserve_input_order (a b : Entry) (equal : a.rank = b.rank) :
    ordered [a,b] = [a,b] := by simp [ordered,orderedInsert,equal]
theorem replacement_keeps_insertion_position :
    (run [⟨0,true,0,1⟩,⟨1,true,2,2⟩,⟨0,true,2,3⟩]).entries = [⟨0,true,2,3⟩,⟨1,true,2,2⟩] := by decide
theorem only_replacement_warns :
    (run [⟨0,true,0,1⟩,⟨0,false,2,2⟩,⟨0,true,0,3⟩,⟨0,true,1,4⟩]).warnings = 1 := by decide

end MinecraftHost.Polytone.Priority
