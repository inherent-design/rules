import empack.Model
import playground.Model
import moment.Model
open Rules

namespace Across
/-- Compare the same outer capacity predicate through three different
    owners. Empack can classify pressure by retryability, Moment also
    requires current authority, and Playground rejects zero-size tokens. -/
def oneDim (x : Nat) : Empack.Envelope :=
  fun r => if r = .memory then x else 0

theorem empack_to_gate (used ask cap : Nat) :
    (Empack.classify false (oneDim cap) (oneDim used) (oneDim ask) == .granted) =
    admit used ask cap := by
  simp [Empack.classify, Empack.dimensions, oneDim, admit]
  by_cases large : cap < ask
  · have bad : ¬ used + ask ≤ cap := by omega
    simp [large,bad]
  · by_cases fits : used + ask ≤ cap <;> simp [large,fits] <;> rfl

theorem playground_to_gate (used ask cap : Nat) (positive : 0 < ask) :
    (Playground.reserve ⟨used,used⟩ ask cap cap).isSome = admit used ask cap := by
  simp [Playground.reserve,positive]
  split <;> simp_all

theorem moment_to_gate (ask cap : Nat) :
    Moment.dispatch ⟨0,true,1⟩ true cap ask = admit 0 ask cap := rfl

example : Moment.dispatch ⟨0,true,1⟩ false 10 1 ≠ admit 0 1 10 := by decide
end Across
