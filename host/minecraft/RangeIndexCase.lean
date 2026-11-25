import Lean
import host.minecraft.RangeIndex
open Lean

private structure Row where
  kind : String
  values : List Nat
  query : Nat
  present : Bool
  index : Nat
  found : Bool
  deriving FromJson
private structure Envelope where
  schema : Nat
  target : String
  hostContract : String
  cases : List Row
  deriving FromJson

private def evaluate (r : Row) : Except String Bool := do
  if r.values.length > 32 || r.values.any (· > 33) || r.query > 33 || r.index > 32 then
    throw "Unselected ordered integer-valued float profile."
  if !Host.Java.ArraySearch.sorted r.values then throw "Unsorted input outside this contract."
  let result := if r.present then some r.index else none
  match r.kind with
  | "game-floor" =>
    if !r.present && r.index != 0 then throw "Noncanonical absent floor."
    pure (MinecraftHost.RangeIndex.admitted r.values r.query result)
  | "api-result" => pure (Host.Java.ArraySearch.binaryResultAllowed r.values r.query r.found r.index)
  | "api-floor" =>
    if !r.present && r.index != 0 then throw "Noncanonical absent floor."
    pure (Host.Java.ArraySearch.binaryFloorAllowed r.values r.query result)
  | _ => throw "Unsupported search contract."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one range-contract request."; return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Envelope) with
  | .error e => IO.eprintln e; return 2
  | .ok r =>
    if r.schema != 1 || r.target != "java-1.21.4-vanilla" || r.hostContract != "java17-21-25-arrays-float-ordered-integer-subset" then
      IO.eprintln "Unselected schema, target, or host contract."; return 2
    match r.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
