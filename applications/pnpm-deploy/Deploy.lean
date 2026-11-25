namespace ApplicationStudy.PnpmDeploy

structure RootDependency where
  target : Nat
  group : Nat
  deriving Repr, DecidableEq
structure Arc where
  owner : Nat
  target : Nat
  deriving Repr, DecidableEq

/-- Root groups: runtime=0, optional=1, development=2. Transitive arcs in
    this profile are ordinary runtime edges, with no peers or optional arcs. -/
def enabled (group : Nat) (production optional : Bool) : Bool :=
  if group == 0 then true else if group == 1 then optional else !production
def roots (dependencies : List RootDependency) (production optional : Bool) : List Nat :=
  (dependencies.filter fun edge => enabled edge.group production optional).map (·.target)
def step (nodes : Nat) (reached : List Nat) (edges : List Arc) : List Nat :=
  (List.range nodes).filter fun node => reached.contains node ||
    edges.any (fun edge => edge.target == node && reached.contains edge.owner)
def iterate (nodes : Nat) (edges : List Arc) : Nat → List Nat → List Nat
  | 0, reached => reached
  | fuel + 1, reached => iterate nodes edges fuel (step nodes reached edges)
def direct (nodes : Nat) (dependencies : List RootDependency) (production optional : Bool) : List Nat :=
  (List.range nodes).filter fun node => (roots dependencies production optional).contains node
def closure (nodes : Nat) (dependencies : List RootDependency) (edges : List Arc)
    (production optional : Bool) : List Nat :=
  iterate nodes edges nodes (0 :: roots dependencies production optional)

theorem runtime_group_always_kept (production optional : Bool) : enabled 0 production optional = true := rfl
theorem production_excludes_development (optional : Bool) : enabled 2 true optional = false := rfl
theorem optional_exclusion_is_separate (production : Bool) : enabled 1 production false = false := rfl
theorem default_keeps_development (optional : Bool) : enabled 2 false optional = true := rfl

def fixtureRoots : List RootDependency := [⟨1, 0⟩, ⟨3, 0⟩, ⟨4, 1⟩, ⟨5, 2⟩]
def fixtureEdges : List Arc := [⟨1, 2⟩]
theorem production_closure_keeps_optional : closure 6 fixtureRoots fixtureEdges true true = [0,1,2,3,4] := by decide
theorem no_optional_closure : closure 6 fixtureRoots fixtureEdges true false = [0,1,2,3] := by decide
theorem full_closure : closure 6 fixtureRoots fixtureEdges false true = [0,1,2,3,4,5] := by decide
theorem transitive_is_not_root_exposure :
    (closure 6 fixtureRoots fixtureEdges true true).contains 2 = true ∧
    (direct 6 fixtureRoots true true).contains 2 = false := by decide

/-- Study admission tags: nothing=1,many=2,unsafe=3,occupied=4.
    Already-admitted workspace/config and a valid packable package are premises.
    Unsafe includes root/ancestor and inspected workspace-child symlink relations. -/
def admit (selected : Nat) (unsafeTarget force inside unsafeLink occupied : Bool) : Nat :=
  if selected == 0 then 1
  else if selected > 1 then 2
  else if unsafeTarget || (force && !inside) || unsafeLink then 3
  else if occupied && !force then 4 else 0
structure Outcome where
  code : Nat
  payloadCopied : Bool
  priorRemoved : Bool
  commandSucceeded : Bool
  sourcePreserved : Bool
  deriving Repr, DecidableEq
/-- Closed native profile: selected payload was valid before preparation. An
    admitted forced target is cleared before the file copier reads its source.
    Source/target aliases can therefore leave a successful empty payload. -/
def finish (admission : Nat) (force occupied aliasesSource : Bool) (installAvailable : Option Bool) : Option Outcome :=
  if admission != 0 then some ⟨admission, false, false, false, true⟩
  else do
    let available ← installAvailable
    let removed := force && occupied
    let sourceLost := aliasesSource && removed
    return ⟨if available then 0 else 5, !sourceLost, removed, available, !sourceLost⟩

/-- Proposed admission, not a patched native implementation. This additional
    witness concerns actual protected filesystem relationships, not spelling. -/
def proposedAdmission (physicalConflict : Option Bool) (current : Nat) : Option Nat :=
  if current != 0 then some current
  else do
    let conflict ← physicalConflict
    return if conflict then 3 else 0

theorem empty_selection_refuses_first (unsafeTarget force inside link occupied : Bool) :
    admit 0 unsafeTarget force inside link occupied = 1 := rfl
theorem force_outside_is_not_permission : admit 1 false true false false true = 3 := rfl
theorem new_outside_without_force_can_be_admitted : admit 1 false false false false false = 0 := rfl
theorem occupied_requires_force : admit 1 false false true false true = 4 := rfl
theorem unsafe_even_with_force : admit 1 true true true false true = 3 := rfl
theorem blocked_before_copy (force occupied aliases : Bool) (available : Option Bool) :
    finish 3 force occupied aliases available = some ⟨3, false, false, false, true⟩ := rfl
theorem later_failure_keeps_partial_effects : finish 0 true true false (some false) = some ⟨5, true, true, false, true⟩ := rfl
theorem lexical_admission_is_not_source_protection :
    finish 0 true true true (some true) = some ⟨0, false, true, true, false⟩ := rfl
theorem needed_install_unknown_is_not_success : finish 0 false false false none = none := rfl
theorem unknown_physical_relation_is_not_distinct : proposedAdmission none 0 = none := rfl
theorem protected_alias_refused : proposedAdmission (some true) 0 = some 3 := rfl
theorem known_refusal_needs_no_physical_observation : proposedAdmission none 3 = some 3 := rfl

end ApplicationStudy.PnpmDeploy
