import Lean
import applications.empack.«channel-publication».Publication
open Lean ApplicationStudy.EmpackChannelPublication

private structure Wire where
  id : String
  priorAuthenticated : Bool
  oldSequence : Nat
  sequence : Nat
  sameDocument : Bool
  samePayload : Bool
  sameEnvelope : Bool
  deriving FromJson

private structure Packet where
  schema : Nat
  profile : String
  candidateAdmitted : Bool
  identityAndOriginAdmitted : Bool
  scenarios : List Wire
  deriving FromJson

private structure Observation where
  publisher : Bool
  subscriber : Option Bool
  proposed : Bool
  deriving ToJson

private def runPacket (p : Packet) : Except String (List Observation) := do
  if p.schema != 1 || p.profile != "source-publisher-payload-floor" ||
      !p.candidateAdmitted || !p.identityAndOriginAdmitted then
    throw "Unsupported channel publication research profile."
  if p.scenarios.isEmpty || p.scenarios.length > 32 then
    throw "Unsupported channel publication scenario count."
  p.scenarios.mapM fun w => do
    if w.id.isEmpty || w.oldSequence == 0 || w.sequence == 0 ||
        w.oldSequence > 100 || w.sequence > 100 then
      throw "Unsupported channel publication sequence or identity."
    if (w.samePayload && !w.sameDocument) || (w.sameEnvelope && !w.samePayload) then
      throw "Inconsistent channel identity witnesses."
    let result := run ⟨w.priorAuthenticated,w.oldSequence,w.sequence,w.sameDocument,w.samePayload,w.sameEnvelope⟩
    return ⟨result.publisher,result.subscriber,result.proposed⟩

def main (args : List String) : IO UInt32 := do
  let path ← match args with
    | [p] => pure p
    | _ => throw (IO.userError "Supply one channel publication research packet.")
  let raw ← IO.FS.readFile path
  let result := do
    let json ← Json.parse raw
    let packet ← fromJson? (α := Packet) json
    runPacket packet
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok rows => (← IO.getStdout).putStrLn ((toJson rows).compress); return 0
