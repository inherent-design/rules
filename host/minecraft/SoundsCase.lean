import Lean
import host.minecraft.Sounds
open Lean Host.Minecraft.Sounds
private structure InputEntry where
  first : Nat
  second : Nat
  fail : Bool
  deriving FromJson
private structure Row where
  operation : Nat
  entries : List InputEntry
  draw : Nat
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  cases : List Row
  deriving FromJson
private def admit (r : Row) : Except String Outcome := do
  if r.operation > 2 || r.entries.length > 16 || r.draw > 4294967295 then throw "Unselected operation,size or draw word."
  let entries ← r.entries.mapM (fun e => do
    if e.first > 4294967295 || e.second > 4294967295 then throw "Not a32bit word."
    pure (⟨UInt32.ofNat e.first,UInt32.ofNat e.second,e.fail⟩ : Entry))
  let total := sum entries
  if r.operation == 1 && Host.Java.Word32.positive total && r.draw ≥ total.toNat then throw "Draw is outside the observed positive bound."
  if (r.operation != 1 || !Host.Java.Word32.positive total) && r.draw != 0 then throw "No usable random draw in this branch."
  pure (run r.operation entries (UInt32.ofNat r.draw))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one selected sound-control request.";return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "original-sound-weight-controls" || r.cases.length > 64 then
      IO.eprintln "Unselected schema,contract or batch.";return 2
    match r.cases.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok outcomes => IO.println (toJson (outcomes.map fields)).compress;return 0
