import Lean
import applications.empack.Recovery
open Lean ApplicationStudy.EmpackRecovery
private structure ViewRow where
  supported : Bool
  rootMatches : Bool
  committed : Bool
  restoring : Bool
  position : Nat
  beforeObject : Bool
  candidateValid : Bool
  beforeValid : Bool
  deriving FromJson
private structure Row where
  mode : Nat
  restore : Bool
  accepted : Bool
  operationMatches : Bool
  sameJournal : Bool
  sameVisible : Bool
  prepared : ViewRow
  observed : ViewRow
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  cases : List Row
  deriving FromJson
private def view (v : ViewRow) : Except String View := do
  if v.position > 2 then throw "Unknown target position."
  pure ⟨v.supported,v.rootMatches,v.committed,v.restoring,v.position,v.beforeObject,v.candidateValid,v.beforeValid⟩
private def request (r : Row) : Except String Request := do
  if r.mode > 2 then throw "Unknown recovery mode."
  pure ⟨r.mode,r.restore,r.accepted,r.operationMatches,r.sameJournal,r.sameVisible,← view r.prepared,← view r.observed⟩
private def bit (b : Bool) : String := if b then "1" else "0"
private def render (v : Outcome) : String := String.intercalate "/"
  [if v.success then "0" else "1",toString (v.planned.map (· + 1) |>.getD 0),toString v.position,
   bit v.committed,bit v.restoring,bit v.scratchCreated]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one recovery research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "one-file-authored-recovery" || input.cases.length > 256 then
      IO.eprintln "Unsupported recovery research schema/profile/count."; return 2
    match input.cases.mapM (fun row => do
      let r ← request row
      pure (render (evaluate r),proposedPrepare r.prepared r.restore)) with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
