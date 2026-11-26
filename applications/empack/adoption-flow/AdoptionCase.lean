import Lean
import applications.empack.«adoption-flow».Adoption
open Lean ApplicationStudy.AdoptionFlow
private structure Row where
  id : String
  firstLock : Bool
  allRoots : Bool
  repeated : Bool
  localSource : Bool
  sourceBytes : Nat
  installedBytes : Nat
  acceptedBefore : Nat
  preview : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure View where
  id : String
  reason : Nat
  candidate : Nat
  acceptedAfter : Nat
  documentsChanged : Bool
  installedAfter : Nat
  deriving ToJson
private def run (r : Row) : Except String View := do
  if r.sourceBytes > 2 || r.installedBytes > 2 || r.acceptedBefore > 2 ||
      (r.firstLock && r.acceptedBefore != 0) || (!r.firstLock && r.acceptedBefore == 0) ||
      (r.localSource && r.sourceBytes == 0) || (!r.localSource && r.sourceBytes != 0) then
    throw "Unsupported observed-file adoption profile."
  let req : Request := ⟨r.firstLock,r.allRoots,r.repeated,r.localSource,r.sourceBytes,r.installedBytes,r.acceptedBefore,r.preview⟩
  return ⟨r.id,reason req,candidate req,acceptedAfter req,documentsChanged req,(transition req).installed⟩
def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one adoption research packet.")
  let text ← IO.FS.readFile path
  let result := do
    let j ← Json.parse text
    let input ← fromJson? (α := Input) j
    if input.schema != 1 then throw "Unsupported observed-file adoption schema."
    input.cases.mapM run
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
