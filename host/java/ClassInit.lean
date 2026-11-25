import Std
namespace Host.Java.ClassInit

/-- Serial authored fixture:0 fresh,1 initialized,2 erroneous. No in-progress,
    recursive,concurrent,OOM,superclass or arbitrary-loader behavior is modeled. -/
structure Decision where
  next : Nat
  code : Nat
  effect : Bool
  deriving DecidableEq, Repr
def initDecision (status target : Nat) (request : Bool) : Decision :=
  if !request then ⟨status,0,false⟩
  else if status == 1 then ⟨1,0,false⟩
  else if status == 2 then ⟨2,3,false⟩
  else if target == 1 then ⟨2,2,true⟩
  else if target == 2 then ⟨2,4,true⟩
  else ⟨1,0,true⟩

structure Cell where
  defined : Bool := false
  status : Nat := 0
  deriving DecidableEq, Repr
structure State where
  cells : List Cell := List.replicate 15 {}
  seen : List Nat := []
  good : Nat := 0
  bad : Nat := 0
  hard : Nat := 0
  array : Nat := 0
  findA : Nat := 0
  findB : Nat := 0
  deriving DecidableEq, Repr
structure Action where
  target : Nat
  loader : Nat
  request : Bool
  array : Bool
  deriving DecidableEq, Repr
structure Outcome where
  state : State
  code : Nat
  identity : Nat
  loader : Nat
  deriving DecidableEq, Repr

def descriptorKey (a : Action) : Nat := (a.loader*5+a.target)*2 + a.array.toNat
def updateCell : List Cell → Nat → Cell → List Cell
  | [],_,_ => []
  | _::tail,0,value => value::tail
  | head::tail,n+1,value => head::updateCell tail n value
def bumpFind (s : State) (loader : Nat) : State :=
  if loader == 1 then {s with findA := s.findA+1}
  else if loader == 2 then {s with findB := s.findB+1} else s
def bumpInit (s : State) (target : Nat) : State :=
  match target with
  | 0 => {s with good := s.good+1}
  | 1 => {s with bad := s.bad+1}
  | 2 => {s with hard := s.hard+1}
  | _ => {s with array := s.array+1}
def label (seen : List Nat) (key : Nat) : Nat := (seen.idxOf key)+1

/-- Defined caches affect only the authored child-first findClass implementation.
    No claim that arbitrary JVM class loading has no other effects. -/
def step (s : State) (a : Action) : Outcome :=
  let index := a.loader*5+a.target
  let cell := s.cells[index]?.getD {}
  let s := if a.loader != 0 && (!cell.defined || a.target == 4) then bumpFind s a.loader else s
  if a.target == 4 then ⟨s,1,0,0⟩ else
    let d := initDecision cell.status a.target (a.request && !a.array)
    let s := if d.effect then bumpInit s a.target else s
    let s := {s with cells := updateCell s.cells index ⟨true,d.next⟩}
    if d.code != 0 then ⟨s,d.code,0,0⟩ else
      let key := descriptorKey a
      let id := label s.seen key
      let seen := if s.seen.contains key then s.seen else s.seen++[key]
      ⟨{s with seen := seen},0,id,a.loader+1⟩

def fields (o : Outcome) : List Nat :=
  [o.code,(o.code == 0).toNat,o.identity,o.loader,(o.code == 1).toNat,(o.code == 1).toNat,
   o.state.good,o.state.bad,o.state.hard,o.state.array,o.state.findA,o.state.findB]
def trace : State → List Action → List (List Nat)
  | _,[] => []
  | s,a::rest => let result := step s a; fields result :: trace result.state rest

theorem no_request_preserves_disposition (status target : Nat) : initDecision status target false = ⟨status,0,false⟩ := rfl
theorem initialized_does_not_repeat_effects (target : Nat) : initDecision 1 target true = ⟨1,0,false⟩ := rfl
theorem erroneous_refuses_without_rerun (target : Nat) : initDecision 2 target true = ⟨2,3,false⟩ := rfl
theorem metadata_does_not_repair_erroneous : initDecision 2 1 false = ⟨2,0,false⟩ := rfl
theorem non_error_failure_is_wrapped : initDecision 0 1 true = ⟨2,2,true⟩ := rfl
theorem error_failure_is_not_wrapped : initDecision 0 2 true = ⟨2,4,true⟩ := rfl
theorem successful_initialization_is_effectful : initDecision 0 0 true = ⟨1,0,true⟩ := rfl
theorem array_descriptor_suppresses_component_init :
    (step {} ⟨3,0,true,true⟩).state.array = 0 := by decide
theorem default_lookup_runs_initializer : (step {} ⟨0,0,true,false⟩).state.good = 1 := by decide
theorem explicit_false_keeps_initializer_count : (step {} ⟨0,0,false,false⟩).state.good = 0 := by decide
theorem custom_false_still_calls_loader : (step {} ⟨0,1,false,false⟩).state.findA = 1 := by decide
theorem custom_false_keeps_initializer_count : (step {} ⟨0,1,false,false⟩).state.good = 0 := by decide
theorem missing_lookup_can_have_effects : (step {} ⟨4,1,false,false⟩).code = 1 ∧ (step {} ⟨4,1,false,false⟩).state.findA = 1 := by decide
theorem failed_initialization_keeps_prior_effect : (step {} ⟨1,0,true,false⟩).code = 2 ∧ (step {} ⟨1,0,true,false⟩).state.bad = 1 := by decide
theorem retry_is_a_different_failure :
    let first := step {} ⟨1,0,true,false⟩
    (step first.state ⟨1,0,true,false⟩).code = 3 ∧ (step first.state ⟨1,0,true,false⟩).state.bad = 1 := by decide
theorem initialized_once_per_loader :
    let first := step {} ⟨0,0,true,false⟩
    (step first.state ⟨0,0,true,false⟩).state.good = 1 := by decide
theorem different_loader_can_initialize_again :
    let first := step {} ⟨0,0,true,false⟩
    (step first.state ⟨0,1,true,false⟩).state.good = 2 := by decide
theorem same_name_different_loader_identity (target loaderA loaderB : Nat) (array : Bool) (different : loaderA ≠ loaderB) :
    descriptorKey ⟨target,loaderA,false,array⟩ ≠ descriptorKey ⟨target,loaderB,false,array⟩ := by
  simp only [descriptorKey]
  omega
theorem descriptor_does_not_prove_initialized : (step {} ⟨0,0,false,false⟩).code = 0 ∧ (step {} ⟨0,0,false,false⟩).state.good = 0 := by decide
theorem initialization_error_is_not_class_not_found : (fields (step {} ⟨1,0,true,false⟩))[4]? = some 0 := by decide
theorem initialization_error_escapes_exception_catch : (fields (step {} ⟨1,0,true,false⟩))[5]? = some 0 := by decide
theorem missing_class_matches_exception_catch : (fields (step {} ⟨4,0,true,false⟩))[5]? = some 1 := by decide

end Host.Java.ClassInit
