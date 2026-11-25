import Lean
import applications.«yarn-version».Versions
open Lean ApplicationStudy.YarnVersions
private structure V where
  major : Nat
  minor : Nat
  patch : Nat
  deriving FromJson, ToJson
private def value (v : V) : Version := ⟨v.major,v.minor,v.patch⟩
private def wire (v : Version) : V := ⟨v.major,v.minor,v.patch⟩
private structure Scope where
  id : String
  root : Nat
  recursive : Bool
  deriving FromJson
private structure ScopeOut where
  id : String
  selected : List Nat
  deriving ToJson
private structure Record where
  id : String
  current : V
  target : V
  priorDecision : Bool
  priorBump : Bool
  decline : Bool
  force : Bool
  dryRun : Bool
  deriving FromJson
private structure RecordOut where
  id : String
  accepted : Bool
  decision : Bool
  bump : Bool
  deriving ToJson
private structure Apply where
  id : String
  current : V
  target : V
  hasRelease : Bool
  anySelectedLower : Bool
  force : Bool
  dryRun : Bool
  inputAvailable : Bool
  selected : Bool
  deriving FromJson
private structure ApplyOut where
  id : String
  version : V
  retained : Bool
  announced : Bool
  saved : Bool
  successful : Bool
  deriving ToJson
private structure Check where
  id : String
  changedA : Bool
  changedB : Bool
  changedC : Bool
  decidedA : Bool
  decidedB : Bool
  decidedC : Bool
  bumpA : Bool
  bumpB : Bool
  deriving FromJson
private structure CheckOut where
  id : String
  successful : Bool
  deriving ToJson
private structure Range where
  id : String
  old : V
  target : V
  saved : Bool
  deriving FromJson
private structure RangeOut where
  id : String
  target : V
  deriving ToJson
private structure Input where
  schema : Nat
  scopes : List Scope
  records : List Record
  applies : List Apply
  checks : List Check
  ranges : List Range
  deriving FromJson
private structure Output where
  scopes : List ScopeOut
  records : List RecordOut
  applies : List ApplyOut
  checks : List CheckOut
  ranges : List RangeOut
  deriving ToJson
private def scope (r : Scope) : Except String ScopeOut := do
  if r.root ≥ 3 then throw "Unsupported three-workspace research scope."
  return ⟨r.id, ([2,1,0].filter fun i => dependencyScope r.root i r.recursive)⟩
private def recordOut (r : Record) : RecordOut :=
  let result := record ⟨value r.current,value r.target,r.priorDecision,r.priorBump,r.decline,r.force,r.dryRun⟩
  ⟨r.id,result.accepted,result.decision,result.bump⟩
private def applyOut (r : Apply) : Except String ApplyOut := do
  if r.selected && r.hasRelease && lower (value r.target) (value r.current) && !r.anySelectedLower then
    throw "Inconsistent selected-version research witness."
  let out := apply ⟨value r.current,value r.target,r.hasRelease,r.anySelectedLower,r.force,r.dryRun,r.inputAvailable,r.selected⟩
  return ⟨r.id,wire out.version,out.retained,out.announced,out.saved,out.successful⟩
private def checkOut (r : Check) : CheckOut :=
  ⟨r.id,check r.changedA r.changedB r.changedC r.decidedA r.decidedB r.decidedC r.bumpA r.bumpB⟩
private def rangeOut (r : Range) : RangeOut := ⟨r.id,wire (rangeTarget (value r.old) (value r.target) r.saved)⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one version-intent research packet.")
  let raw ← IO.FS.readFile path
  let out := do
    let j ← Json.parse raw
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported version-intent research schema."
    let scopes ← input.scopes.mapM scope
    let applies ← input.applies.mapM applyOut
    return (⟨scopes,input.records.map recordOut,applies,input.checks.map checkOut,input.ranges.map rangeOut⟩ : Output)
  match out with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok result => (← IO.getStdout).putStrLn ((toJson result).compress); return 0
