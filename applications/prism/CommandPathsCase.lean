import Lean
import applications.prism.CommandPaths
open Lean ApplicationStudy.PrismCommandPaths

private structure Row where
  id : String
  wrapper : Bool
  units : List Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure Output where
  id : String
  program : List Nat
  preserved : Bool
  deriving ToJson
private def run (row : Row) : Except String Output := do
  if row.units.isEmpty || row.units.length > 4096 || row.units.any (· > 65535) ||
      row.units.contains 34 || row.units.getLast? == some 92 then
    throw "Unsupported quoted-program research profile."
  return ⟨row.id, program row.wrapper row.units, preserved row.wrapper row.units⟩

def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one quoted-program research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported quoted-program research schema."
    input.cases.mapM run
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
