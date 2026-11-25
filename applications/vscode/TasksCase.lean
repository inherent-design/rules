import Lean
import applications.vscode.Tasks
open Lean ApplicationStudy.VscodeTasks

private structure RawEvent where
  kind : Nat
  task : Nat
  deriving FromJson
private structure Row where
  kind : String
  events : List RawEvent := []
  worker : Bool := false
  execution : Nat := 0
  preserved : Bool := false
  enabled : Bool := false
  registered : Bool := false
  count : Nat := 0
  background : Bool := false
  watching : Bool := false
  inactive : Bool := false
  exited : Bool := false
  pid : Int := 0
  bound : Bool := false
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson

private def bit (v : Bool) : String := if v then "1" else "0"
private def evaluate (r : Row) : Except String String := do
  match r.kind with
  | "trace" =>
    unless !r.events.isEmpty && r.events.length ≤ 64 && r.events.all (fun e =>
        e.kind ≤ 6 && e.task ≤ 5 && (e.kind == 0 || e.task > 0)) do
      throw "Outside admitted task trace."
    pure (traceText (r.events.map fun e => ⟨e.kind, e.task⟩))
  | "admit" =>
    unless r.execution ≤ 3 do throw "Unknown execution kind."
    pure (bit (admits r.worker r.execution r.preserved))
  | "discovery" =>
    unless r.count ≤ 1 do throw "Outside single-provider fixture."
    pure (toString (discover r.enabled r.registered r.count))
  | "dependency" => pure (bit (dependencyReady r.background r.watching r.inactive r.exited))
  | "pid" =>
    unless r.pid == -1 || r.pid == 0 || r.pid == 1 do throw "Unnormalized PID sign witness."
    pure (bit (maySignal r.pid r.bound))
  | _ => throw "Unknown task comparison kind."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one task research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "vscode-task-api-slice" ||
        input.rows.isEmpty || input.rows.length > 64 then
      IO.eprintln "Unsupported task research schema, profile, or count."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
