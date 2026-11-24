import terminal.Model
namespace TerminalStudy.Empack

def canChoose (yes : Bool) (s : Streams) : Bool := !yes && s.inputTty && s.errorTty
def resultChannel : Channel := .stdout
def progressChannel : Channel := .stderr
def parserExit : Nat := 2
def previewEffects : Effects := ⟨.unchanged, .unchanged, .unchanged⟩

/-- Native operation result wins over a late cancellation request. -/
def finalize (_cancelRequested : Bool) (actual : Report) : Report := actual

theorem stdout_redirection_preserves_choice (yes : Bool) (s : Streams) :
    canChoose yes { s with outputTty := false } = canChoose yes s := rfl
theorem stdin_required (yes : Bool) (s : Streams) :
    canChoose yes { s with inputTty := false } = false := by simp [canChoose]
theorem progress_does_not_own_result_stream : resultChannel ≠ progressChannel := by decide
theorem late_interrupt_does_not_erase_success (r : Report) : finalize true r = r := rfl
theorem cleanup_diagnostic_retained (r : Report) :
    (finalize true r).diagnostic = r.diagnostic := rfl

end TerminalStudy.Empack
