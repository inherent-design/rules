import Lean
import applications.cargo.Build
open Lean ApplicationStudy.Cargo

private structure Input where
  schema : Nat
  workspace : Bool
  previousSignature : String
  previousValue : String
  signature : String
  actual : String
  outsideOutput : String
  deriving FromJson

private structure Output where
  red : Bool
  blue : Bool
  captured : String
  targetAfterClean : Bool
  outsideAfterClean : String
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Cargo projection JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported Cargo projection schema."
      return 2
    let f := selectedFeatures (if input.workspace then .workspace else .app)
    let c := capture ⟨input.previousSignature, input.previousValue⟩ input.signature input.actual
    let effects := clean ⟨true, input.outsideOutput⟩
    let result : Output := ⟨f.red, f.blue, c.capturedValue, effects.targetPresent, effects.scriptOutputOutsideTarget⟩
    IO.println (toJson result).compress
    return 0
