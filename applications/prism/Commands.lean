namespace ApplicationStudy.PrismCommands

/-- Parsed tokens are an observed premise, not a proof of either command grammar. -/
structure Request where
  mode : Nat -- 0 pre, 1 post, 2 wrapper
  rawNonempty : Bool
  trimmedEmpty : Bool
  tokens : List Nat
  programExists : Bool
  processResult : Nat -- owned helper: 0 clean, 1 exit7, 2 cannot start, 3 aborted
  abortRequested : Bool
  gameArgs : List Nat
  deriving Repr, DecidableEq

/-- 0 omitted hook, 1 hook, 2 direct Java-data fixture, 3 wrapper,
    4 wrapper refusal, 5 unmet empty-list precondition.
    Code 5 predicts no defined product result; it is not a safe refusal. -/
def disposition (r : Request) : Nat :=
  if r.mode == 2 then
    if r.trimmedEmpty then 2
    else if r.tokens.isEmpty then 5
    else if r.programExists then 3 else 4
  else if !r.rawNonempty then 0
  else if r.tokens.isEmpty then 5 else 1

def attemptsStart (d : Nat) : Bool := d == 1 || d == 2 || d == 3
def terminal (r : Request) : Bool := attemptsStart (disposition r) || disposition r == 4
def successful (r : Request) : Bool := attemptsStart (disposition r) && r.processResult == 0
/-- Witness of the owned fixture child having run, not current liveness or tree containment. -/
def child (r : Request) : Bool := attemptsStart (disposition r) && r.processResult != 2
def abortAccepted (r : Request) : Bool := disposition r == 1 && r.abortRequested
def childArgs (r : Request) : List Nat :=
  if !child r then []
  else if disposition r == 1 then r.tokens.drop 1
  else if disposition r == 2 then r.gameArgs
  else r.tokens.drop 1 ++ [0] ++ r.gameArgs -- fixture label 0 denotes selected Java executable

/-- Proposed admission guard; only this design classifier turns an unmet precondition into refusal. -/
def guardedDisposition (r : Request) : Nat := if disposition r == 5 then 4 else disposition r

/-- Inspected sequence contract; no game or joined controller is executed by this band. -/
def postEligible (preSucceeded gameSucceeded configured : Bool) : Bool :=
  preSucceeded && gameSucceeded && configured

theorem whitespace_wrapper_direct (r : Request) (m : r.mode = 2) (e : r.trimmedEmpty = true) :
    disposition r = 2 := by simp [disposition, m, e]
theorem expanded_empty_wrapper_unmet (r : Request) (m : r.mode = 2)
    (e : r.trimmedEmpty = false) (t : r.tokens = []) : disposition r = 5 := by
  simp [disposition, m, e, t]
theorem nonempty_hook_unmet (r : Request) (m : r.mode = 0) (n : r.rawNonempty = true)
    (t : r.tokens = []) : disposition r = 5 := by simp [disposition, m, n, t]
theorem post_empty_quotes_unmet (r : Request) (m : r.mode = 1) (n : r.rawNonempty = true)
    (t : r.tokens = []) : disposition r = 5 := by simp [disposition, m, n, t]
theorem unconfigured_hook_omitted (r : Request) (m : r.mode = 0) (n : r.rawNonempty = false) :
    disposition r = 0 := by simp [disposition, m, n]
theorem refusal_no_start_attempt : attemptsStart 4 = false := by rfl
theorem unmet_no_execution_claim : attemptsStart 5 = false := by rfl
theorem cannot_start_no_child (r : Request) (p : r.processResult = 2) : child r = false := by
  simp [child, p]
theorem nonzero_exit_not_success (r : Request) (p : r.processResult = 1) : successful r = false := by
  simp [successful, p]
theorem aborted_not_success (r : Request) (p : r.processResult = 3) : successful r = false := by
  simp [successful, p]
theorem proposed_guard_refuses_unmet (r : Request) (d : disposition r = 5) :
    guardedDisposition r = 4 := by simp [guardedDisposition, d]
theorem proposed_guard_keeps_defined (r : Request) (d : disposition r ≠ 5) :
    guardedDisposition r = disposition r := by simp [guardedDisposition, d]
theorem failed_game_skips_post (pre configured : Bool) : postEligible pre false configured = false := by
  simp [postEligible]
theorem unconfigured_post_skipped (pre game : Bool) : postEligible pre game false = false := by
  simp [postEligible]
theorem wrapper_keeps_game_suffix (wrapperParams game : List Nat) :
    (wrapperParams ++ [0] ++ game).drop (wrapperParams.length + 1) = game := by
  simp

end ApplicationStudy.PrismCommands
