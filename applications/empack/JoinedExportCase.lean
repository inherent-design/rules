import Lean
import applications.empack.JoinedExport
open Lean ApplicationStudy.EmpackJoinedExport
private structure Row where
  phase : Nat
  basis : Nat
  current : Nat
  action : Nat
  capture : Nat
  admitted : Bool
  finished : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def run (r : Row) : Except String String := do
  if r.phase > 3 || r.action > 4 || [r.basis,r.current,r.capture].any (· > 4096) then
    throw "Unsupported study state/action/identity."
  if (r.phase == 0) != (r.basis == 0) then throw "Phase lacks a captured basis."
  if r.action == 0 && r.capture == 0 then throw "Begin lacks a captured image."
  let o := step ⟨r.phase,r.basis⟩ r.current r.action r.capture r.admitted r.finished
  pure (String.intercalate "/" [toString o.state.phase,toString o.state.basis,toString o.current,
    toString o.ok,toString o.readable,toString o.mayHaveCopied,toString o.removed])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one research trace."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "joined-research-export" || input.rows.length > 256 then
      IO.eprintln "Unsupported study schema/profile/count."; return 2
    match input.rows.mapM run with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
