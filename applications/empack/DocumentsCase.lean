import Lean
import applications.empack.Documents
open Lean ApplicationStudy.EmpackDocuments

private structure MeaningRow where
  name : Nat
  seedPayload : Bool
  deriving FromJson
private structure BasisRow where
  author : String
  bindings : Option String
  lock : Option String
  deriving FromJson
private structure Row where
  action : Nat
  prepared : BasisRow
  current : BasisRow
  meaning : MeaningRow
  locked : Option MeaningRow
  valid : Bool
  approved : Bool
  otherChecks : Bool
  writtenLock : String
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def basis (r : BasisRow) : Basis := ⟨r.author,r.bindings,r.lock⟩
private def meaning (r : MeaningRow) : Meaning := ⟨r.name,r.seedPayload⟩
private def evaluate (r : Row) : Except String Json := do
  if r.meaning.name > 3 || r.locked.any (fun m => m.name > 3) then throw "Meaning outside controlled document fixture."
  let state : State := ⟨basis r.current,meaning r.meaning,r.locked.map meaning,r.valid⟩
  let label ← match r.action with
    | 0 => pure (inspect state)
    | 1 => pure (if !state.valid then "invalid" else
        if r.approved && r.otherChecks && documentGate (basis r.prepared) state then "recorded" else "refused")
    | _ => throw "Unsupported document action."
  let after := if r.action == 1 then record (basis r.prepared) state r.approved r.otherChecks r.writtenLock else state
  let encodeMeaning (m : Meaning) := Json.mkObj [("name",toJson m.name),("seedPayload",toJson m.seedPayload)]
  pure (Json.mkObj [("label",toJson label),("author",toJson after.basis.author),
    ("bindings",toJson after.basis.bindings),("lock",toJson after.basis.lock),
    ("locked",(after.locked.map encodeMeaning).getD Json.null)])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one document research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported document research schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok result => IO.println (toJson result).compress; return 0
