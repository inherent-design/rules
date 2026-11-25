import Lean
import host.minecraft.GuiScaling
open Lean Host.Minecraft.GuiScaling
private structure Row where
  kind : Nat
  width : Nat
  height : Nat
  left : Nat
  top : Nat
  right : Nat
  bottom : Nat
  nonnegative : Bool
  scalar : Bool
  modern : Bool
  stretch : Bool
  deriving FromJson
private def Row.toInput (r : Row) : Input :=
  ⟨r.kind,r.width,r.height,r.left,r.top,r.right,r.bottom,r.nonnegative,r.scalar,r.modern,r.stretch⟩
private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson
private def admit (r : Row) : Except String Nat := do
  if r.kind > 2 then throw "Unknown selected GUI variant."
  if [r.width,r.height,r.left,r.top,r.right,r.bottom].any (· > 2147483647) then
    throw "Outside selected signed-positive magnitude domain."
  if r.scalar && (r.left != r.top || r.left != r.right || r.left != r.bottom) then
    throw "Scalar border sides disagree."
  pure (evaluate r.toInput)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one GUI scaling request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "selected-gui-scaling-integers" || r.rows.length > 128 then
      IO.eprintln "Unselected schema,contract or batch.";return 2
    match r.rows.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok values => IO.println (toJson values).compress;return 0
