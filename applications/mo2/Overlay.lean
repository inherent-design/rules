namespace ApplicationStudy.Mo2

/-- Candidates for one file after profile eligibility is established. `none`
    models the negative-order sentinel; the native comparison reserves INT_MAX.
    This is the post-sort conflict view, not the Windows injection mechanism. -/
structure Origin where
  id : Nat
  loose : Bool
  order : Option Nat
  deriving DecidableEq, Repr

def rank (o : Origin) : Nat × Nat :=
  ((if o.loose then 2 else 0) + (if o.order.isNone then 1 else 0), o.order.getD 0)

def outranks (a b : Origin) : Bool :=
  let x := rank a
  let y := rank b
  x.1 > y.1 || (x.1 == y.1 && x.2 > y.2)

def pick (candidate : Origin) : Option Origin → Origin
  | none => candidate
  | some best => if outranks candidate best then candidate else best

def winner : List Origin → Option Origin
  | [] => none
  | head :: tail => some (pick head (winner tail))

theorem loose_beats_archive (a b : Option Nat) :
    outranks ⟨1, true, a⟩ ⟨2, false, b⟩ = true := by
  cases a <;> cases b <;> simp [outranks, rank]

theorem sentinel_beats_finite (loose : Bool) (n : Nat) :
    outranks ⟨1, loose, none⟩ ⟨2, loose, some n⟩ = true := by
  cases loose <;> simp [outranks, rank]

theorem higher_order_wins_same_class (loose : Bool) (a b : Nat) (h : a > b) :
    outranks ⟨1, loose, some a⟩ ⟨2, loose, some b⟩ = true := by
  cases loose <;> simp [outranks, rank, h]

theorem empty_has_no_winner : winner [] = none := rfl
theorem sole_candidate_wins (o : Origin) : winner [o] = some o := rfl

end ApplicationStudy.Mo2
