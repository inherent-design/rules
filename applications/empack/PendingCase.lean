import Lean
import applications.empack.Pending
open Lean ApplicationStudy.EmpackPending
private structure StateRow where
  record : Nat
  first : Bool
  second : Bool
  firstBacking : Nat
  secondBacking : Nat
  published : Bool
  deriving FromJson
private structure SupplyRow where
  key : Nat
  content : Nat
  deriving FromJson
private structure Row where
  state : StateRow
  action : Nat
  selected : Nat
  files : List SupplyRow
  discovered : List Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def encode (r : Result) : String :=
  s!"{r.code}/{r.state.record}/{if r.state.first then 1 else 0}/{if r.state.second then 1 else 0}/{r.state.firstBacking}/{r.state.secondBacking}/{if r.state.published then 1 else 0}"
private def runRow (r : Row) : Except String String := do
  if r.action > 3 || r.state.record > 2 || r.selected > 2 ||
      r.state.firstBacking > 2 || r.state.secondBacking > 2 ||
      r.files.any (fun f => f.key > 9 || f.content > 2) || r.discovered.any (· > 2) then
    throw "Outside the selected pending fixture profile."
  pure (encode (evaluate ⟨r.state.record,r.state.first,r.state.second,r.state.firstBacking,r.state.secondBacking,r.state.published⟩
    ⟨r.action,r.selected,r.files.map (fun f => ⟨f.key,f.content⟩),r.discovered⟩))
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one pending-study DTO."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok i =>
    if i.schema != 1 then IO.eprintln "Unsupported pending-study schema."; return 2
    match i.cases.mapM runRow with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
