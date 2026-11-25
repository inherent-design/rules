import Std
namespace Host.Minecraft.SpriteSet

/-- Opaque identities only. No sprite pixels, lifetime, renderer or class allocation. -/
structure State where
  bound : List Nat := []
  boundKnown : Bool := false
  input : List Nat := []
  inputKnown : Bool := false
  deriving Repr, DecidableEq
structure Action where
  kind : Nat
  values : List Nat := []
  index : Int := 0
  max : Int := 1
  value : Nat := 0
  deriving Repr, DecidableEq
structure Outcome where
  state : State
  code : Nat := 0
  selected : Nat := 0
  deriving Repr, DecidableEq
def trunc (a b : Int) : Int :=
  let q := Int.ofNat (a.natAbs / b.natAbs)
  if (a < 0) != (b < 0) then -q else q
def choice (s : State) (index max : Int) (first : Bool) : Nat × Nat :=
  if !s.boundKnown then (1,0)
  else if first then
    match s.bound with
    | [] => (4,0)
    | x::_ => (0,x)
  else if max == 0 then (2,0)
  else
    let selected := trunc (index * (Int.ofNat s.bound.length - 1)) max
    if selected < 0 || selected ≥ Int.ofNat s.bound.length then (3,0)
    else (0,s.bound[selected.toNat]?.getD 0)
def step (s : State) (a : Action) : Outcome :=
  if a.kind == 0 then
    let next := {s with input := a.values, inputKnown := true}
    if a.values.contains 0 then ⟨next,1,0⟩
    else ⟨{next with bound := a.values, boundKnown := true},0,0⟩
  else if a.kind == 1 then ⟨{s with input := [], inputKnown := false},1,0⟩
  else if a.kind == 2 then ⟨{s with input := s.input.set a.index.toNat a.value},0,0⟩
  else let (code,selected) := choice s a.index a.max (a.kind == 4)
       ⟨s,code,selected⟩
def fields (o : Outcome) : List Nat :=
  [o.code,o.selected,o.state.boundKnown.toNat,o.state.bound.length,o.state.inputKnown.toNat,o.state.input.length] ++
  o.state.bound ++ [9] ++ o.state.input
def trace : State → List Action → List (List Nat)
  | _,[] => []
  | s,a::tail => let o := step s a; fields o :: trace o.state tail

theorem read_preserves_state (s : State) (index max : Int) :
    (step s ⟨3,[],index,max,0⟩).state = s := by rfl
theorem first_preserves_state (s : State) : (step s ⟨4,[],0,1,0⟩).state = s := by rfl
theorem input_mutation_preserves_binding (s : State) (i : Int) (v : Nat) :
    (step s ⟨2,[],i,1,v⟩).state.bound = s.bound := by rfl
theorem null_bind_preserves_binding (s : State) : (step s ⟨1,[],0,1,0⟩).state.bound = s.bound := by rfl
theorem bind_null_element_preserves_binding (s : State) :
    (step s ⟨0,[1,0],0,1,0⟩).state.bound = s.bound := by rfl
theorem unbound_read_refuses : (choice {} 0 1 false).1 = 1 := by decide
theorem empty_bind_is_admitted : (step {} ⟨0,[],0,1,0⟩).state.boundKnown = true := by decide
theorem empty_first_refuses : choice ⟨[],true,[],true⟩ 0 1 true = (4,0) := by decide
theorem zero_denominator_refuses : choice ⟨[1],true,[],false⟩ 0 0 false = (2,0) := by decide
theorem negative_fraction_truncates_to_zero : trunc (-2) 3 = 0 := by decide
theorem negative_fraction_can_select_first : choice ⟨[1,2,3],true,[],false⟩ (-1) 3 false = (0,1) := by decide
theorem duplicates_are_retained : (step {} ⟨0,[1,1],0,1,0⟩).state.bound = [1,1] := by decide
theorem singleton_ignores_finite_frame_when_denominator_nonzero :
    choice ⟨[3],true,[],false⟩ (-3) 1 false = (0,3) := by decide
end Host.Minecraft.SpriteSet
