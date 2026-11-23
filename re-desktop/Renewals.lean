import «re-desktop».Model

open Desktop

private def showAccess (label : String) (s : Access) : IO Unit := do
  let mode := match s.mode with | .allowed => "allow" | .pending => "pause_after" | .paused => "pause"
  IO.println s!"{label} {mode} {(s.current.map (·.holder)).getD 0} {acceptsNewGrant s}"

def main : IO Unit := do
  let initial : Grant := ⟨1, 1, 900000⟩
  for (label, caller, epoch) in [("accepted", 1, 1), ("stale", 1, 0), ("wrong-caller", 2, 1)] do
    let next := renew initial caller epoch 100
    IO.println s!"{label} {next.holder} {next.epoch} {next.untilMs}"
  showAccess "empty" (pauseAfter ⟨.allowed,none⟩)
  let pending := pauseAfter ⟨.allowed,some initial⟩
  showAccess "held" pending
  showAccess "released" (endGrant pending)
