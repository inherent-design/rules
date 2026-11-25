import Lean
import applications.restic.Keys
open Lean ApplicationStudy.ResticKeys
private structure Row where
  a : Bool
  b : Bool
  c : Bool
  backing : Nat
  kind : Nat
  password : Nat
  hint : Nat
  target : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def evaluate (r : Row) : Except String String := do
  if r.kind > 4 || r.password < 1 || r.password > 3 || r.hint > 3 || r.target > 4 ||
      r.backing == 0 || r.backing > 4096 then throw "Unsupported key-custody research value."
  let s : State := ⟨r.a,r.b,r.c,r.backing⟩
  let current := access s r.password r.hint
  if current != 0 then
    if r.kind == 1 && (current != 1 || r.b) then throw "Unqualified new-wrapper profile."
    if r.kind == 2 && (current != 1 || r.c) then throw "Unqualified password-change profile."
    if !accepts s r.hint r.password && r.password == 1 && r.a && r.b then
      throw "Ambiguous unhinted wrapper order not qualified."
  let v := run s r.kind r.password r.hint r.target
  pure (String.intercalate "/" ([if v.state.a then 1 else 0,if v.state.b then 1 else 0,
    if v.state.c then 1 else 0,v.state.backing,v.exitCode,v.current].map toString))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one key research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "three-wrapper-local-repository" || input.rows.length > 128 then
      IO.eprintln "Unsupported key-custody research profile."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
