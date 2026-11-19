import common.Core
namespace Desktop
structure Grant where
  holder : Nat
  epoch : Nat
  untilMs : Nat
  deriving DecidableEq
def renew (s : Grant) (who epoch now : Nat) :=
  if who = s.holder ∧ epoch = s.epoch then {s with untilMs := now + 30000} else s
theorem stale_epoch (s : Grant) (who e now : Nat) (h : e ≠ s.epoch) :
    renew s who e now = s := by simp [renew,h]
end Desktop
