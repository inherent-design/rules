import «re-desktop».Model

open Desktop

def main : IO Unit := do
  let initial : Grant := ⟨1, 1, 900000⟩
  for (label, caller, epoch) in [("accepted", 1, 1), ("stale", 1, 0), ("wrong-caller", 2, 1)] do
    let next := renew initial caller epoch 100
    IO.println s!"{label} {next.holder} {next.epoch} {next.untilMs}"
