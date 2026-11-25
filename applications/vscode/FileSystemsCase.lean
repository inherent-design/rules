import Lean
import applications.vscode.FileSystems
open Lean ApplicationStudy.VscodeFileSystems

private structure EventRow where
  id : String
  added : Bool
  providerPresent : Bool
  readonly : Bool
  deriving FromJson
private structure WriteRow where
  id : String
  schemeReadonly : Bool
  backendDenied : Bool
  parentMissing : Bool
  deriving FromJson
private structure QueueRow where
  id : String
  copied : Bool
  mutated : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  events : List EventRow
  writes : List WriteRow
  queues : List QueueRow
  deriving FromJson
private structure EventResult where
  id : String
  current : Nat
  proposed : Nat
  deriving ToJson
private structure WriteResult where
  id : String
  callback : Bool
  refused : Bool
  parentCreated : Bool
  deriving ToJson
private structure QueueResult where
  id : String
  seesMutation : Bool
  deriving ToJson
private structure Output where
  events : List EventResult
  writes : List WriteResult
  queues : List QueueResult
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one filesystem projection JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported filesystem projection schema."
      return 2
    let output : Output := ⟨
      input.events.map (fun r =>
        let e : Registration := ⟨r.added, r.providerPresent, r.readonly⟩
        ⟨r.id, currentKnowledge e, proposedKnowledge e⟩),
      input.writes.map (fun r =>
        let w : WriteRequest := ⟨r.schemeReadonly, r.backendDenied, r.parentMissing⟩
        ⟨r.id, reachesCallback w, refused w, createsParent w⟩),
      input.queues.map (fun r => ⟨r.id, dispatchSeesMutation r.copied r.mutated⟩)⟩
    IO.println (toJson output).compress
    return 0
