namespace ApplicationStudy.VscodeFileSystems

/-- One serialized registration event for its own scheme. The removal producer
    retains the historical provider object. This is not an RPC ordering proof. -/
structure Registration where
  added : Bool
  providerPresent : Bool
  readonly : Bool
  deriving Repr

/-- 0 = unknown, 1 = read-only, 2 = writable. Capability knowledge is not a
    permission grant or proof that a current provider exists. -/
def currentKnowledge (e : Registration) : Nat :=
  if e.providerPresent then (if e.readonly then 1 else 2) else 0

/-- Proposed bridge change; downstream map/query methods remain unchanged. -/
def proposedKnowledge (e : Registration) : Nat :=
  if e.added then currentKnowledge e else 0

theorem current_removal_retains_writable :
    currentKnowledge ⟨false, true, false⟩ = 2 := rfl
theorem current_removal_retains_readonly :
    currentKnowledge ⟨false, true, true⟩ = 1 := rfl
theorem proposed_removal_clears (present ro : Bool) :
    proposedKnowledge ⟨false, present, ro⟩ = 0 := rfl
theorem additions_unchanged (present ro : Bool) :
    proposedKnowledge ⟨true, present, ro⟩ = currentKnowledge ⟨true, present, ro⟩ := rfl

/-- Ordinary local provider shortcut in this fixture: activation succeeds,
    missing parents can be created, and the callback either accepts or refuses.
    No cancellation, OS permissions, transport, or failure inside mkdirp modeled. -/
structure WriteRequest where
  schemeReadonly : Bool
  backendDenied : Bool
  parentMissing : Bool
  deriving Repr

def reachesCallback (w : WriteRequest) : Bool := !w.schemeReadonly
def refused (w : WriteRequest) : Bool := w.schemeReadonly || w.backendDenied
def createsParent (w : WriteRequest) : Bool := !w.schemeReadonly && w.parentMissing

theorem scheme_readonly_blocks_callback (deny parent : Bool) :
    reachesCallback ⟨true, deny, parent⟩ = false := rfl
theorem backend_refusal_is_not_effect_free :
    refused ⟨false, true, true⟩ = true ∧ createsParent ⟨false, true, true⟩ = true := by decide
theorem backend_is_independent_authority :
    reachesCallback ⟨false, true, false⟩ = true ∧ refused ⟨false, true, false⟩ = true := by decide

/-- Caller mutates its original buffer before queued dispatch. Copying before
    submission retains a distinct buffer; the API shortcut itself borrows. -/
def dispatchSeesMutation (copied mutated : Bool) : Bool := !copied && mutated
theorem caller_copy_preserves_input (mutated : Bool) :
    dispatchSeesMutation true mutated = false := rfl
theorem borrowed_input_is_not_snapshot : dispatchSeesMutation false true = true := rfl

/-- The shortcut captures a provider before waiting. Rebinding a URI scheme
    changes new lookups, not that captured target. IDs are fixture identities. -/
def completionTarget (captured _current : Nat) : Nat := captured
theorem completion_keeps_provider (captured current : Nat) :
    completionTarget captured current = captured := rfl

end ApplicationStudy.VscodeFileSystems
