import empack.Model
open Empack
private def record (n : Nat) : Option File :=
  if n = 0 then none else some ⟨(n-1)%3,if n ≤ 3 then .managed else .seed⟩
private def render : Action → String
  | .preserve => "Preserve"
  | .unchanged => "Unchanged"
  | .create n => s!"Create{n}"
  | .replace n => s!"Replace{n}"
  | .remove => "Remove"
  | .conflict .modified => "ModifiedManagedFile"
  | .conflict .seedOwnership => "SeedOwnership"
  | .conflict .wrongKind => "WrongKind"
  | .conflict .unowned => "UnownedDestination"
def main : IO Unit := do
  for old in [:7] do
    for live in [:5] do
      for next in [:7] do
        let path := match live with
          | 0 => Path.absent
          | 1 => Path.directory
          | n+2 => Path.file n
        IO.println s!"{old} {live} {next} {render (planFile (record old) path (record next))}"
