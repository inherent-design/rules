import Lean
import applications.restic.Retention
open Lean ApplicationStudy.Restic

private structure SnapshotInput where
  id : String
  parent : Option String
  reachableData : List String
  deriving FromJson

private structure Input where
  schema : Nat
  gone : String
  snapshots : List SnapshotInput
  availableData : List String
  exclusive : Bool
  deriving FromJson

private structure Output where
  afterForget : List String
  afterPrune : List String
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one projected native-input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported restic projection schema."
      return 2
    let r : Repository := ⟨input.snapshots.map (fun s => ⟨s.id, s.parent, s.reachableData⟩), input.availableData⟩
    let after := forget input.gone r
    let result : Output := ⟨after.availableData, (prune input.exclusive after).availableData⟩
    IO.println (toJson result).compress
    return 0
