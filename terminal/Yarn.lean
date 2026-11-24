import terminal.Model
namespace TerminalStudy.Yarn

inductive Mode | install | updateLockfile | immutable deriving DecidableEq, Repr
structure InstallDecision where
  refuse : Bool
  mayWriteLock : Bool
  link : Bool
  deriving DecidableEq, Repr

def install (mode : Mode) (lockNeedsChange : Bool) : InstallDecision :=
  match mode with
  | .updateLockfile => ⟨false, true, false⟩
  | .immutable => if lockNeedsChange then ⟨true, false, false⟩ else ⟨false, false, true⟩
  | .install => ⟨false, true, true⟩

/-- The ready/unready fixture pair, not mere existence of any lock filename. -/
def infoPayload (recordedFixtureReady : Bool) : Payload := if recordedFixtureReady then .ndjson else .human
/-- In the observed script runner, signal termination is projected to 129. -/
def signalledScriptExit : Nat := 129

theorem update_lockfile_is_not_dry_run :
    (install .updateLockfile true).mayWriteLock = true ∧
    (install .updateLockfile true).link = false := by decide
theorem immutable_disagreement_refuses : (install .immutable true).refuse = true := rfl
theorem json_flag_alone_does_not_cover_info_failure : infoPayload false ≠ .ndjson := by decide
theorem signal_not_universally_130 : signalledScriptExit ≠ 130 := by decide

end TerminalStudy.Yarn
