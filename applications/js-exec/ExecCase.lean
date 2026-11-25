import Lean
import applications.«js-exec».Exec
open Lean ApplicationStudy.JsExec
private structure Row where
  app : Nat
  mode : Nat
  dependencyBin : Bool
  inheritedBin : Bool
  cwd : Nat
  arguments : List String
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def evaluate (r : Row) : Except String Json := do
  if r.app > 2 || r.mode > 2 || r.cwd < 1 || r.cwd > 2 || r.arguments.length > 32 ||
      (r.arguments.map String.length).foldl (· + ·) 0 > 4096 then throw "Unsupported execution research value."
  if r.mode == 2 && r.app != 0 then throw "Call mode is npm-specific."
  if r.mode == 1 && r.cwd != 1 then throw "Named-script fixture is admitted at project root only."
  -- Restricted line codec only for the Bend research driver, not a public API.
  if r.arguments.any (fun s => s.contains '|' || s.contains '\n' || s.contains '\r' || s.contains (Char.ofNat 0)) then
    throw "Argument outside research line codec."
  let app := if r.app == 0 then App.npm else if r.app == 1 then .pnpm else .yarn
  let mode := if r.mode == 0 then Mode.exec else if r.mode == 1 then .namedScript else .npmCall
  let v := run app mode ⟨r.dependencyBin,r.inheritedBin,r.cwd,r.arguments⟩
  pure (Json.mkObj [("selected",toJson v.selected),("stage",toJson v.stage),("exitCode",toJson v.exitCode),
    ("cwd",toJson v.cwd),("arguments",toJson v.arguments)])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one execution research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "offline-literal-command-context" || input.rows.length > 128 then
      IO.eprintln "Unsupported execution research profile."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
