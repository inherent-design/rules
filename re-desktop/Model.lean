import common.Core
namespace Desktop
structure Grant where
  holder : Nat
  epoch : Nat
  untilMs : Nat
  deriving DecidableEq
def renew (s : Grant) (who epoch now : Nat) :=
  if who = s.holder ∧ epoch = s.epoch then {s with untilMs := now + 900000} else s
theorem stale_epoch (s : Grant) (who e now : Nat) (h : e ≠ s.epoch) :
    renew s who e now = s := by simp [renew,h]
theorem wrong_caller (s : Grant) (who e now : Nat) (h : who ≠ s.holder) :
    renew s who e now = s := by simp [renew,h]

theorem accepted_deadline (s : Grant) (now : Nat) :
    (renew s s.holder s.epoch now).untilMs = now + 900000 := by simp [renew]

-- Historical regression: using the presence interval produced 30100 here.
example : (renew ⟨1,1,900000⟩ 1 1 100).untilMs = 900100 := rfl
end Desktop
