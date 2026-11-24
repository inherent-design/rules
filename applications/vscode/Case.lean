import Lean
import applications.vscode.Document
open Lean ApplicationStudy.Vscode

private structure Input where
  schema : Nat
  operations : List String
  deriving FromJson

private structure Output where
  operation : String
  version : String
  dirty : Bool
  buffer : String
  disk : String
  deriving ToJson

private def advance (d : Document) : String → Except String Document
  | "open" | "quit-requested" => .ok d
  | "edit-one" => .ok (edit d ⟨"one", "draft-one\n"⟩)
  | "edit-two" => .ok (edit d ⟨"two", "draft-two\n"⟩)
  | "save" => .ok (save d)
  | "undo" => .ok (historyMove d d.saved)
  | "redo" => .ok (historyMove d ⟨"two", "draft-two\n"⟩)
  | "external-clean" => .ok (externalWrite d ⟨"external-clean", "external-clean\n"⟩)
  | "edit-dirty" => .ok (edit d ⟨"local", "local-unsaved\n"⟩)
  | "external-dirty" => .ok (externalWrite d ⟨"external-dirty", "external-dirty\n"⟩)
  | "revert" => .ok (revert d "external-dirty")
  | name => .error ("Unsupported serial fixture operation: " ++ name)

private def simulate (state : Document) : List String → Except String (List Output)
  | [] => .ok []
  | name :: tail => do
    let after ← advance state name
    let rest ← simulate after tail
    return ⟨name, toString after.version, dirty after, after.current.text, after.disk⟩ :: rest

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one serial-document input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported serial-document schema."
      return 2
    let original := Point.mk "original" "original\n"
    match simulate ⟨1, original, original, original.text⟩ input.operations with
    | .error error => IO.eprintln error; return 2
    | .ok out => IO.println (toJson out).compress; return 0
