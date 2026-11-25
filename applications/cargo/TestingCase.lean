import Lean
import applications.cargo.Testing
open Lean ApplicationStudy.CargoTesting
private structure Row where
  id : String
  scope : Nat
  filter : Nat
  noRun : Bool
  keepGoing : Bool
  failUnit : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure Output where
  id : String
  invoked : List Nat
  bodies : List Nat
  successful : Bool
  refused : Bool
  deriving ToJson
private def apply (r : Row) : Except String Output := do
  if r.scope > 4 || r.filter > 3 || (r.filter != 0 && r.scope != 1 && !(r.scope == 2 && r.filter == 2)) then
    throw "Unsupported test-execution research profile."
  let result := run r.scope r.filter r.noRun r.keepGoing r.failUnit
  return ⟨r.id, result.invoked, result.bodies, result.successful, result.refused⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one test-execution research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported test-execution research schema."
    input.cases.mapM apply
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
