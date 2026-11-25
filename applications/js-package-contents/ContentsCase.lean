import Lean
import applications.«js-package-contents».Contents
open Lean ApplicationStudy.PackageContents
private structure Row where
  id : String
  manager : Nat
  kind : Nat
  globalExcluded : Bool
  required : Bool
  filesPresent : Bool
  listed : Bool
  npmPresent : Bool
  npmMatch : Bool
  gitMatch : Bool
  nestedMatch : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure Output where
  id : String
  included : Bool
  deriving ToJson
private def run (r : Row) : Except String Output := do
  if r.manager > 2 || r.kind > 3 then throw "Unsupported package-content research profile."
  return ⟨r.id, included r.manager r.kind r.globalExcluded r.required r.filesPresent r.listed r.npmPresent r.npmMatch r.gitMatch r.nestedMatch⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one package-content research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported package-content research schema."
    input.cases.mapM run
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
