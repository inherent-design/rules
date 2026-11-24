namespace ApplicationStudy.EmpackJava

structure Policy where
  historical : Option Nat
  minimum : Nat
  supported : Option (List Nat)
  deriving BEq, Repr

structure Profile where
  game : String
  historical : Nat
  supported : List Nat
  deriving Repr

def forGame (profiles : List Profile) (game : String) : Policy :=
  match profiles.find? (fun p => p.game == game) with
  | none => ⟨none, 8, none⟩
  | some p => ⟨some p.historical, max 8 p.historical, some p.supported⟩

def recommended (p : Policy) : Option Nat := p.supported.bind List.getLast?

structure Bound where
  minimum : Nat
  maximum : Option Nat
  deriving Repr

def constrain (p : Policy) (bound : Bound) : Option Policy :=
  let minimum := max p.minimum bound.minimum
  if bound.maximum.any (fun n => n < minimum) then none else
  match p.supported with
  | none => if bound.maximum.isSome then none else some {p with minimum := minimum}
  | some values =>
    let narrowed := values.filter (fun n => minimum ≤ n && bound.maximum.all (fun m => n ≤ m))
    if narrowed.isEmpty then none else some {p with minimum := minimum, supported := some narrowed}

/-- Failed constraints retain the last successful policy; this is the research
    caller's observation of a nonmutating API, not a serialized engine outcome. -/
def constrained (p : Policy) : List Bound → Bool × Policy
  | [] => (true, p)
  | bound :: rest => match constrain p bound with
    | none => (false, p)
    | some next => constrained next rest

def select (p : Policy) (preferred : Option Nat) : Option Nat :=
  let candidate := preferred.orElse (fun _ => recommended p)
  candidate.filter (fun major => major ≥ p.minimum && p.supported.all (fun values => values.contains major))

def actual (p : Policy) (preferred observed : Nat) : Bool :=
  (select p (some preferred)).isSome &&
  (p.supported.isSome || observed == preferred) && (select p (some observed)).isSome

structure Outcome where
  policy : Policy
  stage : String
  selected : Option Nat
  deriving BEq, Repr

def evaluate (base : Policy) (bounds : List Bound) (preferred observed : Option Nat) : Outcome :=
  let (ok, policy) := constrained base bounds
  if !ok then ⟨policy, "constraint", none⟩ else
  match observed with
  | some observed =>
    if preferred.any (fun p => actual policy p observed) then ⟨policy, "ok", some observed⟩
    else ⟨policy, "actual", none⟩
  | none => match select policy preferred with
    | some chosen => ⟨policy, "ok", some chosen⟩
    | none => ⟨policy, "selection", none⟩

def transitional : Policy := ⟨some 16, 16, some [16,17]⟩
def unknown : Policy := ⟨none, 8, none⟩

theorem preferred_is_not_an_exact_execution_requirement : actual transitional 17 16 = true := rfl
theorem lower_preference_does_not_lower_recommendation :
    select transitional (some 16) = some 16 ∧ recommended transitional = some 17 := by constructor <;> rfl
theorem unknown_needs_explicit_selection : select unknown none = none := rfl
theorem unknown_can_preserve_unqualified_selection : select unknown (some 21) = some 21 := rfl
theorem unknown_does_not_admit_newer_actual : actual unknown 21 25 = false := rfl
theorem invalid_preference_is_not_fixed_by_actual : actual transitional 21 17 = false := rfl
theorem historical_minimum_does_not_remove_execution_floor :
    (forGame [⟨"old",5,[8]⟩] "old").minimum = 8 := rfl
theorem unlisted_exact_game_stays_unknown :
    forGame [⟨"1.17.1",16,[16,17]⟩] "1.17.99" = unknown := rfl
theorem upper_constraint_can_lower_recommendation :
    (constrain transitional ⟨0,some 16⟩).bind recommended = some 16 := rfl
theorem empty_intersection_is_refused : constrain transitional ⟨18,none⟩ = none := rfl
theorem unknown_upper_cannot_establish_support : constrain unknown ⟨17,some 25⟩ = none := rfl
theorem narrowed_policy_does_not_silently_replace_preference :
    (evaluate transitional [⟨17,none⟩] (some 16) none).stage = "selection" := rfl
theorem constraint_failure_retains_last_successful_value :
    (evaluate transitional [⟨0,some 16⟩,⟨17,none⟩] none none).policy.supported = some [16] := rfl

end ApplicationStudy.EmpackJava
