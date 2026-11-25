import Lean
import applications.«npm-cache».Cache
open Lean ApplicationStudy.NpmCache
private structure Row where
  kind : Nat
  backing : Nat
  installed : Nat
  author : Nat
  referenced : Bool
  lockAdmitted : Bool
  matchingIndex : Bool
  originReady : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def render (v : Result) : String :=
  let b := match v.state.backing with | .missing => 0 | .verified => 1 | .corrupt => 2
  let i := match v.state.installed with | .missing => 0 | .original => 1 | .editedFixture => 2
  String.intercalate "/" ([b,i,v.state.author,v.exitCode,v.requests].map toString)
private def evaluate (r : Row) : Except String Json := do
  if r.kind > 4 || r.backing > 2 || r.installed > 2 || r.author == 0 || r.author > 4096 then throw "Research state bound."
  let b := if r.backing == 0 then Backing.missing else if r.backing == 1 then .verified else .corrupt
  let i := if r.installed == 0 then Installation.missing else if r.installed == 1 then .original else .editedFixture
  let s : State := ⟨b,i,r.author⟩
  let v ← match r.kind with
    | 0 => pure (verify s r.referenced)
    | 1 => pure (cleanInstall s r.lockAdmitted r.matchingIndex r.originReady)
    | 2 => pure (corruptBacking s)
    | 3 => pure (editInstalled s)
    | 4 => pure (Result.mk s 0 0) -- availability observer protocol,not npm API
    | _ => throw "Unknown operation."
  pure (Json.mkObj [("current",toJson (render v)),("available",toJson (available s)),
    ("proposal",if r.kind == 1 then toJson (some (render (proposedPreflight s r.lockAdmitted r.matchingIndex r.originReady))) else toJson (none : Option String))])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one cache research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "owned-single-package-cache" || input.rows.length > 128 then
      IO.eprintln "Unsupported cache research profile."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
