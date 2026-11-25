import Lean
import applications.«npm-manifest».Manifest
open Lean ApplicationStudy.NpmManifest
private structure Query where
  id : String
  preserveArrays : Bool
  wrapped : Bool
  querySucceeded : Bool
  fieldPresent : Bool
  isArray : Bool
  length : Nat
  leafTruthy : Bool
  deriving FromJson
private structure SaveStep where
  valid : Bool
  changes : Bool
  deriving FromJson
private structure Save where
  id : String
  steps : List SaveStep
  deriving FromJson
private structure AppendRow where
  id : String
  countBefore : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  queries : List Query
  saves : List Save
  appends : List AppendRow
  deriving FromJson
private structure QueryOut where
  id : String
  dataWritten : Bool
  currentIsArray : Bool
  displayCandidateWritten : Bool
  shapeCandidateWritten : Bool
  shapeCandidateIsArray : Bool
  deriving ToJson
private structure SaveOut where
  id : String
  attempted : Nat
  changedFiles : Nat
  successful : Bool
  deriving ToJson
private structure AppendOut where
  id : String
  countAfter : Nat
  deriving ToJson
private structure Output where
  queries : List QueryOut
  saves : List SaveOut
  appends : List AppendOut
  deriving ToJson
private def query (r : Query) : Except String QueryOut := do
  if (!r.fieldPresent && r.isArray) || (!r.isArray && r.length != 0) then
    throw "Unsupported manifest-query research profile."
  let p := producer r.preserveArrays r.wrapped r.fieldPresent r.isArray r.length r.leafTruthy
  let shape := producer true r.wrapped r.fieldPresent r.isArray r.length r.leafTruthy
  return ⟨r.id, r.querySucceeded && currentEmission p,
    r.querySucceeded && policyArray r.preserveArrays r.wrapped r.fieldPresent r.isArray r.length,
    r.querySucceeded && displayCandidate p, r.querySucceeded && displayCandidate shape,
    r.querySucceeded && policyArray true r.wrapped r.fieldPresent r.isArray r.length⟩
private def save (r : Save) : SaveOut :=
  let result := execute (r.steps.map fun s => ⟨s.valid,s.changes⟩)
  ⟨r.id,result.attempted,result.changedFiles,result.successful⟩
private def appendResult (r : AppendRow) : AppendOut := ⟨r.id,appendCount r.countBefore⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one manifest research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported manifest research schema."
    let qs ← input.queries.mapM query
    return (⟨qs, input.saves.map save, input.appends.map appendResult⟩ : Output)
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok output => (← IO.getStdout).putStrLn ((toJson output).compress); return 0
