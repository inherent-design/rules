import terminal.Npm
import terminal.Pnpm
import terminal.Yarn
import terminal.Candidate
open TerminalStudy

private def bit (b : Bool) : Nat := if b then 1 else 0
private def mode (n : Nat) : Candidate.Mode :=
  if n = 0 then .inspect else if n = 1 then .preview else .apply
private def decision : Candidate.Decision → Nat
  | .inspect => 0 | .plan => 1 | .apply => 2 | .requireApproval => 3 | .refresh => 4 | .refuse => 5

def main : IO Unit := do
  IO.println s!"npm-help,{Npm.topHelpExit}"
  IO.println s!"npm-dry-project,{bit (Npm.installDryRunProject = .changed)}"
  IO.println s!"npm-dry-cache,{bit (Npm.installDryRunCache = .changed)}"
  IO.println s!"pnpm-refusal-project,{bit (Pnpm.unknownCommandAfterDefaultGate.effects.project = .changed)}"
  IO.println s!"yarn-lock-write,{bit (Yarn.install .updateLockfile true).mayWriteLock}"
  IO.println s!"yarn-lock-link,{bit (Yarn.install .updateLockfile true).link}"
  IO.println s!"yarn-signal,{Yarn.signalledScriptExit}"
  IO.println s!"empack-parser,{Empack.parserExit}"
  for m in [0, 1, 2] do
    for c in [false, true] do
      for e in [false, true] do
        for a in [false, true] do
          let request : Candidate.Request := ⟨mode m, 7, if c then 7 else 8, if a then some 7 else none, e⟩
          IO.println s!"candidate,{m},{bit c},{bit e},{bit a},{decision (Candidate.decide request)}"
