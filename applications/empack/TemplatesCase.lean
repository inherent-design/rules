import Lean
import applications.empack.Templates
open Lean ApplicationStudy.EmpackTemplates

private structure AddressRow where
  recognized : Bool
  valid : Option Bool
  explicit : Bool
  deriving FromJson
private structure BodyRow where
  mode : Nat
  utf8 : Bool
  known : Bool
  deriving FromJson
private structure PrepareRow where
  addresses : Option Bool
  sameLayer : Option Bool
  namespaceValid : Option Bool
  bodies : Option Bool
  game : Option Bool
  deriving FromJson
private structure Input where
  schema : Nat
  addresses : List AddressRow
  bodies : List BodyRow
  prepares : List PrepareRow
  deriving FromJson
private structure Output where
  addresses : List Nat
  bodies : List Nat
  prepares : List Nat
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one template study JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported template study schema."; return 2
    let results : Except String Output := do
      let addresses ← input.addresses.mapM fun row => do
        let some result := address row.recognized row.valid row.explicit
          | throw "Needed template address fact is unknown."
        return result
      let bodies ← input.bodies.mapM fun row => do
        if row.mode > 2 then throw "Unsupported template mode."
        return body row.mode row.utf8 row.known
      let prepares ← input.prepares.mapM fun row => do
        let some result := prepare row.addresses row.sameLayer row.namespaceValid row.bodies row.game
          | throw "Needed template preparation fact is unknown."
        return result
      return ⟨addresses, bodies, prepares⟩
    match results with
    | .error error => IO.eprintln error; return 2
    | .ok output => IO.println (toJson output).compress; return 0
