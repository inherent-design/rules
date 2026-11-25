import Lean
import applications.empack.Bootstrap
open Lean ApplicationStudy.EmpackBootstrap
private structure Row where
  recordOk : Bool
  optionsOk : Bool
  explicit : Bool
  localState : Nat
  cache : Nat
  versionOk : Bool
  protocolOk : Bool
  termination : Nat
  childResult : Int
  deriving FromJson
private structure Data where
  schema : Nat
  cases : List Row
  deriving FromJson
private def encode (o : Outcome) : String :=
  s!"{o.parent}/{o.engine}/{if o.cacheOpened then 1 else 0}/{if o.delegated then 1 else 0}/{o.child.map toString |>.getD "-"}/{o.cancellation}"
private def runRow (r : Row) : Except String String := do
  if r.localState > 2 || r.cache > 2 || r.termination > 2 || !(r.childResult == 0 || r.childResult == 7) then
    throw "Outside selected bootstrap profile."
  pure (encode (evaluate ⟨r.recordOk,r.optionsOk,r.explicit,r.localState,r.cache,r.versionOk,r.protocolOk,r.termination,r.childResult⟩))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one bootstrap-study DTO."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Data) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported bootstrap-study schema."; return 2
    match input.cases.mapM runRow with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
