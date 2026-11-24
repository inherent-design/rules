import Lean
import applications.vscode.Handles
open Lean ApplicationStudy.VscodeHandles

private structure Row where
  id : String
  firstFile : Bool
  secondFile : Bool
  sameEntry : Bool
  freshReceiver : Bool
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private structure Output where
  id : String
  secondSuffix : Bool
  currentIsFirst : Bool
  currentIsSecond : Bool
  persistedIsFirst : Bool
  persistedIsSecond : Bool
  deriving ToJson

private def simulate (row : Row) : Except String Output := do
  if row.sameEntry && row.firstFile != row.secondFile then
    throw "One underlying handle cannot be both a file and a directory."
  let p : PairInput := ⟨row.firstFile, row.secondFile, row.sameEntry, row.freshReceiver⟩
  return ⟨row.id, secondGetsSuffix p, currentIsFirst p, currentIsSecond p, persistedIsFirst p, persistedIsSecond p⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one handle-pair input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported handle-pair schema."
      return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
