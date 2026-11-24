import Lean
import applications.«js-scripts».Workspaces
open Lean ApplicationStudy.Workspaces

private structure PackageInput where
  id : Nat
  name : String
  dependencies : List Nat
  script : Bool
  deriving FromJson

private structure Row where
  app : Nat
  mode : Nat
  topological : Bool
  bail : Bool
  ifPresent : Bool
  failB : Bool
  packages : List PackageInput
  deriving FromJson

private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def simulate (row : Row) : Except String Json := do
  let manager ← match row.app with
    | 0 => pure Manager.npm | 1 => pure Manager.pnpm | 2 => pure Manager.yarn
    | _ => throw "Unknown workspace manager."
  if row.mode > 6 then throw "Unknown workspace selector."
  if row.packages.length != 5 || row.packages.map (·.id) != [0,1,2,3,4] then
    throw "Workspace package order is outside the captured profile."
  if row.packages.map (·.dependencies) != [[],[2],[],[],[]] then
    throw "Workspace dependency graph is outside the captured profile."
  let packages := row.packages.map fun p => Package.mk p.id p.name p.dependencies p.script
  let result := run ⟨manager,packages,row.mode,row.topological,row.bail,row.ifPresent,row.failB⟩
  return Json.mkObj [("selected", toJson result.selected), ("started", toJson result.started),
    ("failed", toJson result.failed), ("blocked", toJson result.blocked), ("code", toJson result.code)]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one workspace request JSON input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported workspace schema."; return 2
    match input.cases.mapM simulate with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
