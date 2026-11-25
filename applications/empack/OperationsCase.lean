import Lean
import applications.empack.Operations
open Lean ApplicationStudy.EmpackOperations
private structure Row where
  kind : String
  actions : List Nat
  workers : Nat
  driver : Nat
  fault : Bool
  admissionOpen : Bool
  used : Nat
  maximum : Nat
  terminal : Bool
  value : Nat
  accepting : Bool
  cancelled : Bool
  operation : Bool
  owner : Bool
  attempt : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def bit (b : Bool) : String := if b then "1" else "0"
private def evaluate (r : Row) : Except String String := do
  unless r.workers ≤ 2 && r.driver ≤ 2 && r.value ≤ 4 && r.used ≤ 2 && r.maximum ≤ 2 &&
      r.actions.length ≤ 12 && r.actions.all (· ≤ 4) do throw "Outside admitted runtime slice."
  match r.kind with
  | "entry" => pure (entryText (run ⟨1,r.workers,false,0⟩ r.actions r.driver r.fault))
  | "admission" => pure (toString (admission r.admissionOpen r.used r.maximum))
  | "release" => pure (bit (mayRelease r.terminal))
  | "outcome" => pure (toString (outcome r.driver r.fault))
  | "ordinary" => pure (bit (ordinary ⟨r.accepting,r.cancelled,r.operation,r.owner,r.attempt⟩))
  | "receipt" => pure (bit (receipt ⟨r.accepting,r.cancelled,r.operation,r.owner,r.attempt⟩))
  | "progress" =>
    let s := writeProgress ⟨r.terminal,0⟩ r.value
    pure (bit s.terminal ++ "|" ++ toString s.observation)
  | "presentation" => pure (if (presentProgress ⟨r.terminal,r.value⟩).isSome then "show" else "hide")
  | "evidence" =>
    let e := proposedEvidence r.driver r.fault
    pure (toString e.reported ++ "|" ++ toString e.driver ++ "|" ++ bit e.retirementFault)
  | _ => throw "Unknown runtime comparison kind."
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one runtime research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok v =>
    if v.schema != 1 || v.profile != "empack-operation-runtime-slice" || v.rows.isEmpty || v.rows.length > 64 then
      IO.eprintln "Unsupported runtime research schema/profile/count."; return 2
    match v.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
