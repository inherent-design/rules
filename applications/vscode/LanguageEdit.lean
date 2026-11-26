import applications.vscode.WorkspaceSearch

namespace ApplicationStudy.VscodeLanguageEdit
open ApplicationStudy.VscodeWorkspaceSearch

/-- These operations are the generated single-document fixture, not arbitrary
    language semantics, file edits, or a general editor implementation. -/
inductive Mode
  | workspace | guarded | editorPair | formatCompute | formatApply
  | formatCommand | renameCompute | renameApply
  deriving Repr, BEq, DecidableEq

structure Request where
  mode : Mode
  basis : Nat
  secondBasis : Nat
  intervened : Bool
  secondEmpty : Bool
  deriving Repr

structure Result where
  response : String
  text : String
  changes : Nat
  canceled : Bool
  deriving Repr, BEq, DecidableEq

def base : String := "alpha beta\n"
def insertedPrefix : String := "shift "
def replaceFive (text value : String) : String :=
  String.ofList (replaceRange text.toList 0 5 value.toList)
def boolean (b : Bool) : String := if b then "true" else "false"

/-- Empty TextEditor edits return true without reaching version admission.
    A nonempty editor edit binds its version when the builder is created. -/
def editorAllowed (empty : Bool) (captured current : Nat) : Bool :=
  empty || currentVersionGuard captured current

/-- Workspace submission checks the RPC submission basis, not a previously
    computed range's origin. The extension's stricter guard is a proposal. -/
def workspaceAllowed (guarded : Bool) (planned submitted current : Nat) : Bool :=
  if guarded then plannedVersionGuard planned submitted current
  else currentVersionGuard submitted current

def run (r : Request) : Result := Id.run do
  let text := if r.intervened then insertedPrefix ++ base else base
  let changes := if r.intervened then 1 else 0
  let current := r.basis + changes
  match r.mode with
  | .workspace | .guarded =>
    let allowed := workspaceAllowed (r.mode == .guarded) r.basis current current
    return ⟨if r.mode == .guarded && !allowed then "not-called" else boolean allowed,
      if allowed then replaceFive text "EDIT" else text, changes + (if allowed then 1 else 0), false⟩
  | .editorPair =>
    let first := editorAllowed false r.basis current
    let firstText := if first then replaceFive text "ONE" else text
    let firstChanges := changes + (if first then 1 else 0)
    let second := editorAllowed r.secondEmpty r.secondBasis (r.basis + firstChanges)
    let writes := second && !r.secondEmpty
    return ⟨boolean first ++ "," ++ boolean second,
      if writes then replaceFive firstText "TWO" else firstText,
      firstChanges + (if writes then 1 else 0), false⟩
  | .formatCompute | .renameCompute => return ⟨"returned-edits", text, changes, false⟩
  | .formatApply | .renameApply =>
    let replacement := if r.mode == .formatApply then "FMT(alpha)" else "REN"
    return ⟨"true", replaceFive text replacement, changes + 1, false⟩
  | .formatCommand =>
    -- Selected source cancels on content/position change. This fixture does
    -- not isolate those two causes or model arbitrary cancellation timing.
    return ⟨"undefined", if r.intervened then text else replaceFive text "FMT(alpha)",
      changes + (if r.intervened then 0 else 1), r.intervened⟩

theorem empty_success_does_not_check_version (a b : Nat) : editorAllowed true a b = true := by
  simp [editorAllowed]
theorem matching_editor_version_applies (v : Nat) : editorAllowed false v v = true := by
  simp [editorAllowed, currentVersionGuard]
theorem changed_editor_version_refuses (a b : Nat) (h : a ≠ b) :
    editorAllowed false a b = false := by simp [editorAllowed, currentVersionGuard, h]
theorem submission_does_not_retain_plan (p s : Nat) : workspaceAllowed false p s s = true := by
  simp [workspaceAllowed, currentVersionGuard]
theorem caller_guard_refuses_changed_plan (p s : Nat) (h : p ≠ s) :
    workspaceAllowed true p s s = false := by
  simp [workspaceAllowed, plannedVersionGuard, h]
theorem parallel_second_refuses :
    run ⟨.editorPair, 8, 8, false, false⟩ = ⟨"true,false", "ONE beta\n", 1, false⟩ := by decide
theorem sequential_freshness_does_not_rebase_range :
    run ⟨.editorPair, 10, 11, false, false⟩ = ⟨"true,true", "TWOeta\n", 2, false⟩ := by decide
theorem parallel_empty_success_has_no_second_write :
    run ⟨.editorPair, 13, 13, false, true⟩ = ⟨"true,true", "ONE beta\n", 1, false⟩ := by decide
theorem computed_format_is_not_application (v : Nat) :
    run ⟨.formatCompute, v, v, false, false⟩ = ⟨"returned-edits", base, 0, false⟩ := by rfl
theorem computed_rename_is_not_application (v : Nat) :
    run ⟨.renameCompute, v, v, false, false⟩ = ⟨"returned-edits", base, 0, false⟩ := by rfl
theorem changed_normal_format_preserves_intervening_edit (v : Nat) :
    run ⟨.formatCommand, v, v, true, false⟩ = ⟨"undefined", insertedPrefix ++ base, 1, true⟩ := by rfl
theorem delayed_rename_caller_can_apply_old_coordinates :
    run ⟨.renameApply, 20, 20, true, false⟩ = ⟨"true", "REN alpha beta\n", 2, false⟩ := by decide

end ApplicationStudy.VscodeLanguageEdit
