import Lean
import applications.vscode.WebDraft
open Lean ApplicationStudy.VscodeWeb

private structure Input where
  schema : Nat
  logicalResourceKey : String
  renderedMarker : String
  deriving FromJson

private structure Output where
  logicalResourceKey : String
  renderedMarker : String
  dirty : Bool
  fileWriteReceipt : Option String
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one restored-untitled observation input."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported untitled observation schema."
      return 2
    let restored := restoredUntitled input.logicalResourceKey input.renderedMarker
    let result : Output := ⟨restored.resourceKey, restored.renderedText, restored.dirty, restored.fileWriteReceipt⟩
    IO.println (toJson result).compress
    return 0
