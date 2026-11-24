import Lean
import applications.restic.Locks
open Lean ApplicationStudy.ResticLocks

private structure View where
  token : String
  owner : Nat
  exclusive : Bool
  readable : Bool
  emptyUpload : Bool
  old : Bool
  sameHost : Bool
  reachable : Bool
  deriving FromJson

private structure Row where
  mode : Nat
  exclusive : Bool
  owner : Nat
  cleanup : Bool
  locks : List View
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def simulate (row : Row) : Except String Json := do
  let locks := row.locks.map fun p => LockView.mk p.token p.owner p.exclusive p.readable p.emptyUpload p.old p.sameHost p.reachable
  if (tokens locks).eraseDups.length != locks.length then throw "Duplicate lock observation identity."
  match row.mode with
  | 0 => pure (Json.mkObj [("allowed",toJson (admitted row.exclusive locks))])
  | 1 => pure (Json.mkObj [("locks",toJson (tokens (ordinaryUnlock locks)))])
  | 2 => pure (Json.mkObj [("locks",toJson (tokens (retired row.owner row.cleanup locks)))])
  | _ => throw "Unknown lock observation operation."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one lock observation JSON input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported lock observation schema."; return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
