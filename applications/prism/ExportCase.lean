import Lean
import applications.prism.Export
open Lean ApplicationStudy.PrismExport
private structure InputEntry where
  id : Nat
  leafHidden : Bool
  excluded : Bool
  missingAtWrite : Bool
  link : Bool
  deriving FromJson
private structure Row where
  id : String
  rootExists : Bool
  outputDirectory : Bool
  canceled : Bool
  follow : Bool
  placement : Nat
  entries : List InputEntry
  extras : List Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure OutputMember where
  id : Nat
  placement : Nat
  link : Bool
  deriving ToJson
private structure View where
  id : String
  selected : List Nat
  state : Nat
  members : List OutputMember
  errorPresent : Bool
  outputReplaced : Bool
  completed : Bool
  deriving ToJson
private def run (r : Row) : Except String View := do
  if r.placement > 1 || r.entries.length > 20 || r.extras.length > 4 ||
      r.entries.any (fun e => e.id > 31) || r.extras.any (· > 31) ||
      (r.entries.map (·.id)).eraseDups.length != r.entries.length ||
      r.extras.eraseDups.length != r.extras.length then
    throw "Unsupported Prism export research profile."
  let req : Request := ⟨r.rootExists,r.outputDirectory,r.canceled,r.follow,r.placement,
    r.entries.map (fun e => ⟨e.id,e.leafHidden,e.excluded,e.missingAtWrite,e.link⟩),r.extras⟩
  return ⟨r.id,if r.rootExists then (selected req.entries).map (·.id) else [],state req,
    (members req).map (fun m => ⟨m.id,m.placement,m.link⟩),errorPresent (state req),
    outputReplaced req,methodCompleted req⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one export research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported Prism export research schema."
    input.cases.mapM run
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
