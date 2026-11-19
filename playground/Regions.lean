import playground.Schedule
namespace Playground.Regions
open Schedule
/-- Snapshot one cell and its neighbors. Negative addresses are legitimate.
    All observations come from the captured immutable input function. -/
def sample (readCell : Int → Option Nat) (x : Int) : Option (Int × Nat) := do
  let l ← readCell (x-1)
  let c ← readCell x
  let r ← readCell (x+1)
  return (x,max c (max l r))

def prepare (src : Int → Option Nat) (xs : List Int) := xs.mapM (sample src)

theorem partition (src : Int → Option Nat) (a b : List Int) :
    prepare src (a ++ b) = (do
      let left ← prepare src a
      let right ← prepare src b
      pure (left ++ right)) := by
  induction a with
  | nil => simp [prepare]
  | cons x xs ih =>
    unfold prepare at *
    simp only [List.cons_append, List.mapM_cons]
    cases sample src x <;> simp [ih]
    cases xs.mapM (sample src) <;> simp
    cases b.mapM (sample src) <;> rfl

example : prepare (fun k => if k = -2 then none else some 0) [-1,0] = none := by decide
end Playground.Regions
