namespace ApplicationStudy.CargoInstallCompletion

/-- Result of the selected tracking phase, not a durable two-file commit.
    Failed tracking can have partial writes. Disabled tracking claims nothing. -/
inductive Tracking where
  | disabled | saved | failed
  deriving BEq, DecidableEq, Repr

structure Current where
  commandFailed : Bool
  newBinSurvives : Bool
  replacementHeadline : Bool
  deriving BEq, DecidableEq, Repr

/-- The staged-prefix scope has one published new bin and one requested
    replacement. No later cleanup/status failure is admitted. This projects the
    pinned conditional propagation and Transaction.drop; it is not a filesystem,
    serialization, syscall, or crash model. -/
def current (tracking : Tracking) (replacementFailed : Bool) : Current :=
  let failed := tracking != .disabled && replacementFailed
  ⟨failed, !failed, !failed⟩

structure ProposedResult where
  commandFailed : Bool
  replacementMayBeReported : Bool
  deriving BEq, DecidableEq, Repr

/-- Proposed result composition only. Cleanup and partial metadata reconciliation
    remain an implementation obligation; no candidate rollback is asserted. -/
def proposed (tracking : Tracking) (replacementFailed : Bool) : ProposedResult :=
  ⟨replacementFailed || tracking == .failed, !replacementFailed⟩

theorem untracked_replacement_error_is_masked :
    (current .disabled true).commandFailed = false := rfl
theorem untracked_failed_replacement_is_announced :
    (current .disabled true).replacementHeadline = true := rfl
theorem untracked_new_bin_remains :
    (current .disabled true).newBinSurvives = true := rfl
theorem tracked_error_removes_new_bin :
    (current .saved true).newBinSurvives = false := rfl
theorem tracking_error_alone_is_masked :
    (current .failed false).commandFailed = false := rfl
theorem both_errors_fail : (current .failed true).commandFailed = true := rfl
theorem proposed_never_masks_replacement (tracking : Tracking) :
    (proposed tracking true).commandFailed = true := by cases tracking <;> rfl
theorem proposed_never_masks_tracking (replacementFailed : Bool) :
    (proposed .failed replacementFailed).commandFailed = true := by
  cases replacementFailed <;> rfl
theorem proposed_does_not_announce_failed_replacement (tracking : Tracking) :
    (proposed tracking true).replacementMayBeReported = false := rfl
theorem a_replacement_effect_survives_other_failure :
    proposed .failed false = ⟨true,true⟩ := rfl

end ApplicationStudy.CargoInstallCompletion
