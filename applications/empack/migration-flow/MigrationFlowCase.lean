import Lean
import applications.empack.«migration-flow».MigrationFlow
open Lean ApplicationStudy.MigrationFlow
private structure Wire where
  id : String
  project : String
  action : String
  deriving FromJson
private structure Packet where
  schema : Nat
  profile : String
  steps : List Wire
  deriving FromJson
private structure StateOut where
  pin : Nat
  selected : Nat
  game : Nat
  payload : Nat
  deriving ToJson
private def stateOut (s : State) : StateOut := ⟨s.pin,s.selected,s.game,s.payload⟩
private structure Observation where
  id : String
  project : String
  before : StateOut
  after : StateOut
  exit : Nat
  projectChanges : List String
  stateChanged : Bool
  cacheChanged : Bool
  facet : List Nat
  deriving ToJson
private def order : List (String × String × String) := [
  ("compatible-sync","compatible","sync"),
  ("global-prefix-preview","compatible","prefix-preview"),
  ("compatible-preview","compatible","preview"),
  ("compatible-apply","compatible","apply"),
  ("compatible-check","compatible","check"),
  ("incompatible-sync","incompatible","sync"),
  ("incompatible-preview","incompatible","preview"),
  ("incompatible-apply","incompatible","apply"),
  ("explicit-unpin","incompatible","unpin"),
  ("automatic-preview","incompatible","preview"),
  ("automatic-apply","incompatible","apply"),
  ("automatic-check","incompatible","check")]
private def action : String → Except String Op
  | "sync" => .ok .sync | "prefix-preview" => .ok .prefixPreview
  | "preview" => .ok .preview | "apply" => .ok .apply
  | "unpin" => .ok .unpin | "check" => .ok .check
  | _ => .error "Unsupported migration research action."
private def run (packet : Packet) : Except String (List Observation) := do
  if packet.schema != 1 || packet.profile != "released-two-project-target-validation" then
    throw "Unsupported migration research profile."
  if packet.steps.length != order.length then throw "Unsupported migration research step count."
  let mut first : State := ⟨1,0,1,0⟩
  let mut second : State := ⟨2,0,1,0⟩
  let mut observations : List Observation := []
  for (wire, expected) in packet.steps.zip order do
    let op ← action wire.action
    if wire.project != expected.2.1 then throw "Unsupported migration research project order."
    if wire.id != expected.1 || wire.action != expected.2.2 then throw "Unsupported migration research operation order."
    let before := if wire.project == "compatible" then first else second
    let after := step before op
    observations := observations ++ [⟨wire.id,wire.project,stateOut before,stateOut after,code before op,
      projectChanges before op,stateChanged before op,false,facet before op⟩]
    if wire.project == "compatible" then first := after else second := after
  return observations
def main (args : List String) : IO UInt32 := do
  let path ← match args with | [p] => pure p | _ => throw (IO.userError "Supply one migration research packet.")
  let raw ← IO.FS.readFile path
  let result := do
    let json ← Json.parse raw
    let packet ← fromJson? (α := Packet) json
    run packet
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
