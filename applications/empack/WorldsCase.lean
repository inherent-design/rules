import Lean
import applications.empack.Worlds
open Lean ApplicationStudy.EmpackWorlds

private structure Row where
  id : String
  recorded : Bool
  oldGroup : Bool
  incoming : Bool
  overlapsProtected : Bool
  occupied : Option Bool
  capturedAbsent : Bool
  stillCurrent : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure Output where
  id : String
  initializedAfterSuccess : Bool
  protectedGroup : Bool
  planMembers : Bool
  maySeedNewGroup : Bool
  deriving ToJson

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one world-group input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then
      IO.eprintln "Unsupported world-group schema."
      return 2
    if input.cases.any (fun r => r.incoming && !r.recorded && !r.oldGroup &&
        !r.overlapsProtected && r.occupied.isNone) then
      IO.eprintln "A new unprotected world requires a known occupancy observation."
      return 2
    let output : List Output := input.cases.map fun r =>
      -- None is admitted only when protection/omission bypasses occupancy.
      let b : Basis := ⟨r.recorded, r.oldGroup, r.incoming, r.overlapsProtected, r.occupied.getD false⟩
      ⟨r.id, initialized b, protectedGroup b, planMembers b,
       mayPublishNewSeed b r.capturedAbsent r.stillCurrent⟩
    IO.println (toJson output).compress
    return 0
