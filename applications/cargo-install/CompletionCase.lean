import Lean
import applications.«cargo-install».Completion
open Lean ApplicationStudy.CargoInstallCompletion

private structure Row where
  tracking : Nat
  replacementFailed : Bool
  stagedPrefixAdmitted : Bool
  laterFailureExcluded : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson

private def evaluate (row : Row) : Except String String := do
  if row.tracking > 2 || !row.stagedPrefixAdmitted || !row.laterFailureExcluded then
    throw "Unsupported completion scope or tracking result."
  let tracking := match row.tracking with
    | 0 => Tracking.disabled | 1 => .saved | _ => .failed
  let c := current tracking row.replacementFailed
  let p := proposed tracking row.replacementFailed
  pure (String.intercalate "/" ([c.commandFailed,c.newBinSurvives,c.replacementHeadline,
    p.commandFailed,p.replacementMayBeReported].map fun value => if value then "1" else "0"))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one completion research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "staged-new-bin-and-replacement" ||
        input.rows.length > 12 then
      IO.eprintln "Unsupported completion research profile."; return 2
    match input.rows.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
