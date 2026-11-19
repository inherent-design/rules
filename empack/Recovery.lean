import common.Core
namespace Empack.Recovery

/-- One journaled file. Repeating this decision for every retained preimage
    makes a partially applied multi-file operation recoverable. -/
inductive Choice | finish | restore deriving DecidableEq
inductive Decision | leave | write (digest : Option Nat) | conflict deriving DecidableEq
structure Entry where
  before : Option Nat
  after : Option Nat
def reconcile (e : Entry) (seen : Option Nat) (choice : Choice) : Decision :=
  let target := if choice = .finish then e.after else e.before
  if seen = target then .leave
  else if seen = e.before ∨ seen = e.after then .write target
  else .conflict
def interpret (seen : Option Nat) : Decision → Option Nat
  | .write d => d
  | _ => seen

theorem foreign_bytes_preserved (e : Entry) (seen : Option Nat) (c : Choice)
    (hb : seen ≠ e.before) (ha : seen ≠ e.after) :
    reconcile e seen c = .conflict := by cases c <;> simp [reconcile, hb, ha]

theorem replay_safe (e : Entry) (s : Option Nat) (c : Choice) :
    let next := interpret s (reconcile e s c)
    interpret next (reconcile e next c) = next := by
  cases c <;> by_cases hb : s = e.before <;> by_cases ha : s = e.after <;>
    simp_all [reconcile, interpret]

example : reconcile ⟨some 7,none⟩ (some 9) .finish = .conflict := rfl
end Empack.Recovery
