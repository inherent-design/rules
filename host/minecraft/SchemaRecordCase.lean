import Lean
import host.minecraft.SchemaRecord
open Lean MinecraftHost.CodecUI

private structure Row where
  form : Nat
  input : Nat
  deriving FromJson
private structure Envelope where
  schema : Nat
  contract : String
  cases : List Row
  deriving FromJson

private def runCase (row : Row) : Except String (List Nat) := do
  let form ← match row.form with
    | 0 => pure Form.required | 1 => pure Form.optionalWrapper | 2 => pure Form.defaultZero
    | 3 => pure Form.defaultNull | 4 => pure Form.mapRequired | 5 => pure Form.mapDefaultTwo
    | _ => throw "Unselected record form."
  let input ← match row.input with
    | 0 => pure Input.missing | 1 => pure Input.zero | 2 => pure Input.seven
    | 3 => pure Input.wrongType | 4 => pure Input.nullValue
    | _ => throw "Unselected input grammar."
  let r := evaluate form input
  pure [r.advertisedOptional.toNat, r.advertisedDefaultPresent.toNat, r.advertisedDefault,
        r.success.toNat, r.valuePresent.toNat, r.value, r.encodedField.toNat]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one record contract request."; return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Envelope) with
  | .error e => IO.eprintln e; return 2
  | .ok request =>
    if request.schema != 1 || request.contract != "codecui-1.21.1-1.4.10-dfu8-one-field" || request.cases.length > 64 then
      IO.eprintln "Unselected contract, schema, or bounded batch."; return 2
    match request.cases.mapM runCase with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
