import Lean
import applications.restic.Copy
open Lean ApplicationStudy.ResticCopy
private structure RawSnapshot where
  id : Nat
  original : Option Nat
  parent : Option Nat
  fixed : Nat
  paths : List Nat
  tags : List Nat
  excludes : List Nat
  ignored : Nat
  deriving FromJson
private structure Row where
  source : RawSnapshot
  destination : List RawSnapshot
  sourceKeyAccepted : Bool
  copiedId : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def snap (r : RawSnapshot) : Except String Snapshot := do
  if [r.id,r.fixed,r.ignored].any (fun n => n == 0 || n > 4096) ||
      r.original.any (· > 4096) || r.parent.any (· > 4096) ||
      [r.paths,r.tags,r.excludes].any (fun xs => xs.length > 32 || xs.any (fun n => n == 0 || n > 4096)) then throw "Research snapshot bound."
  pure ⟨r.id,r.original,r.parent,r.fixed,r.paths,r.tags,r.excludes,r.ignored⟩
private def evaluate (r : Row) : Except String String := do
  if r.destination.length > 32 || r.copiedId == 0 || r.copiedId > 4096 then throw "Research destination bound."
  let s ← snap r.source
  let ds ← r.destination.mapM snap
  let next := copied s r.copiedId
  pure (String.intercalate "/" [toString (decision s ds r.sourceKeyAccepted),toString (persistent next),
    if next.parent.isNone then "-" else "parent",toString next.fixed])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one copy research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "restic-local-copy" || input.rows.length > 256 then
      IO.eprintln "Unsupported copy research input."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
