import common.Core
namespace Playground
open Rules
structure Charge where
  memoryUsed : Nat
  kindUsed : Nat
  deriving DecidableEq

def reserve (s : Charge) (size memCap kindCap : Nat) : Option Charge :=
  if 0 < size ∧ admit s.memoryUsed size memCap ∧ admit s.kindUsed size kindCap
  then some ⟨s.memoryUsed + size, s.kindUsed + size⟩ else none

theorem split_conserves (total child : Nat) (h : child ≤ total) :
    total - child + child = total := Nat.sub_add_cancel h

/-- Two adjacent regions with a coherent one-cell halo. A value of none
    denotes unavailable coverage. Both outputs read the same old root. -/
abbrev Regions := Nat × Nat
def advance (old : Snapshot Regions) (base : Nat) (leftHalo rightHalo : Option Nat)
    (budget : Option Charge) :=
  commit old base (do
    let _ ← budget
    let l ← leftHalo
    let r ← rightHalo
    pure (max l old.value.2, max old.value.1 r))

theorem missing_halo (old : Snapshot Regions) (base : Nat) (r : Option Nat) (b : Option Charge) :
    advance old base none r b = old := by cases b <;> apply missing_holds

example : advance ⟨4,(1,9)⟩ 4 (some 0) (some 0)
    (reserve ⟨3,1⟩ 2 5 3) = ⟨5,(9,1)⟩ := by decide
example : advance ⟨4,(1,9)⟩ 4 (some 0) (some 0)
    (reserve ⟨3,2⟩ 2 5 3) = ⟨4,(1,9)⟩ := by decide
end Playground

namespace Playground
/-- Equal total usage in the same memory class can hide different target
    charges. Coarsening to total memory loses the target-admission decision. -/
def tryTarget (s : Charge) : Charge := (reserve s 1 10 2).getD s

example : ¬ ∃ coarse : Nat → Nat, ∀ s : Charge,
    (tryTarget s).memoryUsed = coarse s.memoryUsed := by
  exact Rules.loss_obstruction Charge.memoryUsed tryTarget ⟨3,1⟩ ⟨3,2⟩ rfl (by decide)
end Playground
