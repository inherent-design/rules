import Lean
import applications.cargo.Workspaces
open Lean ApplicationStudy.CargoWorkspaces

private structure Row where
  rootPackage : Bool
  explicitA : Bool
  memberB : Bool
  mode : Nat
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def simulate (row : Row) : Except String Json := do
  let mode ← match row.mode with
    | 0 => pure Mode.defaultRequest | 1 => pure Mode.workspaceExcludeB
    | 2 => pure Mode.explicitA | 3 => pure Mode.invalidExclude
    | _ => throw "Unknown Cargo workspace request."
  let p : Profile := ⟨row.rootPackage,row.explicitA,row.memberB⟩
  return Json.mkObj [("members",toJson (members p)),("defaults",toJson (defaults p)),
    ("selected",toJson (selection p mode)),("checked",toJson (checked p mode)),
    ("code",toJson (if mode == .invalidExclude then 101 else 0 : Nat))]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Cargo workspace JSON input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported Cargo workspace schema."; return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
