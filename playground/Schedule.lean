import common.Core
namespace Playground.Schedule

/-- Interleavings of two intents commute only for disjoint cells and
    immutable prepared values. Halo reads happen before either write. -/
abbrev Grid := Int → Nat
def patch (g : Grid) (i : Int) (v : Nat) : Grid := fun j => if i = j then v else g j

theorem disjoint_patches (g : Grid) (a b : Int) (va vb : Nat) (h : a ≠ b) :
    patch (patch g a va) b vb = patch (patch g b vb) a va := by
  funext j
  by_cases x : a = j <;> by_cases y : b = j <;> simp_all [patch]

theorem competing_patches (g : Grid) (a : Int) (va vb : Nat) (h : va ≠ vb) :
    patch (patch g a va) a vb ≠ patch (patch g a vb) a va := by
  intro eq
  exact h (by simpa [patch] using (congrFun eq a).symm)

/-- A complete tick root and pending neighbor intents are captured together. -/
structure Saved where
  tick : Nat
  cells : Grid
  pending : List (Int × Nat)
def tick (s : Saved) (incoming : List (Int × Nat)) : Saved :=
  ⟨s.tick + 1, s.pending.foldl (fun g p => patch g p.1 p.2) s.cells, incoming⟩
theorem resume (s : Saved) (a b : List (List (Int × Nat))) :
    Rules.replay tick s (a ++ b) = Rules.replay tick (Rules.replay tick s a) b :=
  Rules.replay_chunks tick s a b
end Playground.Schedule
