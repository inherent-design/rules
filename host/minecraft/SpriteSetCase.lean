import Lean
import host.minecraft.SpriteSet
open Lean Host.Minecraft.SpriteSet
private structure RequestAction where
  kind : Nat
  values : List Nat
  index : Int
  max : Int
  value : Nat
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  firstAvailable : Bool
  cases : List (List RequestAction)
  deriving FromJson
private def admit (firstAvailable : Bool) (rows : List RequestAction) : Except String (List (List Nat)) := do
  if rows.length > 32 then throw "Unselected program length."
  let mut state : State := {}
  let mut result := []
  for r in rows do
    if r.kind > 4 || r.values.length > 8 || r.values.any (· > 3) || r.value > 3 then throw "Unselected operation or identity."
    if r.index < -16 || r.index > 16 || r.max < -16 || r.max > 16 then throw "Outside the nonoverflow signed fixture."
    if r.kind == 4 && !firstAvailable then throw "First is not available on this selected helper."
    if r.kind != 0 && !r.values.isEmpty then throw "Values belong only to bind."
    if r.kind == 2 && (!state.inputKnown || r.index < 0 || r.index ≥ Int.ofNat state.input.length) then
      throw "Input mutation needs an admitted current list and index."
    let o := step state ⟨r.kind,r.values,r.index,r.max,r.value⟩
    result := result ++ [fields o]
    state := o.state
  pure result
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one sprite-set control request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "original-sprite-set-controls" || r.cases.length > 32 then
      IO.eprintln "Unselected schema,contract or batch.";return 2
    match r.cases.mapM (admit r.firstAvailable) with
    | .error e => IO.eprintln e;return 2
    | .ok results => IO.println (toJson results).compress;return 0
