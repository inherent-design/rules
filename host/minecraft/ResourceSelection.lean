import Std

namespace MinecraftHost.ResourceSelection

/-- Generated-file scope: body 0 absent; nonzero values identify bytes.
    Metadata 0 absent,1 blur,2 clamp,3 malformed. Filter matches are premises. -/
structure Pack where
  id : Nat
  body : Nat
  metadata : Nat
  blocksBody : Bool
  blocksMetadata : Bool
  deriving DecidableEq, BEq, Repr

structure Resource where
  source : Nat
  body : Nat
  metadata : Nat
  deriving DecidableEq, BEq, Repr

/-- Some 0 is a metadata filter boundary, different from not finding one yet. -/
def chooseMetadata (pending : Option Nat) (p : Pack) : Option Nat :=
  if pending.isSome then pending
  else if p.metadata != 0 then some p.metadata
  else if p.blocksMetadata then some 0
  else none

/-- Input is ordered highest to lowest. Metadata search stops at the winning
    file's floor; a pack's own bytes are considered before its body filter. -/
def singleHigh : List Pack → Option Nat → Option Resource
  | [], _ => none
  | p::ps, pending =>
    let next := chooseMetadata pending p
    if p.body != 0 then some ⟨p.id,p.body,next.getD 0⟩
    else if p.blocksBody then none
    else singleHigh ps next

/-- Stack metadata belongs to each file's own pack, unless a higher metadata
    filter blocks it. A higher metadata file alone does not replace it. -/
def stackHigh : List Pack → Bool → List Resource
  | [], _ => []
  | p::ps, blocked =>
    let own := if p.body == 0 then [] else [⟨p.id,p.body,if blocked then 0 else p.metadata⟩]
    let tail := if p.blocksBody then [] else stackHigh ps (blocked || p.blocksMetadata)
    own ++ tail

def single (lowToHigh : List Pack) (pathAdmitted : Bool := true) : Option Resource :=
  if pathAdmitted then singleHigh lowToHigh.reverse none else none
def stack (lowToHigh : List Pack) (pathAdmitted : Bool := true) : List Resource :=
  if pathAdmitted then (stackHigh lowToHigh.reverse false).reverse else []

def low : Pack := ⟨1,1,1,false,false⟩
def high : Pack := ⟨2,2,2,false,false⟩

theorem no_pack_no_resource : single [] = none ∧ stack [] = [] := by decide
theorem last_pack_wins : single [low,high] = some ⟨2,2,2⟩ := by decide
theorem reverse_order_changes_winner : single [high,low] = some ⟨1,1,1⟩ := by decide
theorem stack_preserves_low_to_high_order : stack [low,high] = [⟨1,1,1⟩,⟨2,2,2⟩] := by decide
theorem higher_metadata_only_changes_single :
    single [low,{high with body := 0}] = some ⟨1,1,2⟩ ∧
    stack [low,{high with body := 0}] = [⟨1,1,1⟩] := by decide
theorem metadata_below_winning_file_is_not_used :
    single [low,{high with metadata := 0}] = some ⟨2,2,0⟩ := by decide
theorem filter_only_pack_removes_lower_body :
    single [low,⟨2,0,0,true,false⟩] = none ∧ stack [low,⟨2,0,0,true,false⟩] = [] := by decide
theorem own_body_precedes_own_filter :
    single [low,{high with blocksBody := true}] = some ⟨2,2,2⟩ := by decide
theorem body_filter_stops_lower_stack :
    stack [low,{high with blocksBody := true}] = [⟨2,2,2⟩] := by decide
theorem metadata_filter_keeps_body :
    single [low,⟨2,0,0,false,true⟩] = some ⟨1,1,0⟩ ∧
    stack [low,⟨2,0,0,false,true⟩] = [⟨1,1,0⟩] := by decide
theorem own_metadata_precedes_own_filter_in_single :
    single [low,⟨2,0,2,false,true⟩] = some ⟨1,1,2⟩ ∧
    stack [low,⟨2,0,2,false,true⟩] = [⟨1,1,0⟩] := by decide
theorem malformed_higher_metadata_is_not_fallback :
    single [low,⟨2,0,3,false,false⟩] = some ⟨1,1,3⟩ := by decide
theorem invalid_selected_bytes_still_win_lookup :
    single [low,{high with body := 3}] = some ⟨2,3,2⟩ := by decide
theorem rejected_physical_path_yields_no_file (packs : List Pack) :
    single packs false = none ∧ stack packs false = [] := by simp [single,stack]
theorem sealed_metadata_stays_sealed (p : Pack) : chooseMetadata (some 0) p = some 0 := rfl
theorem prior_metadata_stays_selected (p : Pack) (n : Nat) : chooseMetadata (some n) p = some n := rfl
theorem later_metadata_failure_preserves_selected_file :
    (single [low,⟨2,0,3,false,false⟩]).map Resource.body = some 1 := by decide
end MinecraftHost.ResourceSelection
