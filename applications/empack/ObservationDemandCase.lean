import Lean
import applications.empack.ObservationDemand
open Lean ApplicationStudy.EmpackObservation ApplicationStudy.EmpackOwnership

private structure Row where
  role : String
  kind : String
  knownBytes : Bool
  seed : Bool
  explicitChange : Bool
  deriving FromJson

private structure Input where
  schema : Nat
  size : Nat
  maximum : Nat
  cases : List Row
  deriving FromJson

private structure Output where
  currentByteGate : Bool
  proposed : List String
  deriving ToJson

private def classify (r : Row) : Except String String := do
  let role ← match r.role with
    | "installed-destination" => pure Role.installedDestination
    | "distribution-source" => pure Role.distributionSource
    | _ => throw "Unknown observation role."
  if r.kind != "regular" && r.knownBytes then
    throw "Only a regular-file observation can contain these byte facts."
  let evidence ← match r.kind with
    | "unavailable" => pure Evidence.unavailable
    | "absent" => pure Evidence.absent
    | "directory" => pure Evidence.directory
    | "regular" => pure (Evidence.regular (if r.knownBytes then some ⟨1, 1, false, false⟩ else none))
    | _ => throw "Unknown observed shape."
  pure (label (nextStep role (if r.seed then .seed else .managed) r.explicitChange evidence))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one observation-demand input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported observation-demand schema."
      return 2
    match input.cases.mapM classify with
    | .error error => IO.eprintln error; return 2
    | .ok proposed =>
      let output : Output := ⟨currentByteGate input.size input.maximum, proposed⟩
      IO.println (toJson output).compress
      return 0
