import Lean
import applications.mo2.Process
open Lean ApplicationStudy.Mo2Process

private structure Row where
  id : String
  hooked : Nat
  flags : Nat
  reason : Nat
  lockEnabled : Nat
  waitResult : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private structure Output where
  id : String
  values : List Nat
  deriving ToJson
private def bit (n offset : Nat) : Bool := n / (2 ^ offset) % 2 == 1
private def nat (b : Bool) : Nat := if b then 1 else 0
private def run (row : Row) : Except String Output := do
  if row.hooked > 1 || row.lockEnabled > 1 || row.flags > 7 || row.reason > 3 ||
      row.waitResult < 1 || row.waitResult > 5 then
    throw "Unsupported process-policy research input."
  let request : Request := ⟨row.hooked == 1, bit row.flags 0, bit row.flags 1,
    bit row.flags 2, row.reason, row.lockEnabled == 1, row.waitResult⟩
  let out := post request
  return ⟨row.id, [out.returned, out.reason, nat out.waited, nat out.lockAttached,
    nat out.nullSession, nat out.afterRun, nat out.refreshWait, nat out.refreshWait,
    nat (shouldRefresh request.triggerRefresh request.waitResult)]⟩

def main : IO Unit := do
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  let text ← stdin.readToEnd
  let decoded := do
    let json ← Json.parse text
    let input ← fromJson? (α := Input) json
    if input.schema != 1 then throw "Unsupported process-policy research schema."
    input.cases.mapM run
  match decoded with
  | .error message => throw (IO.userError message)
  | .ok rows => stdout.putStrLn ((toJson rows).compress)
