import terminal.Model
namespace TerminalStudy.Pnpm

inductive Gate | install | prompt | error deriving DecidableEq, Repr
inductive Action | proceed | installThenRun | ask | refuse deriving DecidableEq, Repr

/-- Only the pre-run dependency gate, not a model of the entire solver. -/
def gate (mode : Gate) (current : Bool) (inputTty : Bool) : Action :=
  if current then .proceed else
  match mode with
  | .install => .installThenRun
  | .prompt => if inputTty then .ask else .refuse
  | .error => .refuse

def unknownCommandAfterDefaultGate : Report :=
  ⟨.failed, ⟨.changed, .unknown, .changed⟩, true⟩

theorem unknown_command_can_follow_install :
    unknownCommandAfterDefaultGate.completion = .failed ∧
    unknownCommandAfterDefaultGate.effects.project = .changed := by decide
theorem prompt_needs_input : gate .prompt false false = .refuse := rfl
theorem prompt_is_not_default_install :
    gate .prompt false true ≠ gate .install false true := by decide
theorem fresh_default_installs : gate .install false false = .installThenRun := rfl

end TerminalStudy.Pnpm
