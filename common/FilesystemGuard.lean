import Std
namespace Host.FilesystemGuard

/-- Relation is0 unknown,1 overlap,2 separation established for the protected
    scope. Different IDs alone do not establish tree separation. -/
structure Evidence where
  policyAllows : Bool
  relation : Nat
  complete : Bool
  identityCurrent : Bool
  scopeMatches : Bool
  authority : Bool
  boundaryBound : Bool
  deriving Repr

/-- 0 policy refusal;1 needs evidence;2 conflict;3 preflight candidate. -/
def preflight (r : Evidence) : Nat :=
  if !r.policyAllows then 0
  else if !r.identityCurrent || !r.scopeMatches then 1
  else if r.relation == 1 then 2
  else if r.relation == 2 && r.complete then 3
  else 1
/-- Boundary binding is a separate owner-supplied protocol premise, not a
    conclusion of stat, path normalization, or preflight. No write executes here. -/
def mayMutate (r : Evidence) : Bool :=
  preflight r == 3 && r.authority && r.boundaryBound

theorem policy_refusal_needs_no_identity (r : Evidence) :
    preflight {r with policyAllows := false} = 0 := by simp [preflight]
theorem stale_requires_evidence (r : Evidence) :
    preflight {r with policyAllows := true,identityCurrent := false} = 1 := by simp [preflight]
theorem wrong_scope_requires_evidence (r : Evidence) :
    preflight {r with policyAllows := true,scopeMatches := false} = 1 := by simp [preflight]
theorem current_conflict_refuses (r : Evidence) :
    preflight {r with policyAllows := true,relation := 1,identityCurrent := true,scopeMatches := true} = 2 := by simp [preflight]
theorem conflict_does_not_need_complete_scan (r : Evidence) :
    preflight {r with policyAllows := true,relation := 1,complete := false,identityCurrent := true,scopeMatches := true} = 2 := by simp [preflight]
theorem unknown_is_not_separate (r : Evidence) :
    preflight {r with policyAllows := true,relation := 0,identityCurrent := true,scopeMatches := true} = 1 := by simp [preflight]
theorem incomplete_separation_is_unresolved (r : Evidence) :
    preflight {r with policyAllows := true,relation := 2,complete := false,identityCurrent := true,scopeMatches := true} = 1 := by simp [preflight]
theorem separated_preflight_is_candidate (r : Evidence) :
    preflight {r with policyAllows := true,relation := 2,complete := true,identityCurrent := true,scopeMatches := true} = 3 := by simp [preflight]
theorem no_authority_no_mutation (r : Evidence) : mayMutate {r with authority := false} = false := by simp [mayMutate]
theorem no_boundary_binding_no_mutation (r : Evidence) : mayMutate {r with boundaryBound := false} = false := by simp [mayMutate]
theorem mutation_requires_candidate (r : Evidence) (h : mayMutate r = true) : preflight r = 3 := by
  simpa using (Bool.and_eq_true_iff.mp (Bool.and_eq_true_iff.mp h).1).1
theorem mutation_requires_authority (r : Evidence) (h : mayMutate r = true) : r.authority = true := by
  exact (Bool.and_eq_true_iff.mp (Bool.and_eq_true_iff.mp h).1).2
theorem mutation_requires_boundary (r : Evidence) (h : mayMutate r = true) : r.boundaryBound = true := by
  exact (Bool.and_eq_true_iff.mp h).2
theorem preflight_is_not_mutation :
    preflight ⟨true,2,true,true,true,false,false⟩ = 3 ∧
    mayMutate ⟨true,2,true,true,true,false,false⟩ = false := by decide
end Host.FilesystemGuard
