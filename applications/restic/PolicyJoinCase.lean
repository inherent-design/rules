import Lean
import applications.restic.PolicyJoin
open Lean ApplicationStudy

private structure Metadata where
  id : String
  host : String
  paths : List String
  rank : Nat
  parent : Option String
  reachable : List String
  deriving FromJson
private structure Boundary where
  dry : Bool
  refused : List String
  deriving FromJson
private structure Input where
  schema : Nat
  snapshots : List Metadata
  available : List String
  cases : List Boundary
  deriving FromJson
private def render (o : ResticPolicyJoin.Outcome) : Json := Json.mkObj [
  ("planned",toJson o.planned.mergeSort),("removed",toJson o.removed.mergeSort),
  ("snapshots",toJson o.snapshots.mergeSort),("available",toJson o.available.mergeSort),
  ("prunePhase",toJson o.prunePhase),("code",toJson o.code)]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one policy-join JSON path."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    let ids := input.snapshots.map (·.id)
    let ranks := input.snapshots.map (·.rank)
    if input.schema != 1 || input.snapshots.length != 4 || ids.eraseDups.length != 4 ||
        ranks.eraseDups.length != 4 || input.available.eraseDups.length != 5 then
      IO.eprintln "Unsupported policy-join fixture or duplicate identity/rank."; return 2
    if input.snapshots.any (fun s => s.paths.length != 1 || s.reachable.length != 2 ||
        s.reachable.any (fun b => !input.available.contains b)) ||
        input.cases.any (fun c => c.refused.any (fun id => !ids.contains id)) then
      IO.eprintln "Incomplete selected reachability or unknown refusal identity."; return 2
    let metadata := input.snapshots.map fun s => ResticSelection.Snapshot.mk s.id s.host s.paths [] s.rank
    let repository : Restic.Repository := ⟨input.snapshots.map (fun s => ⟨s.id,s.parent,s.reachable⟩),input.available⟩
    IO.println (toJson (input.cases.map fun c => render (ResticPolicyJoin.run metadata repository c.dry c.refused))).compress
    return 0
