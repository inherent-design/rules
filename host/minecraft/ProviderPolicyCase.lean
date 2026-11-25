import Lean
import host.minecraft.ProviderPolicy
open Lean Host.Minecraft.ProviderPolicy
private structure Row where
  selected : Option Bool
  rotation : Option Nat
  items : Option Nat
  client : Option Bool
  modefite : Option Nat
  polytone : Option Bool
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson
private def need {α : Type} (x : Option α) : Except String α :=
  match x with
  | some v => .ok v
  | none => .error "Required provider-policy evidence is unknown."
private def admit (r : Row) : Except String (List Nat) := do
  let selected ← need r.selected
  if !selected then return evaluate false false false false 0 false
  let rotation ← need r.rotation
  let items ← need r.items
  if rotation > 2 || items > 2 then throw "Outside selected false/true/omitted settings."
  let a := setting rotation
  let b := setting items
  if !a && !b then return evaluate true false false false 0 false
  let client ← need r.client
  if !client then return evaluate true a b false 0 false
  let version ← need r.modefite
  if version > 2 then throw "Outside selected absent/exact/other metadata."
  pure (evaluate true a b true version false)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one provider-policy request.";return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "isolated-compat-model-policy-v1" || r.rows.length > 128 then
      IO.eprintln "Unselected provider-policy schema,contract or batch.";return 2
    match r.rows.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok values => IO.println (toJson values).compress;return 0
