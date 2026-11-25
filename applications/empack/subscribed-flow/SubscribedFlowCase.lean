import Lean
import applications.empack.«subscribed-flow».SubscribedFlow
open Lean ApplicationStudy.SubscribedFlow

private def names : List String := ["enroll","previewA","observeA","installA","playerEdit",
  "previewB","observeB","previewInstallB","missingInputB","installB","checkB","ensureOld",
  "rollbackA","staleA","badSignature","checkRollback"]
private structure Input where
  schema : Nat
  profile : String
  operations : List String
  channelWitness : String
  deriving FromJson

def main (args : List String) : IO UInt32 := do
  let path ← match args with | [p] => pure p | _ => throw (IO.userError "Supply one subscribed research packet.")
  let raw ← IO.FS.readFile path
  let result := do
    let j ← Json.parse raw
    let r ← fromJson? (α := Input) j
    if r.schema != 1 || r.profile != "local-signed-inputs-current-engine/1" ||
       r.channelWitness != "native-valid-A-B-forged-B-and-stale-A" || r.operations != names then
      throw "Outside admitted subscribed research profile."
    return trace {} sequence
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok result => (← IO.getStdout).putStrLn ((toJson result).compress); return 0
