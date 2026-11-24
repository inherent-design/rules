import terminal.Model
namespace TerminalStudy.Npm

/-- Pinned no-command --help path; not all npm help subcommands. -/
def topHelpExit : Nat := 1
def unknownCommandChannel : Channel := .stdout
def installDryRunProject : EffectKnowledge := .unchanged
def installDryRunCache : EffectKnowledge := .changed
def childFailure (effects : Effects) : Report := ⟨.failed, effects, true⟩

theorem help_is_not_exit_zero : topHelpExit ≠ 0 := by decide
theorem dry_run_does_not_mean_no_writes :
    installDryRunProject ≠ installDryRunCache := by decide
theorem child_failure_retains_project_effect (e : Effects) :
    (childFailure e).effects.project = e.project := rfl

end TerminalStudy.Npm
