import Std
namespace Host.Minecraft.Atlas

/-- Two generated keys and three authored supplier identities. No pixels, resource
    parsing, GPU objects, or HashMap iteration-order guarantee. -/
structure Action where
  kind : Nat
  key : Nat
  supplier : Nat
  caught : Bool
  deriving DecidableEq, Repr
structure State where
  slots : List Nat := [0,0]
  created : List Bool := [false,false,false]
  discards : List Nat := [0,0,0]
  runs : Nat := 0
  catches : Nat := 0
  error : Nat := 0
  deriving DecidableEq, Repr
def replace : List α → Nat → α → List α
  | [],_,_ => []
  | _::tail,0,value => value::tail
  | head::tail,index+1,value => head::replace tail index value
def discard (s : State) (supplier throwing : Nat) : State :=
  if supplier == 0 then s else
    {s with discards := replace s.discards (supplier-1) (s.discards[supplier-1]!.succ),
            error := if supplier == throwing then supplier+1 else 0}
def add (s : State) (key supplier throwing : Nat) : State :=
  let old := s.slots[key]!
  let s := {s with slots := replace s.slots key supplier,created := replace s.created (supplier-1) true}
  discard s old throwing
def removeAt (s : State) (key throwing : Nat) : State :=
  let s := discard s s.slots[key]! throwing
  if s.error != 0 then s else {s with slots := replace s.slots key 0}
def selectsKey (selection key : Nat) : Bool := selection == 1 || (selection == 2 && key == 0)
def remove (s : State) (selection throwing : Nat) : State :=
  let s := if selectsKey selection 0 then removeAt s 0 throwing else s
  if s.error != 0 then s else if selectsKey selection 1 then removeAt s 1 throwing else s
def rawStep (s : State) (a : Action) (throwing : Nat) : State :=
  if s.error != 0 then s else
    match a.kind with
    | 0 => add s a.key a.supplier throwing
    | 1 => remove s a.key throwing
    | _ => {s with error := 1}
def step (s : State) (a : Action) (throwing : Nat) : State :=
  let s := rawStep s a throwing
  if a.caught && s.error != 0 then {s with error := 0,catches := s.catches+1} else s
def actions : State → List Action → Nat → State
  | s,[],_ => s
  | s,a::tail,throwing => if s.error != 0 then s else actions (step s a throwing) tail throwing
def sources : State → List (List Action) → Nat → State
  | s,[],_ => s
  | s,head::tail,throwing =>
    if s.error != 0 then s else sources (actions {s with runs := s.runs+1} head throwing) tail throwing
def count (slots : List Nat) (supplier : Nat) : Nat := (slots.filter (· == supplier)).length
def fields (s : State) : List Nat :=
  let retained := if s.error == 0 then s.slots else []
  [(s.error == 0).toNat,(s.error == 0).toNat,count retained 1,count retained 2,count retained 3] ++
  s.created.map Bool.toNat ++ s.discards ++ [s.runs,s.catches,s.error]

/-- Throwing multi-target removal is refused: native map iteration order can choose
    which other callbacks happen first. Nonthrowing counts are order-independent. -/
def safeAction (s : State) (a : Action) (throwing : Nat) : Bool :=
  let targets := (s.slots.zipIdx.filter (fun (supplier,key) => supplier != 0 && selectsKey a.key key)).map Prod.fst
  !(a.kind == 1 && throwing != 0 && targets.contains throwing && targets.length > 1)
def safeActions : State → List Action → Nat → Bool
  | _,[],_ => true
  | s,a::tail,throwing => s.error != 0 || (safeAction s a throwing && safeActions (step s a throwing) tail throwing)
def safeSources : State → List (List Action) → Nat → Bool
  | _,[],_ => true
  | s,head::tail,throwing => s.error != 0 ||
    (safeActions s head throwing && safeSources (actions s head throwing) tail throwing)

theorem empty_has_only_default : fields {} = [1,1,0,0,0,0,0,0,0,0,0,0,0,0] := by decide
theorem discard_preserves_slots (s : State) (supplier throwing : Nat) :
    (discard s supplier throwing).slots = s.slots := by simp only [discard];split <;> rfl
theorem failed_raw_step_is_ignored (s : State) (a : Action) (throwing : Nat) (h : s.error ≠ 0) :
    rawStep s a throwing = s := by simp [rawStep,h]
theorem first_add_does_not_discard : (add {} 0 1 0).discards = [0,0,0] := by decide
theorem replacement_discards_previous : (add (add {} 0 1 0) 0 2 0).discards = [1,0,0] := by decide
theorem replacement_keeps_new_slot : (add (add {} 0 1 0) 0 2 0).slots = [2,0] := by decide
theorem failed_discard_does_not_undo_put : (add (add {} 0 1 0) 0 2 1).slots = [2,0] := by decide
theorem failed_discard_keeps_its_effect : (add (add {} 0 1 0) 0 2 1).discards = [1,0,0] := by decide
theorem failed_remove_keeps_slot : (removeAt (add {} 0 1 0) 0 1).slots = [1,0] := by decide
theorem successful_remove_clears_slot : (removeAt (add {} 0 1 0) 0 0).slots = [0,0] := by decide
theorem same_supplier_can_be_discarded_and_retained :
    (add (add {} 0 1 0) 0 1 0).slots = [1,0] ∧ (add (add {} 0 1 0) 0 1 0).discards = [1,0,0] := by decide
theorem shared_supplier_survives_other_replacement :
    (add (add (add {} 0 1 0) 1 1 0) 0 2 0).slots = [2,1] := by decide
theorem failure_stops_later_sources :
    (sources {} [[⟨0,0,1,false⟩,⟨2,0,0,false⟩],[⟨0,0,2,false⟩]] 0).runs = 1 := by decide
theorem failure_does_not_discard_every_candidate :
    (sources {} [[⟨0,0,1,false⟩,⟨2,0,0,false⟩]] 0).discards = [0,0,0] := by decide
theorem ambiguous_throwing_removal_refuses :
    safeAction (add (add {} 0 1 0) 1 3 0) ⟨1,1,0,false⟩ 1 = false := by decide
theorem nonthrowing_removal_is_admitted :
    safeAction (add (add {} 0 1 0) 1 3 0) ⟨1,1,0,false⟩ 0 = true := by decide
end Host.Minecraft.Atlas
