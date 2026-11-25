import Lean
import applications.cargo.Freshness
open Lean ApplicationStudy.CargoFreshness
private structure S where
  scriptValid : Bool
  basis : Nat
  generated : Nat
  rustValid : Bool
  binary : Nat
  macroValue : Nat
  runs : Nat
  deriving FromJson
private structure Row where
  action : Nat
  state : S
  basis : Nat
  dataValue : Nat
  macroValue : Nat
  fail : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def encode (o : Outcome) : String :=
  let s := o.state
  s!"{o.code}/{if o.ran then 1 else 0}/{if o.reported then 1 else 0}/{o.artifactFresh}/{if s.scriptValid then 1 else 0}/{s.basis}/{s.generated}/{if s.rustValid then 1 else 0}/{s.binary}/{s.macroValue}/{s.runs}"
private def runRow (r : Row) : Except String String := do
  if r.action > 1 || r.basis > 16 || r.dataValue > 16 || r.macroValue > 2 || r.state.basis > 16 || r.state.generated > 16 || r.state.binary > 16 then
    throw "Outside the selected freshness catalog."
  if r.action == 0 && (r.basis == 0 || r.dataValue == 0 || r.macroValue == 0) then throw "Build requires admitted labels."
  if r.state.scriptValid && r.state.basis == 0 then throw "Valid script basis cannot be absent."
  if r.state.macroValue > 2 || (r.state.binary == 0) != (r.state.macroValue == 0) then throw "Invalid compiled product label."
  let s : State := ⟨r.state.scriptValid,r.state.basis,r.state.generated,r.state.rustValid,r.state.binary,r.state.macroValue,r.state.runs⟩
  pure (encode (if r.action == 1 then ⟨0,false,false,2,clean s⟩ else build s ⟨r.basis,r.dataValue,r.macroValue,r.fail⟩))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Cargo freshness DTO."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok i =>
    if i.schema != 1 then IO.eprintln "Unsupported freshness DTO schema."; return 2
    match i.cases.mapM runRow with
    | .error e => IO.eprintln e; return 2
    | .ok out => IO.println (toJson out).compress; return 0
