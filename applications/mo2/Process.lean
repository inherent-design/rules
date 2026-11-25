namespace ApplicationStudy.Mo2Process

/-- Interpreted flags and injected wait result; not Windows process observations. -/
structure Request where
  hooked : Bool
  triggerRefresh : Bool
  forceWait : Bool
  waitForRefresh : Bool
  reason : Nat -- 0 none, 1 lock UI, 2 output required, 3 prevent exit
  lockEnabled : Bool
  waitResult : Nat -- source enum: 1 running, 2 completed, 3 error, 4 cancelled, 5 unlocked
  deriving Repr, DecidableEq
structure Outcome where
  returned : Nat
  reason : Nat
  waited : Bool := false
  lockAttached : Bool := false
  nullSession : Bool := false
  afterRun : Bool := false
  refreshWait : Bool := false
  deriving Repr, DecidableEq

def shouldRefresh (trigger : Bool) (result : Nat) : Bool :=
  trigger && (result == 2 || result == 5)

def post (r : Request) : Outcome :=
  if !r.hooked && !r.forceWait then { returned := 1, reason := r.reason }
  else
    let reason := if r.forceWait && r.reason == 0 then 1 else r.reason
    if !r.forceWait && r.reason == 0 then { returned := 1, reason }
    else if !r.forceWait && !r.lockEnabled then { returned := 5, reason }
    else
      let background := r.forceWait && reason == 3 && !r.lockEnabled
      let refresh := shouldRefresh r.triggerRefresh r.waitResult
      { returned := r.waitResult, reason, waited := true,
        lockAttached := !background, nullSession := background,
        afterRun := refresh, refreshWait := refresh && r.waitForRefresh }

theorem no_trigger (result : Nat) : shouldRefresh false result = false := by
  simp [shouldRefresh]
theorem completed_refresh (trigger : Bool) : shouldRefresh trigger 2 = trigger := by
  simp [shouldRefresh]
theorem unlocked_refresh (trigger : Bool) : shouldRefresh trigger 5 = trigger := by
  simp [shouldRefresh]
theorem cancellation_no_refresh (trigger : Bool) : shouldRefresh trigger 4 = false := by
  simp [shouldRefresh]
theorem error_no_refresh (trigger : Bool) : shouldRefresh trigger 3 = false := by
  simp [shouldRefresh]
theorem running_no_refresh (trigger : Bool) : shouldRefresh trigger 1 = false := by
  simp [shouldRefresh]
theorem unhooked_no_force (r : Request) (h : r.hooked = false) (f : r.forceWait = false) :
    post r = { returned := 1, reason := r.reason } := by
  simp [post, h, f]
theorem force_waits (r : Request) (f : r.forceWait = true) : (post r).waited = true := by
  simp [post, f]
theorem force_uses_wait_outcome (r : Request) (f : r.forceWait = true) :
    (post r).returned = r.waitResult := by
  simp [post, f]
theorem force_default_reason (r : Request) (f : r.forceWait = true) (n : r.reason = 0) :
    (post r).reason = 1 := by
  simp [post, f, n]
theorem no_reason_does_not_wait (r : Request) (f : r.forceWait = false) (n : r.reason = 0) :
    (post r).waited = false := by
  simp [post, f, n]
theorem disabled_early_skips_refresh (r : Request) (h : r.hooked = true)
    (f : r.forceWait = false) (n : r.reason ≠ 0) (l : r.lockEnabled = false) :
    (post r).returned = 5 ∧ (post r).afterRun = false := by
  simp [post, h, f, n, l]
theorem background_wait_has_no_ui (r : Request) (f : r.forceWait = true)
    (n : r.reason = 3) (l : r.lockEnabled = false) :
    (post r).nullSession = true ∧ (post r).lockAttached = false := by
  simp [post, f, n, l]
theorem force_refresh_bound (r : Request) (f : r.forceWait = true) :
    (post r).afterRun = shouldRefresh r.triggerRefresh r.waitResult := by
  simp [post, f]
theorem force_refresh_wait_bound (r : Request) (f : r.forceWait = true) :
    (post r).refreshWait = (shouldRefresh r.triggerRefresh r.waitResult && r.waitForRefresh) := by
  simp [post, f]

end ApplicationStudy.Mo2Process
