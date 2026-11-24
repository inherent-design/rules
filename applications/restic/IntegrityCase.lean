import Lean
import applications.restic.Integrity
open Lean ApplicationStudy.ResticIntegrity

private structure PackRow where
  id : String
  bucket : Nat
  healthy : Bool
  deriving FromJson

private structure Row where
  action : Nat
  scope : Nat
  indexOK : Bool
  structureOK : Bool
  headersRecoverable : Bool
  packs : List PackRow
  target : String
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def simulate (row : Row) : Except String Json := do
  if row.scope > 3 then throw "Unsupported integrity scope."
  let ids := row.packs.map (·.id)
  if ids.eraseDups.length != ids.length then throw "Duplicate pack identity."
  if row.packs.any (fun p => p.bucket > 1) then throw "Unsupported half-bucket."
  let repo : Repository := ⟨row.indexOK, row.structureOK, row.headersRecoverable,
    row.packs.map (fun p => ⟨p.id, p.bucket, p.healthy⟩)⟩
  let success ← match row.action with
    | 0 => pure (check repo row.scope)
    | 1 => pure repo.headersRecoverable
    | 2 =>
      if !ids.contains row.target then throw "Read target lacks a captured pack."
      pure (readOne repo row.target)
    | _ => throw "Unsupported integrity action."
  pure (Json.mkObj [("success", toJson success),
    ("fullDataClaim", toJson (row.action == 0 && fullDataClaim repo row.scope))])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one integrity projection input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported integrity schema."; return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
