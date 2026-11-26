import Lean
import applications.empack.«author-transitions».Admission
open Lean ApplicationStudy.AuthorAdmission
private structure Row where
  id : String
  phase : String
  held : Bool
  version : Nat
  requestPinned : Bool
  missingRoot : Bool
  runtimeMatches : Bool
  deriving FromJson
private structure Packet where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private structure After where
  rootPin : Option String
  roots : List String
  locked : List String
  selected : Nat
  intentPreserved : Bool
  runtime : String
  edges : List String
  coverageComplete : Bool
  deriving ToJson
private structure Result where
  id : String
  accepted : Bool
  error : Option String
  after : Option After
  changed : Option (List String)
  bindings : Option (List String)
  inputUnchanged : Bool
  deriving ToJson
private def run (row : Row) : Except String Result := do
  let phase ← match row.phase with
    | "existing-adopt" => pure Phase.existingAdopt
    | "initial-adopt" => pure Phase.initialAdopt
    | "validate-target" => pure Phase.validateTarget
    | _ => throw "Unsupported research phase."
  if row.version < 1 || row.version > 2 then throw "Unsupported research selection."
  if row.missingRoot && phase != .initialAdopt then throw "Unsupported missing-root profile."
  if phase == .initialAdopt && !row.runtimeMatches then throw "Unsupported initial runtime profile."
  if phase == .validateTarget && row.requestPinned then throw "Target validation does not consume a group pin."
  let request : Request := ⟨phase, row.held, row.version, row.requestPinned, row.missingRoot, row.runtimeMatches⟩
  let after := if accepted request then
    some (⟨authorPin request, ["a"], locked request, row.version, true, runtime request, ["b"], true⟩ : After)
    else none
  return ⟨row.id, accepted request, failure request, after, changed request, bindings request, true⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with | [p] => pure p | _ => throw (IO.userError "Supply one author-admission packet.")
  let raw ← IO.FS.readFile path
  let result := do
    let json ← Json.parse raw
    let packet ← fromJson? (α := Packet) json
    if packet.schema != 1 || packet.profile != "fictional-core-author-admission" then throw "Unsupported research packet."
    if packet.rows.isEmpty || packet.rows.length > 32 then throw "Unsupported research row count."
    if (packet.rows.map (fun (row : Row) => row.id)).eraseDups.length != packet.rows.length then throw "Repeated research identity."
    packet.rows.mapM run
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
