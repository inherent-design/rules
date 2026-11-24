import Lean
import applications.cargo.Package
open Lean ApplicationStudy.CargoPackage

private structure Row where
  profile : String
  request : String
  includeLock : Bool
  compiles : Bool
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private structure Output where
  files : List String
  archiveCreated : Bool
  buildChecked : Bool
  buildSucceeded : Bool
  commandSucceeded : Bool
  deriving ToJson

private def evaluate (row : Row) : Except String Output := do
  let profile ← match row.profile with
    | "default" | "invalid-source" => pure Profile.defaults
    | "exclude" => pure Profile.exclude
    | "include" => pure Profile.include
    | "both" => pure Profile.both
    | _ => throw "Unknown package-selection profile."
  let request ← match row.request with
    | "list" => pure Request.list
    | "unchecked" | "without-lock" => pure Request.unchecked
    | "verified" | "verification-fails" => pure Request.verify
    | _ => throw "Unknown package request."
  let result := outcome request row.compiles
  pure ⟨inventory profile row.includeLock, result.archiveCreated, result.buildChecked,
    result.buildSucceeded, result.commandSucceeded⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Cargo package input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported Cargo package schema."
      return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok results => IO.println (toJson results).compress; return 0
