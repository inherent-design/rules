import Lean
import applications.empack.Java
open Lean ApplicationStudy.EmpackJava

private structure ProfileRow where
  game : String
  historical : Nat
  supported : List Nat
  deriving FromJson
private structure BoundRow where
  minimum : Nat
  maximum : Option Nat
  deriving FromJson
private structure Row where
  game : String
  bounds : List BoundRow
  preferred : Option Nat
  actual : Option Nat
  deriving FromJson
private structure Input where
  schema : Nat
  profiles : List ProfileRow
  cases : List Row
  deriving FromJson

private def output (outcome : Outcome) : Json := Json.mkObj [
  ("historical", toJson outcome.policy.historical), ("minimum", toJson outcome.policy.minimum),
  ("supported", toJson outcome.policy.supported), ("recommended", toJson (recommended outcome.policy)),
  ("stage", toJson outcome.stage), ("selected", toJson outcome.selected)]

private def runCases (input : Input) : Except String (List Json) := do
  if input.schema != 1 then throw "Unsupported Java research schema."
  let ids := input.profiles.map (·.game)
  if ids.eraseDups.length != ids.length then throw "Duplicate exact game identity."
  for p in input.profiles do
    if p.supported.isEmpty || p.supported.any (fun n => n < max 8 p.historical || n > 65535) ||
        !p.supported.Pairwise (fun a b => a < b) then
      throw "Profile requires an ordered finite admitted set."
  let profiles := input.profiles.map (fun p => Profile.mk p.game p.historical p.supported)
  input.cases.mapM fun row => do
    if row.actual.isSome && row.preferred.isNone then throw "Actual check needs an explicit preference."
    if row.preferred.any (· > 65535) || row.actual.any (· > 65535) ||
        row.bounds.any (fun b => b.minimum > 65535 || b.maximum.any (· > 65535)) then
      throw "Java major exceeds the source u16 domain."
    pure (output (evaluate (forGame profiles row.game)
      (row.bounds.map (fun b => ⟨b.minimum,b.maximum⟩)) row.preferred row.actual))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Java policy research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input => match runCases input with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
