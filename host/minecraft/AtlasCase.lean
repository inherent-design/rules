import Lean
import host.minecraft.Atlas
open Lean Host.Minecraft.Atlas
private structure InputAction where
  kind : Nat
  key : Nat
  supplier : Nat
  caught : Bool
  deriving FromJson
private structure Row where
  throwing : Nat
  sources : List (List InputAction)
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  cases : List Row
  deriving FromJson
private def admit (r : Row) : Except String State := do
  if r.throwing > 3 || r.sources.length > 8 || r.sources.any (·.length > 16) then throw "Unselected supplier or size."
  let groups ← r.sources.mapM (fun group => group.mapM (fun a => do
    if a.kind > 2 || (a.kind == 0 && (a.key > 1 || a.supplier == 0 || a.supplier > 3)) ||
       (a.kind == 1 && (a.key > 2 || a.supplier != 0)) || (a.kind == 2 && (a.key != 0 || a.supplier != 0)) then
      throw "Unselected operation,identifier or supplier."
    pure (⟨a.kind,a.key,a.supplier,a.caught⟩ : Action)))
  if !(safeSources {} groups r.throwing) then throw "Throwing multi-target removal needs an actual iteration-order witness."
  pure (sources {} groups r.throwing)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one atlas assembly request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "authored-atlas-output-controls" || r.cases.length > 64 then
      IO.eprintln "Unselected schema,contract or batch.";return 2
    match r.cases.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok states => IO.println (toJson (states.map fields)).compress;return 0
