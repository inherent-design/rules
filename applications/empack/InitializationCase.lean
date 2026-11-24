import Lean
import applications.empack.Initialization
open Lean ApplicationStudy.EmpackInitialization

private structure Row where
  initial : Nat
  actors : Nat
  events : List Event
  deriving FromJson
private structure Request where
  schema : Nat
  profile : String
  cases : List Row
  deriving FromJson
private def seed (m n : Nat) : State :=
  {slot := m % 2 == 1, operation := m / 2 % 2 == 1,
   metadata := m / 4 % 2 == 1, association := m / 16 % 2 == 1,
   unknown := m / 32 % 2 == 1, actors := List.replicate n {}}
private def checked (r : Row) : Except String State := do
  if r.initial > 63 || r.initial / 8 % 2 == 1 ||
      (r.initial != 0 && r.initial % 2 == 0) then throw "Invalid initial slot projection."
  if r.actors == 0 || r.actors > 16 || r.events.length > 128 then throw "Research trace limit."
  if r.events.any (fun e => e.kind > 7 || e.variant > 1 || e.actor ≥ r.actors) then
    throw "Invalid protocol event."
  pure (run (seed r.initial r.actors) r.events)
private def bit (b : Bool) : String := if b then "1" else "0"
private def actorText (a : Actor) : String := String.intercalate ","
  [toString a.variant,toString a.phase,toString a.api,toString a.command,bit a.scratch,toString a.found]
private def render (s : State) : String := String.intercalate "/"
  ([bit s.valid,toString (mask s),toString (leases s),toString s.writes] ++ s.actors.map actorText)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one initializer research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e; return 2
  | .ok r =>
    if r.schema != 1 || r.profile != "selected-initializer-phases" || r.cases.length > 256 then
      IO.eprintln "Unsupported initializer research schema/profile/count."; return 2
    match r.cases.mapM (fun row => checked row >>= fun s => pure (render s)) with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
