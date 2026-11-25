import Lean
import host.minecraft.FontFilter
open Lean Host.Minecraft.FontFilter
private structure Row where
  left : Nat
  right : Nat
  mask : Nat
  merged : Bool
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson
private def admit (r : Row) : Except String Nat := do
  if r.left > 8 || r.right > 8 || r.mask > 3 then throw "Outside the selected two-option universe."
  if !r.merged && r.right != 0 then throw "Direct application has no second filter."
  pure (evaluate r.left r.right r.mask r.merged)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one font-filter request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "original-font-filter-two-options" || r.rows.length > 512 then
      IO.eprintln "Unselected schema,contract or batch.";return 2
    match r.rows.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok values => IO.println (toJson values).compress;return 0
