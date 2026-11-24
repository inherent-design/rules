import Lean
import applications.restic.Selection
open Lean ApplicationStudy.ResticSelection

private structure SnapshotRow where
  id : String
  host : String
  paths : List String
  tags : List String
  rank : Nat
  deriving FromJson

private structure Row where
  operation : String
  hosts : List String
  paths : List String
  tags : List (List String)
  groupBy : String
  keepTags : List (List String)
  deriving FromJson

private structure Input where
  schema : Nat
  snapshots : List SnapshotRow
  cases : List Row
  deriving FromJson

private structure Output where
  selected : List String
  kept : List String
  removed : List String
  deriving ToJson

private def ids (snapshots : List Snapshot) : List String := (snapshots.map (·.id)).mergeSort

private def evaluate (snapshots : List Snapshot) (row : Row) : Except String Output := do
  if (row.tags ++ row.keepTags).any (fun tags => tags.isEmpty || tags.contains "") then
    throw "Untagged selector is outside this bounded profile."
  let group ← match row.groupBy with
    | "" => pure ungrouped
    | "host,paths" => pure hostPaths
    | "host,paths,tags" => pure (Grouping.mk true true true)
    | _ => throw "Unknown snapshot grouping profile."
  let filtered := select snapshots ⟨row.hosts, row.paths, row.tags⟩
  match row.operation with
  | "select" => pure ⟨ids filtered, [], []⟩
  | "latest" => pure ⟨ids (latest filtered (inspectionGrouping group)), [], []⟩
  | "latest-id" => pure ⟨ids (latest filtered ungrouped), [], []⟩
  | "keep" => pure ⟨[], ids (keep filtered group row.keepTags), ids (remove filtered group row.keepTags)⟩
  | _ => throw "Unknown snapshot-selection operation."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one restic-selection input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported restic-selection schema."
      return 2
    let snapshots := input.snapshots.map fun row => Snapshot.mk row.id row.host row.paths row.tags row.rank
    let identities := snapshots.map (·.id)
    let ranks := snapshots.map (·.rank)
    if identities.eraseDups.length != identities.length || ranks.eraseDups.length != ranks.length then
      IO.eprintln "Unique snapshot identities and timestamps required."
      return 2
    match input.cases.mapM (evaluate snapshots) with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
