import Lean
import applications.empack.Authoring
open Lean ApplicationStudy.EmpackAuthoring

private structure RawEditor where
  epoch : Nat
  current : Nat
  saved : Option Nat
  savedRevision : Nat
  deriving FromJson

private structure Action where
  kind : String
  image : Nat
  epoch : Nat
  revision : Nat
  project : Nat
  incarnation : Nat
  confirmed : Bool
  deriving FromJson

private structure Readiness where
  id : String
  valid : Bool
  complete : Bool
  capable : Bool
  available : List Nat
  missing : List Nat
  required : List Nat
  held : List Nat
  deriving FromJson

private structure Retained where
  saved : List Nat
  current : List Nat
  history : List Nat
  plans : List Nat
  pending : List Nat
  stored : List Nat
  deriving FromJson

private structure Input where
  schema : Nat
  project : Nat
  incarnation : Nat
  initial : RawEditor
  actions : List Action
  readiness : List Readiness
  retention : Retained
  deriving FromJson

private structure EditorOutput where
  kind : String
  epoch : String
  current : String
  saved : Option String
  savedRevision : String
  unsaved : Bool
  backgroundAccepted : Option Bool
  deriving ToJson

private structure ReadinessOutput where
  id : String
  canSave : Bool
  canExport : Bool
  deriving ToJson

private structure Output where
  editor : List EditorOutput
  readiness : List ReadinessOutput
  collected : List Nat
  deriving ToJson

private def runActions (context : Context) : List Action → Except String (List EditorOutput)
  | [] => .ok []
  | action :: rest => do
    let next ← match action.kind with
      | "observe" | "background" => pure context
      | "edit" => pure { context with editor := editTo context.editor action.image }
      | "save" => pure (acceptSave context ⟨action.project, action.incarnation, action.revision, action.image, action.confirmed⟩)
      | unknown => throw ("Unsupported proposed authoring action: " ++ unknown)
    let accepted := if action.kind == "background" then
      some (acceptsBackground next.editor action.epoch action.image) else none
    let output : EditorOutput := ⟨action.kind, toString next.editor.epoch, toString next.editor.current,
      next.editor.saved.map toString, toString next.editor.savedRevision, dirty next.editor, accepted⟩
    return output :: (← runActions next rest)

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one proposed authoring input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported proposed authoring schema."
      return 2
    let initial : Editor := ⟨input.initial.epoch, input.initial.current, input.initial.saved, input.initial.savedRevision⟩
    match runActions ⟨input.project, input.incarnation, initial⟩ input.actions with
    | .error error => IO.eprintln error; return 2
    | .ok editor =>
      let readiness := input.readiness.map fun c =>
        let image : DraftImage := ⟨0, c.valid, c.available, c.missing⟩
        let plan : ExportPlan := ⟨0, c.valid, c.complete, c.capable, c.required⟩
        ReadinessOutput.mk c.id (canSave image c.held) (canExport plan c.held)
      let r := input.retention
      let retained : Retention := ⟨r.saved, r.current, r.history, r.plans, r.pending⟩
      let output : Output := ⟨editor, readiness, Lifecycle.gc (roots retained) r.stored⟩
      IO.println (toJson output).compress
      return 0
