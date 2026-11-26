import Lean
import applications.cargo.RunConfig
open Lean ApplicationStudy.CargoRunConfig
private structure Row where
  packageCwd : Bool
  explicitFile : Bool
  environmentRunner : Bool
  cliRunner : Bool
  invalidEnvironmentJobs : Bool
  cliJobs : Bool
  build : Option Bool
  oldArtifact : Bool
  runnerStatus : Nat
  applicationStatus : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def evaluate (r : Row) : Except String (List Nat × Nat) := do
  let request : Request := ⟨r.packageCwd,r.explicitFile,r.environmentRunner,r.cliRunner,
    r.invalidEnvironmentJobs,r.cliJobs,r.build,r.oldArtifact,r.runnerStatus,r.applicationStatus⟩
  if r.runnerStatus != 0 && r.runnerStatus != 9 then throw "Unsupported generated runner status."
  if r.applicationStatus != 0 && r.applicationStatus != 7 then throw "Unsupported generated application status."
  if configurationAccepted request != r.build.isSome then throw "Build observation does not match configuration admission."
  let o := run request
  pure ([if o.runnerStarted then 1 else 0, if o.applicationStarted then 1 else 0,
    o.executedRunner,o.stage,o.code,o.applicationCwd],runnerId (proposedRunner request))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one configuration/run JSON path."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported Cargo run/configuration schema."; return 2
    match input.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok result => IO.println (toJson result).compress; return 0
