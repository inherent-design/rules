import Lean
import host.java.ClassInit
open Lean Host.Java.ClassInit

private structure Row where
  target : Nat
  loader : Nat
  request : Bool
  array : Bool
  operation : Nat
  deriving FromJson
private structure Request where
  schema : Nat
  contract : String
  cases : List Row
  deriving FromJson

private def admit (r : Row) : Except String Action := do
  if r.target > 4 || r.loader > 2 || r.operation > 2 then throw "Unselected class,loader or API form."
  if r.loader != 0 && r.target != 0 && r.target != 4 then throw "Unselected custom-loader target."
  if r.operation == 0 && (r.request || r.loader != 0 || !((r.target == 0 && !r.array) || (r.target == 3 && r.array))) then
    throw "Unselected class literal."
  if r.operation == 1 && (!r.request || r.loader != 0) then throw "Default API initializes through the caller loader."
  if r.array && (r.target != 3 || r.loader != 0 || r.operation == 2) then throw "Unselected array lookup."
  pure ⟨r.target,r.loader,r.request,r.array⟩

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one class-initialization request."; return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e; return 2
  | .ok request =>
    if request.schema != 1 || request.contract != "java17-21-25-authored-serial-class-init" || request.cases.length > 64 then
      IO.eprintln "Unselected schema,contract or batch."; return 2
    match request.cases.mapM admit with
    | .error e => IO.eprintln e; return 2
    | .ok actions => IO.println (toJson (trace {} actions)).compress; return 0
