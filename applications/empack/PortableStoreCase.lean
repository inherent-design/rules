import Lean
import applications.empack.PortableStore
open Lean ApplicationStudy.EmpackPortableStore ApplicationStudy.EmpackAuthoring
private structure StoreRow where
  revision : Nat
  image : Option Nat
  deriving FromJson
private structure EditorRow where
  epoch : Nat
  current : Nat
  saved : Option Nat
  savedRevision : Nat
  deriving FromJson
private structure Row where
  kind : Nat
  stored : StoreRow
  editor : EditorRow
  expected : Nat
  image : Nat
  validAuthoring : Bool
  available : List Nat
  missing : List Nat
  verified : List Nat
  boundary : Nat
  backing : Bool
  finalized : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def canonical (xs : List Nat) : Bool := xs == xs.mergeSort (· ≤ ·) && xs.eraseDups.length == xs.length
private def label (n : Nat) : Bool := 0 < n && n ≤ 4096
private def run (r : Row) : Except String Result := do
  if r.kind > 4 || r.boundary > 3 || r.stored.revision > 4096 || r.expected > 4096 || r.editor.savedRevision > 4096 || r.editor.epoch > 65536 then throw "Research operation or revision bound."
  if (r.stored.revision == 0) != r.stored.image.isNone || (r.editor.savedRevision == 0) != r.editor.saved.isNone then throw "Invalid observed saved basis."
  if r.stored.image.any (fun n => !label n) || r.editor.saved.any (fun n => !label n) || !label r.image || r.editor.current > 4096 then throw "Invalid image label."
  for xs in [r.available,r.missing,r.verified] do
    if xs.length > 33 || !canonical xs || xs.any (fun n => !label n) then throw "Invalid role set."
  let s : Stored := ⟨r.stored.revision,r.stored.image⟩
  let e : Editor := ⟨r.editor.epoch,r.editor.current,r.editor.saved,r.editor.savedRevision⟩
  let d : DraftImage := ⟨r.image,r.validAuthoring,r.available,r.missing⟩
  let result ← match r.kind with
    | 0 => pure (observe s e)
    | 1 => pure (save s e r.expected d r.verified r.boundary)
    | 2 => pure (reopen s e r.backing)
    | 3 => pure (backup s e r.backing r.finalized)
    | 4 => pure (reopenThenSave s e r.backing d r.verified r.boundary)
    | _ => throw "Unknown operation."
  pure result
private def option (n : Option Nat) : String := n.map toString |>.getD "-"
private def render (r : Result) : String := String.intercalate "/"
  [toString r.stored.revision,option r.stored.image,toString r.editor.epoch,toString r.editor.current,
   option r.editor.saved,toString r.editor.savedRevision,toString r.status]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one portable study research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "captured-browser-study-save" || input.rows.length > 256 then
      IO.eprintln "Unsupported study schema/profile/count."; return 2
    match input.rows.mapM (fun r => do let result ← run r; pure (render result)) with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
