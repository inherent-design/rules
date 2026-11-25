import Base

# Relation0 unknown,1 overlap,2 established separation of the protected scope.
def fs_preflight(policy: Bool,+relation: Nat,complete: Bool,current: Bool,scope: Bool) -> Nat:
  Bool.pick(Nat,policy,
    Bool.pick(Nat,Bool.and(current,scope),
      Bool.pick(Nat,Nat.is_eq(relation,1n),2n,Bool.pick(Nat,Bool.and(Nat.is_eq(relation,2n),complete),3n,1n)),1n),0n)
def fs_may_mutate(policy: Bool,relation: Nat,complete: Bool,current: Bool,scope: Bool,authority: Bool,boundary: Bool) -> Bool:
  Bool.and(Nat.is_eq(fs_preflight(policy,relation,complete,current,scope),3n),Bool.and(authority,boundary))

law fs_policy_refusal:
  for relation: Nat
  for complete: Bool
  for current: Bool
  for scope: Bool
  {fs_preflight(False{},relation,complete,current,scope) == 0n : Nat}
def fs_policy_refusal(relation,complete,current,scope):
  {==}
law fs_stale_requires_evidence:
  for relation: Nat
  for complete: Bool
  for scope: Bool
  {fs_preflight(True{},relation,complete,False{},scope) == 1n : Nat}
def fs_stale_requires_evidence(relation,complete,scope):
  {==}
law fs_scope_requires_evidence:
  for relation: Nat
  for complete: Bool
  {fs_preflight(True{},relation,complete,True{},False{}) == 1n : Nat}
def fs_scope_requires_evidence(relation,complete):
  {==}
law fs_conflict_refuses_without_complete_scan:
  {fs_preflight(True{},1n,False{},True{},True{}) == 2n : Nat}
def fs_conflict_refuses_without_complete_scan():
  {==}
law fs_unknown_unresolved:
  {fs_preflight(True{},0n,True{},True{},True{}) == 1n : Nat}
def fs_unknown_unresolved():
  {==}
law fs_partial_separation_unresolved:
  {fs_preflight(True{},2n,False{},True{},True{}) == 1n : Nat}
def fs_partial_separation_unresolved():
  {==}
law fs_preflight_candidate:
  {fs_preflight(True{},2n,True{},True{},True{}) == 3n : Nat}
def fs_preflight_candidate():
  {==}
law fs_candidate_without_boundary_cannot_mutate:
  {fs_may_mutate(True{},2n,True{},True{},True{},True{},False{}) == False{} : Bool}
def fs_candidate_without_boundary_cannot_mutate():
  {==}
law fs_candidate_without_authority_cannot_mutate:
  {fs_may_mutate(True{},2n,True{},True{},True{},False{},True{}) == False{} : Bool}
def fs_candidate_without_authority_cannot_mutate():
  {==}
