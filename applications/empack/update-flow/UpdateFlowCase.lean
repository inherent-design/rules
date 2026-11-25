import Lean
import applications.empack.«update-flow».UpdateFlow
open Lean ApplicationStudy.UpdateFlow

private def decode : String → Except String Op
  | "syncOld" => .ok .syncOld | "inspect" => .ok .inspect | "held" => .ok .held
  | "unpin" => .ok .unpin | "automaticPreview" => .ok .automaticPreview
  | "exactPreview" => .ok .exactPreview | "applyExact" => .ok .applyExact
  | "checkRecorded" => .ok .checkRecorded | "materialize" => .ok .materialize
  | "checkOnline" => .ok .checkOnline | "bundled" => .ok .bundled
  | "references" => .ok .references | "ensure" => .ok .ensure
  | "checkRecipient" => .ok .checkRecipient
  | _ => .error "Unsupported research operation."

private def sequence : List String := ["syncOld","inspect","held","unpin","inspect",
  "automaticPreview","exactPreview","applyExact","inspect","held","checkRecorded",
  "materialize","checkRecorded","checkOnline","inspect","bundled","references",
  "ensure","ensure","checkRecipient"]

private structure Input where
  schema : Nat
  profile : String
  old : String
  target : String
  operations : List String
  deriving FromJson

def main (args : List String) : IO UInt32 := do
  let path ← match args with | [p] => pure p | _ => throw (IO.userError "Supply one research packet.")
  let raw ← IO.FS.readFile path
  let result := do
    let j ← Json.parse raw
    let input ← fromJson? (α := Input) j
    if input.schema != 1 || input.profile != "ferrite-one-root-snapshot-success/1" ||
        input.old != "wmIZ4wP4" || input.target != "sOzRw3CG" || input.operations != sequence then
      throw "Outside admitted research fixture/sequence."
    let ops ← input.operations.mapM decode
    return trace {} ops
  match result with
  | .error message => (← IO.getStderr).putStrLn message; return 2
  | .ok result => (← IO.getStdout).putStrLn ((toJson result).compress); return 0
