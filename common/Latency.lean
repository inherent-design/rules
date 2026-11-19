import common.Core
namespace Rules.Latency

/-- Stamps in one monotonic clock domain. Bounds must include queueing,
    admission, observation and publication. None allows unbounded waiting. -/
abbrev Bound := Option Nat
def chain (a b : Bound) : Bound := do return (← a) + (← b)
def barrier (a b : Bound) : Bound := do return max (← a) (← b)
def eitherReady : Bound → Bound → Bound
  | some a, some b => some (min a b)
  | some a, none | none, some a => some a
  | none, none => none

theorem serial_bound (start observed published a b : Nat)
    (observeBy : observed ≤ start + a) (publishBy : published ≤ observed + b) :
    published ≤ start + (a+b) := by omega

theorem join_bound (start left right a b : Nat)
    (hl : left ≤ start + a) (hr : right ≤ start + b) :
    max left right ≤ start + max a b := by omega

theorem first_sufficient_bound (start left right a b : Nat)
    (hl : left ≤ start+a) (hr : right ≤ start+b) :
    min left right ≤ start + min a b := by omega

example : chain (some 2) none = none := rfl
example : barrier (some 2) none = none := rfl
example : eitherReady (some 2) none = some 2 := rfl
end Rules.Latency
