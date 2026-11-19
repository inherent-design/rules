import moment.Model
namespace Moment.Hierarchy
abbrev Edge := Nat → Nat → Prop
inductive Path (e : Edge) : Nat → Nat → Prop where
  | direct {a b} : e a b → Path e a b
  | more {a b c} : e a b → Path e b c → Path e a c

/-- An acyclicity certificate for the final asserted graph in one perspective.
    A finite validated DAG admits a ranking. This lemma checks a supplied
    certificate; the runtime uses a traversal instead. -/
theorem strict_path (e : Edge) (rank : Nat → Nat)
    (increases : ∀ a b, e a b → rank a < rank b) {x y} (p : Path e x y) :
    rank x < rank y := by
  induction p with
  | direct h => exact increases _ _ h
  | more h _ ih => exact Nat.lt_trans (increases _ _ h) ih

theorem excludes_cycle (e : Edge) (rank : Nat → Nat)
    (h : ∀ a b, e a b → rank a < rank b) (a : Nat) : ¬ Path e a a :=
  fun p => (Nat.lt_irrefl _) (strict_path e rank h p)

theorem projected_hierarchy (full view : Edge) (included : ∀ a b, view a b → full a b)
    (rank : Nat → Nat) (h : ∀ a b, full a b → rank a < rank b) (a : Nat) :
    ¬ Path view a a := excludes_cycle _ rank (fun x y v => h x y (included x y v)) a
end Moment.Hierarchy
