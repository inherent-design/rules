import Lean
import applications.vscode.Configuration
open Lean ApplicationStudy.VscodeConfiguration

private structure Row where
  id : String
  slots : List Json
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def decodeSlot (value : Json) : Except String (Option Json) := do
  let present ← value.getObjValAs? Bool "present"
  let fields ← value.getObj?
  if present then
    if fields.size != 2 then throw "Present carrier needs exactly present and value."
    return some (← value.getObjVal? "value")
  if fields.size != 1 then throw "Absent carrier must not contain a value."
  return none

private def shallowEnough : Nat → Json → Bool
  | 0, _ => false
  | n + 1, .obj fields => fields.all fun _ value => shallowEnough n value
  | n + 1, .arr values => values.all (shallowEnough n)
  | _ + 1, _ => true

private def simulate (row : Row) : Except String Json := do
  if row.slots.length != 8 then throw "Configuration profile requires eight ordered slots."
  let slots ← row.slots.mapM decodeSlot
  if !(slots.all fun slot => slot.all (shallowEnough 16)) then
    throw "Configuration value exceeds the captured depth bound."
  let result := match resolve slots with
    | none => Json.mkObj [("present", .bool false)]
    | some value => Json.mkObj [("present", .bool true), ("value", value)]
  return Json.mkObj [("id", .str row.id), ("effective", result)]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one configuration input JSON path."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported configuration schema."; return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
