import Lean
import host.minecraft.ReloadSchedule
open Lean Host.Minecraft.ReloadSchedule
private structure Row where
  count : Nat
  hasShared : Option Bool
  sharedFailure : Option Bool
  initial : Option Nat
  p0 : Option Nat
  p1 : Option Nat
  barrier0 : Option Bool
  fail0 : Option Bool
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  rows : List Row
  deriving FromJson
private def need {α : Type} (x : Option α) : Except String α :=
  match x with
  | some v => .ok v
  | none => .error "Required reload evidence is unknown."
private def admit (r : Row) : Except String (List Nat) := do
  if r.count == 0 then return evaluate 0 false false 0 0 0 false false
  if r.count != 2 then throw "Outside selected zero/two-listener profile."
  let shared ← need r.hasShared
  if !shared && r.sharedFailure == some true then throw "Selected interface has no shared hook."
  let failed ← if shared then need r.sharedFailure else pure false
  if shared && failed then return evaluate 2 true true 0 0 0 false false
  let initial ← need r.initial
  let p0 ← need r.p0
  let p1 ← need r.p1
  if initial > 2 || p0 > 2 || p1 > 2 then throw "Outside selected future states."
  pure (evaluate 2 shared failed initial p0 p1 (← need r.barrier0) (← need r.fail0))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one reload request.";return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e;return 2
  | .ok r =>
    if r.schema != 1 || r.contract != "direct-two-listener-reload-v1" || r.rows.length > 128 then
      IO.eprintln "Unselected reload schema,contract or batch.";return 2
    match r.rows.mapM admit with
    | .error e => IO.eprintln e;return 2
    | .ok values => IO.println (toJson values).compress;return 0
