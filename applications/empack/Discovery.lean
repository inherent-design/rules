namespace ApplicationStudy.EmpackDiscovery

/-- Distinct fixture byte identities matching all declared assertions.
    These IDs are independently checked test-vector labels, not cryptographic proofs. -/
structure Request where
  entries : Nat
  limit : Nat
  matching : List Nat
  explicit : Option Nat
  explicitMatches : Bool
  deriving Repr, DecidableEq
inductive Decision where
  | missing
  | ambiguous
  | limit
  | selected (content : Nat)
  | explicitMismatch
  deriving Repr, DecidableEq

def choose (r : Request) : Decision :=
  match r.explicit with
  | some content => if r.explicitMatches then .selected content else .explicitMismatch
  | none =>
    if r.entries > r.limit then .limit
    else match r.matching.eraseDups with
      | [] => .missing
      | [content] => .selected content
      | _ => .ambiguous

def published : Decision → Bool
  | .selected _ => true
  | _ => false
def exitCode (d : Decision) : Nat := if published d then 0 else 1

theorem explicit_matches_select (r : Request) (n : Nat) (s : r.explicit = some n)
    (m : r.explicitMatches = true) : choose r = .selected n := by
  simp [choose, s, m]
theorem explicit_mismatch_refuses (r : Request) (n : Nat) (s : r.explicit = some n)
    (m : r.explicitMatches = false) : choose r = .explicitMismatch := by
  simp [choose, s, m]
theorem explicit_can_bypass_scan_limit (n entries limit : Nat) :
    choose ⟨entries, limit, [], some n, true⟩ = .selected n := by
  rfl
theorem incomplete_scan_has_no_selection (r : Request) (s : r.explicit = none)
    (h : r.entries > r.limit) : choose r = .limit := by
  simp [choose, s, h]
theorem incomplete_scan_not_published (r : Request) (s : r.explicit = none)
    (h : r.entries > r.limit) : published (choose r) = false := by
  rw [incomplete_scan_has_no_selection r s h]; rfl
theorem ambiguity_not_published : published .ambiguous = false := by rfl
theorem missing_not_published : published .missing = false := by rfl
theorem mismatch_not_published : published .explicitMismatch = false := by rfl
theorem selection_published (n : Nat) : published (.selected n) = true := by rfl
theorem selection_exit_zero (n : Nat) : exitCode (.selected n) = 0 := by rfl
theorem ambiguity_exit_one : exitCode .ambiguous = 1 := by rfl
theorem collision_control : choose ⟨2, 10000, [0,1], none, false⟩ = .ambiguous := by decide
theorem duplicate_control : choose ⟨2, 10000, [0,0], none, false⟩ = .selected 0 := by decide
theorem stronger_assertion_control : choose ⟨2, 10000, [0], none, false⟩ = .selected 0 := by decide
theorem limit_before_matching_control : choose ⟨10001, 10000, [0], none, false⟩ = .limit := by decide

end ApplicationStudy.EmpackDiscovery
